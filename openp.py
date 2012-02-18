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


IS_PY3 = sys.version_info[0] == 3





class OpenP(object):
    _procs_to_cleanup = []
    registered_cleanup = False

    def __init__(self, cmd, persist=False):
        if not OpenP.registered_cleanup:
            atexit.register(OpenP._cleanup_procs)
            OpenP.registered_cleanup = True


        # these are for aggregating the stdout and stderr
        self._stdout = []
        self._stderr = []
        
        #self._stdin = stdin or Queue()

        self._stdout_collector_thread = None
        self._stdout_reader_thread = None
        self._stderr_collector_thread = None
        self._stderr_reader_thread = None



        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc_was_enabled = gc.isenabled()
        gc.disable()

        self.stderr, slave_stderr = pty.openpty()
        try: self.pid, self.stdinout = pty.fork()
        except:
            if gc_was_enabled: gc.enable()
            raise

        if self.pid == 0:
            os.dup2(slave_stderr, 2)

            os.execv(cmd[0], cmd)

            os._exit(255)

        else:
            if not persist: OpenP._procs_to_cleanup.append(self)
            self.stdin = self.stdinout
            self.stdout = self.stdinout

            self.setwinsize(24, 80)

            #attr = termios.tcgetattr(self.stdin)
            #attr[3] = attr[3] & ~termios.ECHO
            #termios.tcsetattr(self.stdin, termios.TCSANOW, attr)


    def setwinsize(self, r, c):
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735L: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.

        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self.stdout, TIOCSWINSZ, s)


    @staticmethod
    def _start_thread(fn, *args):
        thrd = threading.Thread(target=fn, args=args)
        thrd.daemon = True
        thrd.start()


    def _write_stream(self, stream, queue):
        while True:
            chunk = queue.get()
            if chunk is None: break
            os.write(stream, chunk.encode())
        os.close(stream)
    

    def _read_stream(self, stream, fn, bufsize, queue):
         # we can't actually start collecting yet until both threads have
        # started, the reason being, if one thread exits very quickly (for
        # example, if the command errored out), the stdout and stderr are
        # both used in the exception handling, but if both threads haven't
        # started, we don't exactly have stdout and stderr
        self._start_collecting.wait()

        # here we choose how to call the callback, depending on how many
        # arguments it takes.  the reason for this is to make it as easy as
        # possible for people to use, without limiting them.  a new user will
        # assume the callback takes 1 argument (the data).  as they get more
        # advanced, they may want to terminate the process, or pass some stdin
        # back, and will realize that they can pass a callback of more args
        if fn:
            num_args = len(inspect.getargspec(fn).args)
            args = ()
            if num_args == 2: args = (self._stdin,)
            elif num_args == 3: args = (self._stdin, self)
         
        call_fn = bool(fn)
        
        # we use this sentinel primarily for python3+, because iter() takes
        # a buffer object (for the second argument) to test against.  if we
        # just say iter(stream, ""), it will read forever in python3, because
        # although we're receiving data off of the stream, it's in bytes,
        # not as a string object
        sentinel = "".encode()
            

        buf = []
        line_buffered = bufsize == 1
        if line_buffered: bufsize = 1024

        try:
            while True:
                chunk = os.read(stream, bufsize)
                if not chunk: break

                if line_buffered:
                    newline = chunk.find("\n")
                    if newline == -1: continue
                    else:
                        buf.append(chunk[:newline+1])
                        remainder = chunk[newline+1:]
                        chunk = "".join(buf)
                        buf = [remainder]

                if IS_PY3: chunk = chunk.decode("utf8")
                queue.put(chunk)
                if call_fn and fn(chunk, *args): call_fn = False

                    
        except KeyboardInterrupt:
            interrupt_main()
                    
        finally:
            os.close(stream)
            
            # so our collector and possible iterator can stop
            queue.put(None)


    def kill(self, sig=signal.SIGKILL):
        try: os.kill(self.pid, sig)
        except OSError: pass


    @staticmethod
    def _cleanup_procs():
        for proc in OpenP._procs_to_cleanup:
            proc.kill()


    def wait(self):
        pid, status = os.waitpid(self.pid, 0)
        return status

