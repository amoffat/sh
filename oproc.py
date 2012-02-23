import pty
import os
import sys
import termios
import signal
import select
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





class OProc(object):
    _procs_to_cleanup = []
    registered_cleanup = False

    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, bufsize=1,
            persist=False, wait=True, ibufsize=100000):
        
        if not OProc.registered_cleanup:
            atexit.register(OProc._cleanup_procs)
            OProc.registered_cleanup = True


        self.cmd = cmd
        self.exit_code = None
        self._done_callbacks = []
        
        self.stdin = stdin or Queue()
        self._pipe_queue = Queue()


        # these are for aggregating the stdout and stderr.  we use a deque
        # because we don't want to overflow
        self._stdout = deque(maxlen=ibufsize)
        self._stderr = deque(maxlen=ibufsize)


        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc_was_enabled = gc.isenabled()
        gc.disable()

        self._stderr_fd, slave_stderr = pty.openpty()
        self._stdin_fd, slave_stdin = pty.openpty()
        
        try: self.pid, stdinout = pty.fork()
        except:
            if gc_was_enabled: gc.enable()
            raise

        # child
        if self.pid == 0:
            os.dup2(slave_stdin, 0)
            os.dup2(slave_stderr, 2)
            
            # don't inherit file descriptors
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            os.closerange(3, max_fd)

            os.execv(cmd[0], cmd)

            os._exit(255)

        # parent
        else:
            if gc_was_enabled: gc.enable()
            
            if not persist: OProc._procs_to_cleanup.append(self)
            self._stdout_fd = stdinout

            self._setwinsize(24, 80)

            # turn off echoing
            attr = termios.tcgetattr(stdinout)
            attr[3] = attr[3] & ~termios.ECHO
            termios.tcsetattr(stdinout, termios.TCSANOW, attr)
            
            # set raw mode, so there isn't any weird translation of newlines
            # to \r\n and other oddities
            tty.setraw(stdinout)



            stdout_stream = StreamReader(
                self._stdout_fd, stdout, self._stdout, bufsize,
                self._pipe_queue
            )
                
            stderr_stream = StreamReader(self._stderr_fd, stderr, self._stderr,
                bufsize)
            
            self._reader_thread = self._start_thread(self.reader_thread,
                stdout_stream, stderr_stream)
                
            self._stdin_writer_thread = self._start_thread(
                self._write_stream, self._stdin_fd, self.stdin)
            
            if wait: self.wait()
            

    def _setwinsize(self, r, c):
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735L: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.

        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self._stdout_fd, TIOCSWINSZ, s)


    @staticmethod
    def _start_thread(fn, *args):
        thrd = threading.Thread(target=fn, args=args)
        thrd.daemon = True
        thrd.start()
        return thrd


    def _write_stream(self, stream, queue):
        while True:
            chunk = queue.get()
            
            # EOF
            if chunk is None:
                os.write(stream, chr(4))
                break
            
            # process exiting
            elif chunk is False:
                break
            
            try: os.write(stream, chunk.encode())
            except OSError: break
        
        
    def add_done_callback(self, cb):
        self._done_callbacks.append(cb)
        
    @property
    def alive(self):
        # this might happen on interpretter shutdown, as python is cleaning
        # up modules (gc'ing them and setting their names to None), so we
        # check for that
        if os is None: return False
        
        alive = True
         
        try:
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                alive = False
                self.exit_code = exit_code
             
        # no child process   
        except OSError: alive = False
        return alive


    def reader_thread(self, stdout, stderr):
        readers = [stdout, stderr]
        
        while True:
            try: read, write, err = select.select(readers, [], [], 0.01)
            except: break
            
            #print read, write, err
            
            if not read:
                if not self.alive: break
                continue

            for stream in read:
                error = stream.read()
                if error: readers.remove(stream)
                
        stdout.close()
        stderr.close()


    @property
    def stdout(self):
        return "".join(self._stdout)
    
    @property
    def stderr(self):
        return "".join(self._stderr)
    

    def kill(self, sig=signal.SIGKILL):
        try: os.kill(self.pid, sig)
        except OSError: pass


    @staticmethod
    def _cleanup_procs():
        for proc in OProc._procs_to_cleanup:
            proc.kill()


    def wait(self):
        if self.exit_code is None: pid, self.exit_code = os.waitpid(self.pid, 0)
        
        self._reader_thread.join()
        
        self.stdin.put(False)
        self._stdin_writer_thread.join()
        
        for cb in self._done_callbacks: cb()
        
        return self.exit_code




class StreamReader(object):

    def __init__(self, stream, handler, buffer, bufsize, pipe_queue=None):
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
            num_args = len(inspect.getargspec(handler).args)
            self.handler_args = ()
            if num_args == 2: self.handler_args = (self.stdin,)
            elif num_args == 3: self.handler_args = (self.stdin, self)
            

    def fileno(self):
        return self.stream
            

    def close(self):
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
        except OSError: return True
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
