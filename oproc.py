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
            persist=False, wait=True, ibufsize=10000):
        
        if not OProc.registered_cleanup:
            atexit.register(OProc._cleanup_procs)
            OProc.registered_cleanup = True


        self.cmd = cmd
        self.exit_code = None
        self._done_callbacks = []
        
        self.bufsize = bufsize
        self.stdin = stdin or Queue()
        self._pipe_queue = Queue()


        # these are for aggregating the stdout and stderr
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

        if self.pid == 0:
            os.dup2(slave_stdin, 0)
            os.dup2(slave_stderr, 2)
            
            # don't inherit file descriptors
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            os.closerange(3, max_fd)

            os.execv(cmd[0], cmd)

            os._exit(255)

        else:
            if not persist: OProc._procs_to_cleanup.append(self)
            #self._stdin_fd = stdinout
            self._stdout_fd = stdinout

            self._setwinsize(24, 80)

            # turn off echoing
            attr = termios.tcgetattr(stdinout)
            attr[3] = attr[3] & ~termios.ECHO
            termios.tcsetattr(stdinout, termios.TCSANOW, attr)
            
            tty.setraw(stdinout)

            # start the threads
            self._stdin_writer_thread = self._start_thread(
                self._write_stream, self._stdin_fd, self.stdin)
            self._stdout_reader_thread = self._start_thread(
                self._read_stream, self._stdout_fd, stdout, self._stdout, self._pipe_queue)
            self._stderr_reader_thread = self._start_thread(
                self._read_stream, self._stderr_fd, stderr, self._stderr)
            
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
            
            os.write(stream, chunk.encode())
        
        
    def add_done_callback(self, cb):
        self._done_callbacks.append(cb)
        
    @property
    def alive(self):
        alive = True     
         
        try:
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                alive = False
                self.exit_code = exit_code
             
        # no child process   
        except OSError: alive = False
        return alive
    
        
    @property
    def stdout(self):
        return "".join(self._stdout)
    
    @property
    def stderr(self):
        return "".join(self._stderr)
    

    def _read_stream(self, stream, handler, buffer, pipe_queue=None):
        if callable(handler): handler_type = "fn"
        elif hasattr(handler, "write"): handler_type = "fd"
        else: handler_type = None
        
        should_quit = False
        
        # here we choose how to call the callback, depending on how many
        # arguments it takes.  the reason for this is to make it as easy as
        # possible for people to use, without limiting them.  a new user will
        # assume the callback takes 1 argument (the data).  as they get more
        # advanced, they may want to terminate the process, or pass some stdin
        # back, and will realize that they can pass a callback of more args
        if handler_type == "fn":
            num_args = len(inspect.getargspec(handler).args)
            args = ()
            if num_args == 2: args = (self.stdin,)
            elif num_args == 3: args = (self.stdin, self)
            
            
            
        def write_chunk(chunk, should_quit):
            if IS_PY3: chunk = chunk.decode("utf8")
            if handler_type == "fn" and not should_quit:
                should_quit = handler(chunk, *args)
                
            elif handler_type == "fd":
                handler.write(chunk) 
                
            if pipe_queue: pipe_queue.put(chunk)        
            buffer.append(chunk)
            return should_quit
        
        # we use this sentinel primarily for python3+, because iter() takes
        # a buffer object (for the second argument) to test against.  if we
        # just say iter(stream, ""), it will read forever in python3, because
        # although we're receiving data off of the stream, it's in bytes,
        # not as a string object
        sentinel = "".encode()
            

        buf = []
        bufsize = self.bufsize
        line_buffered = bufsize == 1
        if bufsize == 0: bufsize = 1
        if line_buffered: bufsize = 1024

        try:
            while True:
                try: read, write, err = select.select([stream], [], [], 0.01)
                except: break
                
                if not read:
                    if not self.alive: break
                    continue
                
                try: chunk = os.read(stream, bufsize)
                except OSError: break
                if not chunk: break


                if line_buffered:
                    while True:
                        newline = chunk.find("\n")
                        if newline == -1: break
                        
                        chunk_to_write = chunk[:newline+1]
                        if buf:
                            chunk_to_write = "".join(buf) + chunk_to_write
                            buf = []
                        
                        chunk = chunk[newline+1:]
                        write_chunk(chunk_to_write, should_quit)
                             
                    if chunk: buf.append(chunk)       
                        
                    
                else:
                    write_chunk(chunk, should_quit)
              
        finally:
            try: os.close(stream)
            except: pass
            
            # so our possible iterator can stop
            if pipe_queue: pipe_queue.put(None)


    def kill(self, sig=signal.SIGKILL):
        try: os.kill(self.pid, sig)
        except OSError: pass


    @staticmethod
    def _cleanup_procs():
        for proc in OProc._procs_to_cleanup:
            proc.kill()


    def wait(self):
        if self.exit_code is None: pid, self.exit_code = os.waitpid(self.pid, 0)
        
        self._stdout_reader_thread.join()
        self._stderr_reader_thread.join()
        
        self.stdin.put(False)
        self._stdin_writer_thread.join()
        
        for cb in self._done_callbacks: cb()
        
        return self.exit_code

