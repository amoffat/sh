import pty
import os
import sys
import termios
import signal
import select
import errno
import atexit
import gc
import threading
import traceback
import tty
import pickle
import inspect
import fcntl
import struct
import resource
from collections import deque
import logging
import time

from threading import Thread, Event
try: from Queue import Queue, Empty
except ImportError: from queue import Queue, Empty  # 3


IS_PY3 = sys.version_info[0] == 3

if IS_PY3:
    basestring = str


# used in redirecting
STDOUT = -1
STDERR = -2



class OProc(object):
    _procs_to_cleanup = []
    registered_cleanup = False

    def __init__(self, cmd, stdin, stdout, stderr, call_args,
            persist=False, ibufsize=100000, pipe=STDOUT):

        self.call_args = call_args

        if self.call_args["tty_in"]: self._stdin_fd, self._slave_stdin_fd = os.openpty()
        else: self._slave_stdin_fd, self._stdin_fd = os.pipe()
        self._stdout_fd, self._slave_stdout_fd = pty.openpty()
        
        # only open a pty for stderr if we're not directing to stdout
        if stderr is not STDOUT: self._stderr_fd, self._slave_stderr_fd = pty.openpty()
        
        self.pid = os.fork()


        # child
        if self.pid == 0:            
            os.close(self._stdin_fd)
            os.close(self._stdout_fd)
            if stderr is not STDOUT: os.close(self._stderr_fd)
            
            # this controlling tty code was borrowed from pexpect.py
            # good work, noah!
            if self.call_args["tty_in"]:
                child_tty = os.ttyname(self._slave_stdin_fd)

                # disconnect from controlling tty if still connected.
                fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
                if fd >= 0: os.close(fd)
        
                os.setsid()
        
                # verify we are disconnected from controlling tty
                try:
                    fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
                    if fd >= 0:
                        os.close(fd)
                        raise Exception("Error! We are not disconnected from a controlling tty.")
                except:
                    # good! we are disconnected from a controlling tty
                    pass
        
                # verify we can open child pty
                fd = os.open(child_tty, os.O_RDWR);
                if fd < 0: raise Exception("Error! Could not open child pty, " + child_tty)
                else: os.close(fd)
        
                # verify we now have a controlling tty
                fd = os.open("/dev/tty", os.O_WRONLY)
                if fd < 0: raise Exception("Error! Could not open controlling tty, /dev/tty")
                else: os.close(fd)
                
                    
                    
            if self.call_args["cwd"]: os.chdir(self.call_args["cwd"])
            os.dup2(self._slave_stdin_fd, 0)
            os.dup2(self._slave_stdout_fd, 1)
            
            # we're not directing stderr to stdout?  then set self._slave_stderr_fd to
            # fd 2, the common stderr fd
            if stderr is STDOUT: os.dup2(self._slave_stdout_fd, 2) 
            else: os.dup2(self._slave_stderr_fd, 2)
            
            # don't inherit file descriptors
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            os.closerange(3, max_fd)
                    

            self.setwinsize(1, 24, 80)
            
            # actually execute the process
            if self.call_args["env"] is None: os.execv(cmd[0], cmd)
            else: os.execve(cmd[0], cmd, self.call_args["env"])

            os._exit(255)

        # parent
        else:
            
            if not OProc.registered_cleanup:
                atexit.register(OProc._cleanup_procs)
                OProc.registered_cleanup = True
        
        
            self.cmd = cmd
            self.exit_code = None
            self._done_callbacks = []
            
            self.stdin = stdin or Queue()
            self._pipe_queue = Queue()
        
            # this is used to prevent a race condition when we're waiting for
            # a process to end, and the OProc's internal threads are also checking
            # for the processes's end
            self._wait_lock = threading.Lock()
        
            # these are for aggregating the stdout and stderr.  we use a deque
            # because we don't want to overflow
            self._stdout = deque(maxlen=ibufsize)
            self._stderr = deque(maxlen=ibufsize)
            
            
            if self.call_args["tty_in"]: self.setwinsize(self._stdin_fd, 24, 80)
            
            
            self.log = logging.getLogger("process %r" % self)
            
            os.close(self._slave_stdin_fd)
            os.close(self._slave_stdout_fd)
            if stderr is not STDOUT: os.close(self._slave_stderr_fd)
            
            self.log.debug("started process")
            if not persist: OProc._procs_to_cleanup.append(self)


            if self.call_args["tty_in"]:
                attr = termios.tcgetattr(self._stdin_fd)
                attr[3] &= ~termios.ECHO  
                termios.tcsetattr(self._stdin_fd, termios.TCSANOW, attr)


            # set raw mode, so there isn't any weird translation of newlines
            # to \r\n and other oddities.  we're not outputting to a terminal
            # anyways
            tty.setraw(self._stdout_fd)
            if stderr is not STDOUT: tty.setraw(self._stderr_fd)



            stdin_stream = StreamWriter("stdin", self, self._stdin_fd, self.stdin)
                           
            stdout_pipe = self._pipe_queue if pipe is STDOUT else None
            stdout_stream = StreamReader("stdout", self, self._stdout_fd, stdout,
                self._stdout, self.call_args["bufsize"], stdout_pipe)
                
                
            if stderr is STDOUT: stderr_stream = None 
            else:
                stderr_pipe = self._pipe_queue if pipe is STDERR else None   
                stderr_stream = StreamReader("stderr", self, self._stderr_fd, stderr,
                    self._stderr, self.call_args["bufsize"], stderr_pipe)
            
            # start the main io thread
            self._io_thread = self._start_thread(self.io_thread,
                stdin_stream, stdout_stream, stderr_stream)
            
            
    def __repr__(self):
        return "<Process %d %r>" % (self.pid, self.cmd)        
            

    # also borrowed from pexpect.py
    @staticmethod
    def setwinsize(fd, r, c):
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.

        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(fd, TIOCSWINSZ, s)


    @staticmethod
    def _start_thread(fn, *args):
        thrd = threading.Thread(target=fn, args=args)
        thrd.daemon = True
        thrd.start()
        return thrd            
                
                
        
    def add_done_callback(self, cb):
        self._done_callbacks.append(cb)

    def io_thread(self, stdin, stdout, stderr):
        writers = [stdin]
        readers = []
        errors = []
        
        # they might be None in the case that we're redirecting one to the other
        if stdout is not None:
            readers.append(stdout)
            errors.append(stdout)
        if stderr is not None:
            readers.append(stderr)
            errors.append(stderr)
            
        break_next = False
        
        while readers:
            read, write, err = select.select(readers, writers, errors, 0)

            for stream in read:
                self.log.debug("%r ready to be read from", stream)
                done = stream.read()
                if done: readers.remove(stream)
                
            for stream in write:
                self.log.debug("%r ready for more input", stream)
                done = stream.write()
                if done: writers.remove(stream)
                
            for stream in err:
                pass
            
        if stdout: stdout.close()
        if stderr: stderr.close()


    @property
    def stdout(self):
        return "".join(self._stdout)
    
    @property
    def stderr(self):
        return "".join(self._stderr)
    
    
    def send_signal(self, sig):
        self.log.debug("sending signal %d", sig)
        try: os.kill(self.pid, sig)
        except OSError: pass

    def kill(self):
        self.log.debug("killing")
        self.send_signal(signal.SIGKILL)

    def terminate(self):
        self.log.debug("terminating")
        self.send_signal(signal.SIGTERM)

    @staticmethod
    def _cleanup_procs():
        for proc in OProc._procs_to_cleanup:
            proc.kill()
            proc.wait()


    def _handle_exitstatus(self, sts):
        # if we exited from a signal, let our exit code reflect that
        if os.WIFSIGNALED(sts): return -os.WTERMSIG(sts)
        # otherwise just give us a normal exit code
        elif os.WIFEXITED(sts): return os.WEXITSTATUS(sts)
        else: raise RuntimeError("Unknown child exit status!")
        
    @property
    def alive(self):
        if self.exit_code is not None: return False
         
        # what we're doing here essentially is making sure that the main thread
        # (or another thread), isn't calling .wait() on the process.  because
        # .wait() calls os.waitpid(self.pid, 0), we can't do an os.waitpid
        # here...because if we did, and the process exited while in this
        # thread, the main thread's os.waitpid(self.pid, 0) would raise OSError
        # (because the process ended in another thread).
        #
        # so essentially what we're doing is, using this lock, checking if
        # we're calling .wait(), and if we are, let .wait() get the exit code
        # and handle the status, otherwise let us do it.
        acquired = self._wait_lock.acquire(False)
        if not acquired:
            if self.exit_code is not None: return False
            return True
         
        try:
            # WNOHANG is just that...we're calling waitpid without hanging...
            # essentially polling the process
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                self.exit_code = self._handle_exitstatus(exit_code)
                return False
             
        # no child process   
        except OSError: return False
        else: return True
        finally: self._wait_lock.release()
            

    def wait(self):
        self.log.debug("acquiring wait lock to wait for completion")
        with self._wait_lock:
            self.log.debug("got wait lock")
            
            if self.exit_code is None:
                self.log.debug("exit code not set, waiting on pid")
                pid, exit_code = os.waitpid(self.pid, 0)
                self.exit_code = self._handle_exitstatus(exit_code)
            else:
                self.log.debug("exit code already set (%d), no need to wait", self.exit_code)
            
            self._io_thread.join()
            
            for cb in self._done_callbacks: cb()
        
            return self.exit_code




class DoneReadingStdin(Exception): pass
class NoStdinData(Exception): pass



# this guy is for reading from some input (the stream) and writing to our
# opened process's stdin fd.  the stream can be a Queue, a callable, something
# with the "read" method, a string, or an iterable
class StreamWriter(object):
    def __init__(self, name, process, stream, stdin):
        self.name = name
        self.process = process
        self.stream = stream
        self.stdin = stdin
        
        self.log = logging.getLogger(repr(self))
        
        if isinstance(stdin, Queue):
            log_msg = "queue"
            self.get_chunk = self.get_queue_chunk
            
        elif callable(stdin):
            log_msg = "callable"
            self.get_chunk = self.get_callable_chunk
            
        elif hasattr(stdin, "read"):
            log_msg = "file descriptor"
            self.get_chunk = self.get_file_chunk
            
        elif isinstance(stdin, basestring):
            log_msg = "string"
            #self.stdin = iter((c+"\n" for c in stdin.split("\n")))
            stdin_bufsize = 1024
            self.stdin = iter(stdin[i:i+stdin_bufsize] for i in range(0, len(stdin), stdin_bufsize))
            self.get_chunk = self.get_iter_chunk
            
        else:
            log_msg = "general iterable"
            self.stdin = iter(stdin)
            self.get_chunk = self.get_iter_chunk
            
        self.log.debug("parsed stdin as a %s", log_msg)
        
            
    def __repr__(self):
        return "<StreamWriter %s for %r>" % (self.name, self.process)
    
    def fileno(self):
        return self.stream
    
    def get_queue_chunk(self):
        try: chunk = self.stdin.get_nowait()
        except Empty: raise NoStdinData
        if chunk is None: raise DoneReadingStdin
        return chunk
        
    def get_callable_chunk(self):
        try: return self.stdin()
        except: raise DoneReadingStdin
        
    def get_iter_chunk(self):
        try:
            if IS_PY3: return self.stdin.__next__()
            else: return self.stdin.next()
        except StopIteration: raise DoneReadingStdin
        
    def get_file_chunk(self):
        chunk = self.stdin.readline()
        if not chunk: raise DoneReadingStdin
        else: return chunk


    # the return value answers the questions "are we done writing forever?"
    def write(self):
        try: chunk = self.get_chunk()
        except DoneReadingStdin:
            self.log.debug("done reading")
            # write the ctrl+d, which signals some processes that we've reached
            # the EOF.  if we try to straight up close our self.stream fd,
            # some programs will give us errno 5: input/output error.  i assume
            # this is because they think we blind-sided them and closed their
            # input fd without signalling an EOF first.  is there a better
            # way to handle these cases?
            try: char = termios.tcgetattr(self.stream)[6][termios.VEOF]
            except:
                # platform does not define VEOF so assume CTRL-D
                char = chr(4).encode()
                
            if self.process.call_args["tty_in"]: os.write(self.stream, char)
            else: os.close(self.stream)
            return True
        
        except NoStdinData:
            self.log.debug("received no data")
            return False
        
        self.log.debug("got chunk size %d", len(chunk))
        
        if IS_PY3 and hasattr(chunk, "encode"): chunk = chunk.encode()
        
        self.log.debug("writing chunk to process")
        try:
            os.write(self.stream, chunk)
        except OSError:
            self.log.debug("OSError writing stdin chunk")
            return True
        
        
    def close(self):
        try: os.close(self.stream)
        except OSError: pass
        


class StreamReader(object):

    def __init__(self, name, process, stream, handler, buffer, bufsize, pipe_queue=None):
        self.name = name
        self.process = process
        self.stream = stream
        self.buffer = buffer
        self._tmp_buffer = []
        self.pipe_queue = pipe_queue

        self.log = logging.getLogger(repr(self))
        
        # determine buffering
        self.line_buffered = False
        if bufsize == 1:
            buffer_type = "line buffered"
            self.line_buffered = True
            self.bufsize = 1024
        elif bufsize == 0:
            buffer_type = "unbuffered"
            self.bufsize = 1 
        else:
            buffer_type = "%d buffering" % bufsize
            self.bufsize = bufsize
            
        self.log.debug("buffering is " + buffer_type)

        self.handler = handler
        if callable(handler): self.handler_type = "fn"
        elif hasattr(handler, "write"): self.handler_type = "fd"
        else: self.handler_type = None
        
        self.should_quit = False
        
        # here we choose how to call the callback, depending on how many
        # arguments it takes.  the reason for this is to make it as easy as
        # possible for people to use, without limiting them.  a new user will
        # assume the callback takes 1 argument (the data).  as they get more
        # advanced, they may want to terminate the process, or pass some stdin
        # back, and will realize that they can pass a callback of more args
        if self.handler_type == "fn":
            implied_arg = 0
            if inspect.ismethod(handler): implied_arg = 1
            
            num_args = len(inspect.getargspec(handler).args)
            self.handler_args = ()
            if num_args == implied_arg + 2: self.handler_args = (self.process.stdin,)
            elif num_args == implied_arg + 3: self.handler_args = (self.process.stdin, self.process)

    def fileno(self):
        return self.stream
            
    def __repr__(self):
        return "<StreamReader %s for %r>" % (self.name, self.process)

    def close(self):
        # write the last of any tmp buffer that might be leftover from a
        # line-buffered process ending before a newline has been reached
        if self._tmp_buffer:
            self.write_chunk("".join(self._tmp_buffer))
            self._tmp_buffer = []
        
        if self.pipe_queue: self.pipe_queue.put(None)
        try: os.close(self.stream)
        except OSError: pass


    def write_chunk(self, chunk):        
        if self.handler_type == "fn" and not self.should_quit:
            self.should_quit = self.handler(chunk, *self.handler_args)
            
        elif self.handler_type == "fd":
            self.handler.write(chunk.encode())
            
        # we put the chunk on the pipe queue as a string, not py3 bytes
        # this is because it gets used directly by iterators over the Command
        # object..and we want to iterate over strings, not bytes
        if self.pipe_queue: self.pipe_queue.put(chunk)

        self.buffer.append(chunk)

            
    def read(self):
        try: chunk = os.read(self.stream, self.bufsize)
        except OSError as e:
            self.log.debug("got errno %d, done reading", e.errno)
            return True
        if not chunk: return True
        
        if IS_PY3: chunk = chunk.decode()
        self.log.debug("got chunk size %d", len(chunk))

        if self.line_buffered:
            while True:
                newline = chunk.find("\n")
                if newline == -1: break
                
                chunk_to_write = chunk[:newline+1]
                if self._tmp_buffer:
                    chunk_to_write = "".join(self._tmp_buffer) + chunk_to_write
                    self._tmp_buffer = []
                
                chunk = chunk[newline+1:]
                self.write_chunk(chunk_to_write)
                     
            if chunk: self._tmp_buffer.append(chunk)       
                
        # not line buffered
        else: self.write_chunk(chunk)
