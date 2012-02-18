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
import pickle
import inspect
import fcntl
import struct
import resource

from threading import Thread, Event
try: from Queue import Queue, Empty
except ImportError: from queue import Queue, Empty  # 3


IS_PY3 = sys.version_info[0] == 3




class OProc(object):
    _procs_to_cleanup = []
    registered_cleanup = False

    def __init__(self, cmd, bufsize=1, persist=False, wait=True):
        if not OProc.registered_cleanup:
            atexit.register(OProc._cleanup_procs)
            OProc.registered_cleanup = True


        self.exit_code = None
        
        self.bufsize = bufsize
        self.stdin = Queue()
        self._stdout_queue = Queue()
        self._stderr_queue = Queue()
        self._pipe_queue = Queue()

        # these are for aggregating the stdout and stderr
        self._stdout = []
        self._stderr = []


        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc_was_enabled = gc.isenabled()
        gc.disable()

        self._stderr_fd, slave_stderr = pty.openpty()
        try: self.pid, stdinout = pty.fork()
        except:
            if gc_was_enabled: gc.enable()
            raise

        if self.pid == 0:
            os.dup2(slave_stderr, 2)
            
            # don't inherit file descriptors
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            os.closerange(3, max_fd)

            os.execv(cmd[0], cmd)

            os._exit(255)

        else:
            if not persist: OProc._procs_to_cleanup.append(self)
            self._stdin_fd = stdinout
            self._stdout_fd = stdinout

            self._setwinsize(24, 80)

            # turn off echoing
            attr = termios.tcgetattr(stdinout)
            attr[3] = attr[3] & ~termios.ECHO
            termios.tcsetattr(stdinout, termios.TCSANOW, attr)

            # start the threads
            self._start_thread(self._write_stream, self._stdin_fd, self.stdin)
            self._stdout_reader_thread = self._start_thread(
                self._read_stream, self._stdout_fd, None, self._stdout)
            self._stderr_reader_thread = self._start_thread(
                self._read_stream, self._stderr_fd, None, self._stderr)
            
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
            if chunk is None: break
            os.write(stream, chunk.encode())
        os.close(stream)
        
        
    @property
    def alive(self):
        alive = True     
         
        try:
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                alive = False
                self.exit_code = exit_code
                
        except OSError: alive = False
            
        return alive
    
        
    @property
    def stdout(self):
        return "".join(self._stdout)
    
    @property
    def stderr(self):
        return "".join(self._stderr)
    

    def _read_stream(self, stream, fn, buffer, pipe_queue=None):
        # here we choose how to call the callback, depending on how many
        # arguments it takes.  the reason for this is to make it as easy as
        # possible for people to use, without limiting them.  a new user will
        # assume the callback takes 1 argument (the data).  as they get more
        # advanced, they may want to terminate the process, or pass some stdin
        # back, and will realize that they can pass a callback of more args
        if fn:
            num_args = len(inspect.getargspec(fn).args)
            args = ()
            if num_args == 2: args = (self.stdin,)
            elif num_args == 3: args = (self.stdin, self)
         
        call_fn = bool(fn)
        
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
                read, write, err = select.select([stream], [], [], 0.01)
                if not read:
                    if not self.alive: break
                    continue
                
                try: chunk = os.read(stream, bufsize)
                except OSError: break
                if not chunk: break

                if line_buffered:
                    
                    to_write = []
                    found_newline = False
                    
                    while True:
                        newline = chunk.find("\n")
                        if newline == -1: break
                        found_newline = True
                        
                        to_write.append(chunk[:newline+1])
                        chunk = chunk[newline+1:]            
                        
                    if found_newline:
                        tmp = chunk
                        chunk = "".join(buf) + "".join(to_write)
                        buf = [tmp]

                    
                if IS_PY3: chunk = chunk.decode("utf8")
                if call_fn and fn(chunk, *args): call_fn = False
                buffer.append(chunk)
                    
        finally:
            os.close(stream)
            
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
        return self.exit_code

