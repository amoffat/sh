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

from threading import Thread, Event
try: from Queue import Queue, Empty
except ImportError: from queue import Queue, Empty  # 3


IS_PY3 = sys.version_info[0] == 3



# used in redirecting
STDOUT = -1
STDERR = -2



class OProc(object):
    _procs_to_cleanup = []
    registered_cleanup = False

    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, bufsize=1,
            persist=False, ibufsize=100000, pipe=STDOUT, env=None):
        
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


        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc_was_enabled = gc.isenabled()
        gc.disable()

        # only open a pty for stderr if we're not directing to stdout
        if stderr is not STDOUT: self._stderr_fd, slave_stderr = pty.openpty()
        self._stdin_fd, slave_stdin = pty.openpty()
        
        try: self.pid, stdinout = pty.fork()
        except:
            if gc_was_enabled: gc.enable()
            raise

        # child
        if self.pid == 0:
            os.dup2(slave_stdin, 0)
            
            if stderr is not STDOUT: os.dup2(slave_stderr, 2)
            
            # don't inherit file descriptors
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            os.closerange(3, max_fd)
            
            if env is None: os.execv(cmd[0], cmd)
            else: os.execve(cmd[0], cmd, env)

            os._exit(255)

        # parent
        else:
            if gc_was_enabled: gc.enable()
            
            if not persist: OProc._procs_to_cleanup.append(self)
            self._stdout_fd = stdinout

            self._setwinsize(24, 80)

            # turn off echoing
            attr = termios.tcgetattr(self._stdin_fd)
            attr[3] = attr[3] & ~termios.ECHO
            termios.tcsetattr(self._stdin_fd, termios.TCSANOW, attr)


            # set raw mode, so there isn't any weird translation of newlines
            # to \r\n and other oddities
            tty.setraw(stdinout)
            if stderr is not STDOUT: tty.setraw(self._stderr_fd)



            stdin_stream = StreamWriter("stdin", self, self._stdin_fd, self.stdin)
                           
            stdout_pipe = self._pipe_queue if pipe is STDOUT else None             
            stdout_stream = StreamReader("stdout", self, self._stdout_fd, stdout, self._stdout,
                bufsize, stdout_pipe)
                
                
            if stderr is STDOUT: stderr_stream = None 
            else:
                stderr_pipe = self._pipe_queue if pipe is STDERR else None   
                stderr_stream = StreamReader("stderr", self, self._stderr_fd, stderr,
                    self._stderr, bufsize, stderr_pipe)
            
            # start the main io thread
            self._io_thread = self._start_thread(self.io_thread,
                stdin_stream, stdout_stream, stderr_stream)
            
            
            

    def _setwinsize(self, r, c):
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.

        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self._stdout_fd, TIOCSWINSZ, s)


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
        
        # they might be None in the case that we're redirecting one to the other
        if stdout is not None: readers.append(stdout)
        if stderr is not None: readers.append(stderr)
        
        break_next = False
        
        while True:
            read, write, err = select.select(readers, writers, [], 0)

            for stream in read:
                done = stream.read()
                if done: readers.remove(stream)
                
            for stream in write:
                done = stream.write()
                if done: writers.remove(stream)
                
            if not read and not self.alive:
                if break_next: break
                else:
                    # flush out the output streams, but don't break now
                    # (break next) to allow select a chance to grab the drained
                    # output
                    break_next = True
                    for stream in readers:
                        termios.tcdrain(stream.stream)
                
                
        if stdout: stdout.close()
        if stderr: stderr.close()


    @property
    def stdout(self):
        return "".join(self._stdout)
    
    @property
    def stderr(self):
        return "".join(self._stderr)
    
    
    def send_signal(self, sig):
        try: os.kill(self.pid, sig)
        except OSError: pass

    def kill(self):
        self.send_signal(signal.SIGKILL)

    def terminate(self):
        self.send_signal(signal.SIGTERM)

    @staticmethod
    def _cleanup_procs():
        for proc in OProc._procs_to_cleanup:
            proc.kill()
            proc.wait()


    def _handle_exitstatus(self, sts):
        if os.WIFSIGNALED(sts): return -os.WTERMSIG(sts)
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
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                self.exit_code = self._handle_exitstatus(exit_code)
                return False
             
        # no child process   
        except OSError: return False
        else: return True
        finally: self._wait_lock.release()
            

    def wait(self):
        with self._wait_lock:
            if self.exit_code is None:
                pid, exit_code = os.waitpid(self.pid, 0)
                self.exit_code = self._handle_exitstatus(exit_code)
            
            self._io_thread.join()
            
            for cb in self._done_callbacks: cb()
        
            return self.exit_code




class DoneReadingStdin(Exception): pass
class NoStdinData(Exception): pass


class StreamWriter(object):
    def __init__(self, name, process, stream, stdin):
        self.name = name
        self.process = process
        self.stream = stream
        self.stdin = stdin
        
        if isinstance(stdin, Queue):
            self.get_chunk = self.get_queue_chunk
            
        elif callable(stdin):
            self.get_chunk = self.get_callable_chunk
            
        elif hasattr(stdin, "read"):
            self.get_chunk = self.get_file_chunk
            
        elif isinstance(stdin, basestring):
            self.stdin = iter((c+"\n" for c in stdin.split("\n")))
            self.get_chunk = self.get_iter_chunk
            
        else:
            self.stdin = iter(stdin)
            self.get_chunk = self.get_iter_chunk
            
        
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
        try: return self.stdin.next()
        except StopIteration: raise DoneReadingStdin
        
    def get_file_chunk(self):
        chunk = self.stdin.readline()
        if not chunk: raise DoneReadingStdin
        else: return chunk

    def write(self):
        try: chunk = self.get_chunk()
        except DoneReadingStdin:
            os.write(self.stream, chr(4)) # EOF
            return True
        
        except NoStdinData: return False
        
        try: os.write(self.stream, chunk.encode())
        except OSError: return True
        
        
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

        # determine buffering
        self.line_buffered = False
        if bufsize == 1:
            self.line_buffered = True
            self.bufsize = 1024
        elif bufsize == 0: self.bufsize = 1 
        else: self.bufsize = bufsize

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
        return "<StreamReader %s>" % self.name

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
        if IS_PY3: chunk = chunk.decode("utf8")
        if self.handler_type == "fn" and not self.should_quit:
            self.should_quit = self.handler(chunk, *self.handler_args)
            
        elif self.handler_type == "fd":
            self.handler.write(chunk)
            
        if self.pipe_queue: self.pipe_queue.put(chunk)        
        self.buffer.append(chunk)

            
    def read(self):
        try: chunk = os.read(self.stream, self.bufsize)
        except OSError as e: return True
        if not chunk: return True

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
