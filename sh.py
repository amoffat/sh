"""
http://amoffat.github.io/sh/
"""
#===============================================================================
# Copyright (C) 2011-2017 by Andrew Moffat
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#===============================================================================


__version__ = "1.12.9"
__project_url__ = "https://github.com/amoffat/sh"


import platform

if "windows" in platform.system().lower(): # pragma: no cover
    raise ImportError("sh %s is currently only supported on linux and osx. \
please install pbs 0.110 (http://pypi.python.org/pypi/pbs) for windows \
support." % __version__)


import sys
IS_PY3 = sys.version_info[0] == 3
MINOR_VER = sys.version_info[1]
IS_PY26 = sys.version_info[0] == 2 and MINOR_VER == 6

import traceback
import os
import re
import time
import getpass
from types import ModuleType, GeneratorType
from functools import partial
import inspect
import tempfile
import stat
import glob as glob_module
import ast
from contextlib import contextmanager
import pwd
import errno
from io import UnsupportedOperation

from locale import getpreferredencoding
DEFAULT_ENCODING = getpreferredencoding() or "UTF-8"

# normally i would hate this idea of using a global to signify whether we are
# running tests, because it breaks the assumption that what is running in the
# tests is what will run live, but we ONLY use this in a place that has no
# serious side-effects that could change anything.  as long as we do that, it
# should be ok
RUNNING_TESTS = bool(int(os.environ.get("SH_TESTS_RUNNING", "0")))

if IS_PY3:
    from io import StringIO
    ioStringIO = StringIO
    from io import BytesIO as cStringIO
    iocStringIO = cStringIO
    from queue import Queue, Empty

    # for some reason, python 3.1 removed the builtin "callable", wtf
    if not hasattr(__builtins__, "callable"):
        def callable(ob):
            return hasattr(ob, "__call__")
else:
    from StringIO import StringIO
    from cStringIO import OutputType as cStringIO
    from io import StringIO as ioStringIO
    from io import BytesIO as iocStringIO
    from Queue import Queue, Empty

IS_OSX = platform.system() == "Darwin"
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SH_LOGGER_NAME = __name__


import errno
import pty
import termios
import signal
import gc
import select
import threading
import tty
import fcntl
import struct
import resource
from collections import deque
import logging
import weakref


# a re-entrant lock for pushd.  this way, multiple threads that happen to use
# pushd will all see the current working directory for the duration of the
# with-context
PUSHD_LOCK = threading.RLock()


if hasattr(inspect, "signature"):
    def get_num_args(fn):
        return len(inspect.signature(fn).parameters)
else:
    def get_num_args(fn):
        return len(inspect.getargspec(fn).args)

if IS_PY3:
    raw_input = input
    unicode = str
    basestring = str
    long = int


_unicode_methods = set(dir(unicode()))


def encode_to_py3bytes_or_py2str(s):
    """ takes anything and attempts to return a py2 string or py3 bytes.  this
    is typically used when creating command + arguments to be executed via
    os.exec* """

    fallback_encoding = "utf8"

    if IS_PY3:
        # if we're already bytes, do nothing
        if isinstance(s, bytes):
            pass
        else:
            s = str(s)
            try:
                s = bytes(s, DEFAULT_ENCODING)
            except UnicodeEncodeError:
                s = bytes(s, fallback_encoding)
    else:
        # attempt to convert the thing to unicode from the system's encoding
        try:
            s = unicode(s, DEFAULT_ENCODING)
        # if the thing is already unicode, or it's a number, it can't be
        # coerced to unicode with an encoding argument, but if we leave out
        # the encoding argument, it will convert it to a string, then to unicode
        except TypeError:
            s = unicode(s)

        # now that we have guaranteed unicode, encode to our system encoding,
        # but attempt to fall back to something
        try:
            s = s.encode(DEFAULT_ENCODING)
        except:
            s = s.encode(fallback_encoding, "replace")
    return s


def _indent_text(text, num=4):
    lines = []
    for line in text.split("\n"):
        line = (" " * num) + line
        lines.append(line)
    return "\n".join(lines)


class ForkException(Exception):
    def __init__(self, orig_exc):
        tmpl = """

Original exception:
===================

%s
"""
        msg = tmpl % _indent_text(orig_exc)
        Exception.__init__(self, msg)


class ErrorReturnCodeMeta(type):
    """ a metaclass which provides the ability for an ErrorReturnCode (or
    derived) instance, imported from one sh module, to be considered the
    subclass of ErrorReturnCode from another module.  this is mostly necessary
    in the tests, where we do assertRaises, but the ErrorReturnCode that the
    program we're testing throws may not be the same class that we pass to
    assertRaises
    """
    def __subclasscheck__(self, o):
        other_bases = set([b.__name__ for b in o.__bases__])
        return self.__name__ in other_bases or o.__name__ == self.__name__


class ErrorReturnCode(Exception):
    __metaclass__ = ErrorReturnCodeMeta

    """ base class for all exceptions as a result of a command's exit status
    being deemed an error.  this base class is dynamically subclassed into
    derived classes with the format: ErrorReturnCode_NNN where NNN is the exit
    code number.  the reason for this is it reduces boiler plate code when
    testing error return codes:
    
        try:
            some_cmd()
        except ErrorReturnCode_12:
            print("couldn't do X")
            
    vs:
        try:
            some_cmd()
        except ErrorReturnCode as e:
            if e.exit_code == 12:
                print("couldn't do X")
    
    it's not much of a savings, but i believe it makes the code easier to read """

    truncate_cap = 750

    def __init__(self, full_cmd, stdout, stderr, truncate=True):
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr

        exc_stdout = self.stdout
        if truncate:
            exc_stdout = exc_stdout[:self.truncate_cap]
            out_delta = len(self.stdout) - len(exc_stdout)
            if out_delta:
                exc_stdout += ("... (%d more, please see e.stdout)" % out_delta).encode()

        exc_stderr = self.stderr
        if truncate:
            exc_stderr = exc_stderr[:self.truncate_cap]
            err_delta = len(self.stderr) - len(exc_stderr)
            if err_delta:
                exc_stderr += ("... (%d more, please see e.stderr)" % err_delta).encode()

        msg_tmpl = unicode("\n\n  RAN: {cmd}\n\n  STDOUT:\n{stdout}\n\n  STDERR:\n{stderr}")

        msg = msg_tmpl.format(
            cmd=self.full_cmd,
            stdout=exc_stdout.decode(DEFAULT_ENCODING, "replace"),
            stderr=exc_stderr.decode(DEFAULT_ENCODING, "replace")
        )

        super(ErrorReturnCode, self).__init__(msg)


class SignalException(ErrorReturnCode): pass
class TimeoutException(Exception):
    """ the exception thrown when a command is killed because a specified
    timeout (via _timeout) was hit """
    def __init__(self, exit_code):
        self.exit_code = exit_code
        super(Exception, self).__init__()

SIGNALS_THAT_SHOULD_THROW_EXCEPTION = (
    signal.SIGABRT,
    signal.SIGBUS,
    signal.SIGFPE,
    signal.SIGILL,
    signal.SIGINT,
    signal.SIGKILL,
    signal.SIGPIPE,
    signal.SIGQUIT,
    signal.SIGSEGV,
    signal.SIGTERM,
    signal.SIGSYS,
)


# we subclass AttributeError because:
# https://github.com/ipython/ipython/issues/2577
# https://github.com/amoffat/sh/issues/97#issuecomment-10610629
class CommandNotFound(AttributeError): pass




rc_exc_regex = re.compile("(ErrorReturnCode|SignalException)_((\d+)|SIG[a-zA-Z]+)")
rc_exc_cache = {}

SIGNAL_MAPPING = {}
for k,v in signal.__dict__.items():
    if re.match(r"SIG[a-zA-Z]+", k):
        SIGNAL_MAPPING[v] = k


def get_exc_from_name(name):
    """ takes an exception name, like:

        ErrorReturnCode_1
        SignalException_9
        SignalException_SIGHUP

    and returns the corresponding exception.  this is primarily used for
    importing exceptions from sh into user code, for instance, to capture those
    exceptions """

    exc = None
    try:
        return rc_exc_cache[name]
    except KeyError:
        m = rc_exc_regex.match(name)
        if m:
            base = m.group(1)
            rc_or_sig_name = m.group(2)

            if base == "SignalException":
                try:
                    rc = -int(rc_or_sig_name)
                except ValueError:
                    rc = -getattr(signal, rc_or_sig_name)
            else:
                rc = int(rc_or_sig_name)

            exc = get_rc_exc(rc)
    return exc


def get_rc_exc(rc):
    """ takes a exit code or negative signal number and produces an exception
    that corresponds to that return code.  positive return codes yield
    ErrorReturnCode exception, negative return codes yield SignalException

    we also cache the generated exception so that only one signal of that type
    exists, preserving identity """

    try:
        return rc_exc_cache[rc]
    except KeyError:
        pass

    if rc > 0:
        name = "ErrorReturnCode_%d" % rc
        base = ErrorReturnCode
    else:
        signame = SIGNAL_MAPPING[abs(rc)]
        name = "SignalException_" + signame
        base = SignalException

    exc = ErrorReturnCodeMeta(name, (base,), {"exit_code": rc})
    rc_exc_cache[rc] = exc
    return exc



# we monkey patch glob.  i'm normally generally against monkey patching, but i
# decided to do this really un-intrusive patch because we need a way to detect
# if a list that we pass into an sh command was generated from glob.  the reason
# being that glob returns an empty list if a pattern is not found, and so
# commands will treat the empty list as no arguments, which can be a problem,
# ie:
#
#   ls(glob("*.ojfawe"))
#
# ^ will show the contents of your home directory, because it's essentially
# running ls([]) which, as a process, is just "ls".
#
# so we subclass list and monkey patch the glob function.  nobody should be the
# wiser, but we'll have results that we can make some determinations on
_old_glob = glob_module.glob

class GlobResults(list):
    def __init__(self, path, results):
        self.path = path
        list.__init__(self, results)

def glob(path, *args, **kwargs):
    expanded = GlobResults(path, _old_glob(path, *args, **kwargs))
    return expanded

glob_module.glob = glob




def which(program, paths=None):
    """ takes a program name or full path, plus an optional collection of search
    paths, and returns the full path of the requested executable.  if paths is
    specified, it is the entire list of search paths, and the PATH env is not
    used at all.  otherwise, PATH env is used to look for the program """

    def is_exe(fpath):
        return (os.path.exists(fpath) and
                os.access(fpath, os.X_OK) and
                os.path.isfile(os.path.realpath(fpath)))

    found_path = None
    fpath, fname = os.path.split(program)

    # if there's a path component, then we've specified a path to the program,
    # and we should just test if that program is executable.  if it is, return
    if fpath:
        if is_exe(program):
            found_path = program

    # otherwise, we've just passed in the program name, and we need to search
    # the paths to find where it actually lives
    else:
        paths_to_search = []

        if isinstance(paths, (tuple, list)):
            paths_to_search.extend(paths)
        else:
            env_paths = os.environ.get("PATH", "").split(os.pathsep)
            paths_to_search.extend(env_paths)

        for path in paths_to_search:
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                found_path = exe_file
                break

    return found_path


def resolve_command_path(program):
    path = which(program)
    if not path:
        # our actual command might have a dash in it, but we can't call
        # that from python (we have to use underscores), so we'll check
        # if a dash version of our underscore command exists and use that
        # if it does
        if "_" in program:
            path = which(program.replace("_", "-"))
        if not path:
            return None
    return path


def resolve_command(name, baked_args=None):
    path = resolve_command_path(name)
    cmd = None
    if path:
        cmd = Command(path)
        if baked_args:
            cmd = cmd.bake(**baked_args)
    return cmd




class Logger(object):
    """ provides a memory-inexpensive logger.  a gotcha about python's builtin
    logger is that logger objects are never garbage collected.  if you create a
    thousand loggers with unique names, they'll sit there in memory until your
    script is done.  with sh, it's easy to create loggers with unique names if
    we want our loggers to include our command arguments.  for example, these
    are all unique loggers:
        
            ls -l
            ls -l /tmp
            ls /tmp

    so instead of creating unique loggers, and without sacrificing logging
    output, we use this class, which maintains as part of its state, the logging
    "context", which will be the very unique name.  this allows us to get a
    logger with a very general name, eg: "command", and have a unique name
    appended to it via the context, eg: "ls -l /tmp" """
    def __init__(self, name, context=None):
        self.name = name
        self.log = logging.getLogger("%s.%s" % (SH_LOGGER_NAME, name))
        self.set_context(context)

    def _format_msg(self, msg, *args):
        if self.context:
            msg = "%s: %s" % (self.context, msg)
        return msg % args

    def set_context(self, context):
        if context:
            context = context.replace("%", "%%")
        self.context = context or ""

    def get_child(self, name, context):
        new_name = self.name + "." + name
        new_context = self.context + "." + context
        l = Logger(new_name, new_context)
        return l

    def info(self, msg, *args):
        self.log.info(self._format_msg(msg, *args))

    def debug(self, msg, *args):
        self.log.debug(self._format_msg(msg, *args))

    def error(self, msg, *args):
        self.log.error(self._format_msg(msg, *args))

    def exception(self, msg, *args):
        self.log.exception(self._format_msg(msg, *args))


def default_logger_str(cmd, call_args, pid=None):
    if pid:
        s = "<Command %r, pid %d>" % (cmd, pid)
    else:
        s = "<Command %r>" % cmd
    return s



class RunningCommand(object):
    """ this represents an executing Command object.  it is returned as the
    result of __call__() being executed on a Command instance.  this creates a
    reference to a OProc instance, which is a low-level wrapper around the
    process that was exec'd

    this is the class that gets manipulated the most by user code, and so it
    implements various convenience methods and logical mechanisms for the
    underlying process.  for example, if a user tries to access a
    backgrounded-process's stdout/err, the RunningCommand object is smart enough
    to know to wait() on the process to finish first.  and when the process
    finishes, RunningCommand is smart enough to translate exit codes to
    exceptions. """

    # these are attributes that we allow to passthrough to OProc for
    _OProc_attr_whitelist = set((
        "signal",
        "terminate",
        "kill",
        "kill_group",
        "signal_group",
        "pid",
        "sid",
        "pgid",
        "ctty",

        "input_thread_exc",
        "output_thread_exc",
        "bg_thread_exc",
    ))

    def __init__(self, cmd, call_args, stdin, stdout, stderr):
        """
            cmd is an array, where each element is encoded as bytes (PY3) or str
            (PY2)
        """

        # self.ran is used for auditing what actually ran.  for example, in
        # exceptions, or if you just want to know what was ran after the
        # command ran
        #
        # here we're making a consistent unicode string out if our cmd.
        # we're also assuming (correctly, i think) that the command and its
        # arguments are the encoding we pass into _encoding, which falls back to
        # the system's encoding
        enc = call_args["encoding"]
        self.ran = " ".join([arg.decode(enc, "ignore") for arg in cmd])

        self.call_args = call_args
        self.cmd = cmd

        self.process = None
        self._process_completed = False
        should_wait = True
        spawn_process = True

        # this is used to track if we've already raised StopIteration, and if we
        # have, raise it immediately again if the user tries to call next() on
        # us.  https://github.com/amoffat/sh/issues/273
        self._stopped_iteration = False

        # with contexts shouldn't run at all yet, they prepend
        # to every command in the context
        if call_args["with"]:
            spawn_process = False
            get_prepend_stack().append(self)


        if call_args["piped"] or call_args["iter"] or call_args["iter_noblock"]:
            should_wait = False

        # we're running in the background, return self and let us lazily
        # evaluate
        if call_args["bg"]:
            should_wait = False

        # redirection
        if call_args["err_to_out"]:
            stderr = OProc.STDOUT

        done_callback = call_args["done"]
        if done_callback:
            call_args["done"] = partial(done_callback, self) 


        # set up which stream should write to the pipe
        # TODO, make pipe None by default and limit the size of the Queue
        # in oproc.OProc
        pipe = OProc.STDOUT
        if call_args["iter"] == "out" or call_args["iter"] is True:
            pipe = OProc.STDOUT
        elif call_args["iter"] == "err":
            pipe = OProc.STDERR

        if call_args["iter_noblock"] == "out" or call_args["iter_noblock"] is True:
            pipe = OProc.STDOUT
        elif call_args["iter_noblock"] == "err":
            pipe = OProc.STDERR

        # there's currently only one case where we wouldn't spawn a child
        # process, and that's if we're using a with-context with our command
        self._spawned_and_waited = False
        if spawn_process:
            log_str_factory = call_args["log_msg"] or default_logger_str
            logger_str = log_str_factory(self.ran, call_args)
            self.log = Logger("command", logger_str)

            self.log.info("starting process")

            if should_wait:
                self._spawned_and_waited = True

            # this lock is needed because of a race condition where a background
            # thread, created in the OProc constructor, may try to access
            # self.process, but it has not been assigned yet
            process_assign_lock = threading.Lock()
            with process_assign_lock:
                self.process = OProc(self, self.log, cmd, stdin, stdout, stderr,
                        self.call_args, pipe, process_assign_lock)

            logger_str = log_str_factory(self.ran, call_args, self.process.pid)
            self.log.set_context(logger_str)
            self.log.info("process started")

            if should_wait:
                self.wait()


    def wait(self):
        """ waits for the running command to finish.  this is called on all
        running commands, eventually, except for ones that run in the background
        """
        if not self._process_completed:
            self._process_completed = True

            exit_code = self.process.wait()
            if self.process.timed_out:
                # if we timed out, our exit code represents a signal, which is
                # negative, so let's make it positive to store in our
                # TimeoutException
                raise TimeoutException(-exit_code)

            else:
                self.handle_command_exit_code(exit_code)
        
                # if an iterable command is using an instance of OProc for its stdin,
                # wait on it.  the process is probably set to "piped", which means it
                # won't be waited on, which means exceptions won't propagate up to the
                # main thread.  this allows them to bubble up
                if self.process._stdin_process:
                    self.process._stdin_process.command.wait()

        self.log.info("process completed")
        return self


    def handle_command_exit_code(self, code):
        """ here we determine if we had an exception, or an error code that we
        weren't expecting to see.  if we did, we create and raise an exception
        """
        exc_class = get_exc_exit_code_would_raise(code, self.call_args["ok_code"])
        if exc_class:
            exc = exc_class(self.ran, self.process.stdout, self.process.stderr,
                    self.call_args["truncate_exc"])
            raise exc


    @property
    def stdout(self):
        self.wait()
        return self.process.stdout

    @property
    def stderr(self):
        self.wait()
        return self.process.stderr

    @property
    def exit_code(self):
        self.wait()
        return self.process.exit_code


    def __len__(self):
        return len(str(self))

    def __enter__(self):
        """ we don't actually do anything here because anything that should have
        been done would have been done in the Command.__call__ call.
        essentially all that has to happen is the comand be pushed on the
        prepend stack. """
        pass

    def __iter__(self):
        return self

    def next(self):
        """ allow us to iterate over the output of our command """

        if self._stopped_iteration:
            raise StopIteration()

        # we do this because if get blocks, we can't catch a KeyboardInterrupt
        # so the slight timeout allows for that.
        while True:
            try:
                chunk = self.process._pipe_queue.get(True, 0.001)
            except Empty:
                if self.call_args["iter_noblock"]:
                    return errno.EWOULDBLOCK
            else:
                if chunk is None:
                    self.wait()
                    self._stopped_iteration = True
                    raise StopIteration()
                try:
                    return chunk.decode(self.call_args["encoding"],
                        self.call_args["decode_errors"])
                except UnicodeDecodeError:
                    return chunk


    # python 3
    __next__ = next

    def __exit__(self, typ, value, traceback):
        if self.call_args["with"] and get_prepend_stack():
            get_prepend_stack().pop()

    def __str__(self):
        """ in python3, should return unicode.  in python2, should return a
        string of bytes """
        if IS_PY3:
            return self.__unicode__()
        else:
            return unicode(self).encode(self.call_args["encoding"])

    def __unicode__(self):
        """ a magic method defined for python2.  calling unicode() on a
        RunningCommand object will call this """
        if self.process and self.stdout:
            return self.stdout.decode(self.call_args["encoding"],
                self.call_args["decode_errors"])
        elif IS_PY3:
            return ""
        else:
            return unicode("")

    def __eq__(self, other):
        return unicode(self) == unicode(other)
    __hash__ = None  # Avoid DeprecationWarning in Python < 3

    def __contains__(self, item):
        return item in str(self)

    def __getattr__(self, p):
        # let these three attributes pass through to the OProc object
        if p in self._OProc_attr_whitelist:
            if self.process:
                return getattr(self.process, p)
            else:
                raise AttributeError

        # see if strings have what we're looking for.  we're looking at the
        # method names explicitly because we don't want to evaluate self unless
        # we absolutely have to, the reason being, in python2, hasattr swallows
        # exceptions, and if we try to run hasattr on a command that failed and
        # is being run with _iter=True, the command will be evaluated, throw an
        # exception, but hasattr will discard it
        if p in _unicode_methods:
            return getattr(unicode(self), p)

        raise AttributeError

    def __repr__(self):
        """ in python3, should return unicode.  in python2, should return a
        string of bytes """
        try:
            return str(self)
        except UnicodeDecodeError:
            if self.process:
                if self.stdout:
                    return repr(self.stdout)
            return repr("")

    def __long__(self):
        return long(str(self).strip())

    def __float__(self):
        return float(str(self).strip())

    def __int__(self):
        return int(str(self).strip())



def output_redirect_is_filename(out):
    return isinstance(out, basestring)


def get_prepend_stack():
    tl = Command.thread_local
    if not hasattr(tl, "_prepend_stack"):
        tl._prepend_stack = []
    return tl._prepend_stack


def special_kwarg_validator(kwargs, invalid_list):
    s1 = set(kwargs.keys())
    invalid_args = []

    for args in invalid_list:

        if callable(args):
            fn = args
            ret = fn(kwargs)
            invalid_args.extend(ret)

        else:
            args, error_msg = args

            if s1.issuperset(args):
                invalid_args.append((args, error_msg))

    return invalid_args


def get_fileno(ob):
    # in py2, this will return None.  in py3, it will return an method that
    # raises when called
    fileno_meth = getattr(ob, "fileno", None)

    fileno = None
    if fileno_meth:
        # py3 StringIO objects will report a fileno, but calling it will raise
        # an exception
        try:
            fileno = fileno_meth()
        except UnsupportedOperation:
            pass
    elif isinstance(ob, (int,long)) and ob >= 0:
        fileno = ob

    return fileno


def ob_is_tty(ob):
    """ checks if an object (like a file-like object) is a tty.  """
    fileno = get_fileno(ob)
    is_tty = False
    if fileno:
        is_tty = os.isatty(fileno)
    return is_tty

def ob_is_pipe(ob):
    fileno = get_fileno(ob)
    is_pipe = False
    if fileno:
        fd_stat = os.fstat(fileno)
        is_pipe = stat.S_ISFIFO(fd_stat.st_mode)
    return is_pipe


def tty_in_validator(kwargs):
    pairs = (("tty_in", "in"), ("tty_out", "out"))
    invalid = []
    for tty, std in pairs:
        if tty in kwargs and ob_is_tty(kwargs.get(std, None)):
            args = (tty, std)
            error = "`_%s` is a TTY already, so so it doesn't make sense \
to set up a TTY with `_%s`" % (std, tty)
            invalid.append((args, error))

    return invalid

def bufsize_validator(kwargs):
    """ a validator to prevent a user from saying that they want custom
    buffering when they're using an in/out object that will be os.dup'd to the
    process, and has its own buffering.  an example is a pipe or a tty.  it
    doesn't make sense to tell them to have a custom buffering, since the os
    controls this. """
    invalid = []

    in_ob = kwargs.get("in", None)
    out_ob = kwargs.get("out", None)

    in_buf = kwargs.get("in_bufsize", None)
    out_buf = kwargs.get("out_bufsize", None)

    in_no_buf = ob_is_tty(in_ob) or ob_is_pipe(in_ob)
    out_no_buf = ob_is_tty(out_ob) or ob_is_pipe(out_ob)

    err = "Can't specify an {target} bufsize if the {target} target is a pipe or TTY"

    if in_no_buf and in_buf is not None:
        invalid.append((("in", "in_bufsize"), err.format(target="in")))

    if out_no_buf and out_buf is not None:
        invalid.append((("out", "out_bufsize"), err.format(target="out")))

    return invalid


class Command(object):
    """ represents an un-run system program, like "ls" or "cd".  because it
    represents the program itself (and not a running instance of it), it should
    hold very little state.  in fact, the only state it does hold is baked
    arguments.
    
    when a Command object is called, the result that is returned is a
    RunningCommand object, which represents the Command put into an execution
    state. """
    thread_local = threading.local()

    _call_args = {
        "fg": False, # run command in foreground

        # run a command in the background.  commands run in the background
        # ignore SIGHUP and do not automatically exit when the parent process
        # ends
        "bg": False,

        # automatically report exceptions for background commands
        "bg_exc": True,

        "with": False, # prepend the command to every command after it
        "in": None,
        "out": None, # redirect STDOUT
        "err": None, # redirect STDERR
        "err_to_out": None, # redirect STDERR to STDOUT

        # stdin buffer size
        # 1 for line, 0 for unbuffered, any other number for that amount
        "in_bufsize": 0,
        # stdout buffer size, same values as above
        "out_bufsize": 1,
        "err_bufsize": 1,

        # this is how big the output buffers will be for stdout and stderr.
        # this is essentially how much output they will store from the process.
        # we use a deque, so if it overflows past this amount, the first items
        # get pushed off as each new item gets added.
        #
        # NOTICE
        # this is not a *BYTE* size, this is a *CHUNK* size...meaning, that if
        # you're buffering out/err at 1024 bytes, the internal buffer size will
        # be "internal_bufsize" CHUNKS of 1024 bytes
        "internal_bufsize": 3 * 1024 ** 2,

        "env": None,
        "piped": None,
        "iter": None,
        "iter_noblock": None,
        "ok_code": 0,
        "cwd": None,

        # the separator delimiting between a long-argument's name and its value
        # setting this to None will cause name and value to be two separate
        # arguments, like for short options
        # for example, --arg=derp, '=' is the long_sep
        "long_sep": "=",

        # the prefix used for long arguments
        "long_prefix": "--",

        # this is for programs that expect their input to be from a terminal.
        # ssh is one of those programs
        "tty_in": False,
        "tty_out": True,

        "encoding": DEFAULT_ENCODING,
        "decode_errors": "strict",

        # how long the process should run before it is auto-killed
        "timeout": None,
        "timeout_signal": signal.SIGKILL,

        # TODO write some docs on "long-running processes"
        # these control whether or not stdout/err will get aggregated together
        # as the process runs.  this has memory usage implications, so sometimes
        # with long-running processes with a lot of data, it makes sense to
        # set these to true
        "no_out": False,
        "no_err": False,
        "no_pipe": False,

        # if any redirection is used for stdout or stderr, internal buffering
        # of that data is not stored.  this forces it to be stored, as if
        # the output is being T'd to both the redirected destination and our
        # internal buffers
        "tee": None,

        # will be called when a process terminates regardless of exception
        "done": None,

        # a tuple (rows, columns) of the desired size of both the stdout and
        # stdin ttys, if ttys are being used
        "tty_size": (20, 80),

        # whether or not our exceptions should be truncated
        "truncate_exc": True,

        # a function to call after the child forks but before the process execs
        "preexec_fn": None,

        # UID to set after forking. Requires root privileges. Not supported on
        # Windows.
        "uid": None,

        # put the forked process in its own process session?
        "new_session": True,

        # pre-process args passed into __call__.  only really useful when used
        # in .bake()
        "arg_preprocess": None,

        # a callable that produces a log message from an argument tuple of the
        # command and the args
        "log_msg": None,
    }

    # this is a collection of validators to make sure the special kwargs make
    # sense
    _kwarg_validators = (
        (("fg", "bg"), "Command can't be run in the foreground and background"),
        (("fg", "err_to_out"), "Can't redirect STDERR in foreground mode"),
        (("err", "err_to_out"), "Stderr is already being redirected"),
        (("piped", "iter"), "You cannot iterate when this command is being piped"),
        (("piped", "no_pipe"), "Using a pipe doesn't make sense if you've \
disabled the pipe"),
        (("no_out", "iter"), "You cannot iterate over output if there is no \
output"),
        tty_in_validator,
        bufsize_validator,
    )


    def __init__(self, path, search_paths=None):
        found = which(path, search_paths)

        self._path = encode_to_py3bytes_or_py2str("")

        # is the command baked (aka, partially applied)?
        self._partial = False
        self._partial_baked_args = []
        self._partial_call_args = {}

        # bugfix for functools.wraps.  issue #121
        self.__name__ = str(self)

        if not found:
            raise CommandNotFound(path)

        # the reason why we set the values early in the constructor, and again
        # here, is for people who have tools that inspect the stack on
        # exception.  if CommandNotFound is raised, we need self._path and the
        # other attributes to be set correctly, so repr() works when they're
        # inspecting the stack.  issue #304
        self._path = encode_to_py3bytes_or_py2str(found) 
        self.__name__ = str(self)


    def __getattribute__(self, name):
        # convenience
        getattr = partial(object.__getattribute__, self)
        val = None

        if name.startswith("_"):
            val = getattr(name)

        elif name == "bake":
            val = getattr("bake")

        # here we have a way of getting past shadowed subcommands.  for example,
        # if "git bake" was a thing, we wouldn't be able to do `git.bake()`
        # because `.bake()` is already a method.  so we allow `git.bake_()`
        elif name.endswith("_"):
            name = name[:-1]

        if val is None:
            val = getattr("bake")(name)

        return val


    @staticmethod
    def _extract_call_args(kwargs):
        """ takes kwargs that were passed to a command's __call__ and extracts
        out the special keyword arguments, we return a tuple of special keyword
        args, and kwargs that will go to the execd command """

        kwargs = kwargs.copy()
        call_args = {}
        for parg, default in Command._call_args.items():
            key = "_" + parg

            if key in kwargs:
                call_args[parg] = kwargs[key]
                del kwargs[key]

        invalid_kwargs = special_kwarg_validator(call_args,
                Command._kwarg_validators)

        if invalid_kwargs:
            exc_msg = []
            for args, error_msg in invalid_kwargs:
                exc_msg.append("  %r: %s" % (args, error_msg))
            exc_msg = "\n".join(exc_msg)
            raise TypeError("Invalid special arguments:\n\n%s\n" % exc_msg)

        return call_args, kwargs


    # TODO needs documentation
    def bake(self, *args, **kwargs):
        fn = type(self)(self._path)
        fn._partial = True

        call_args, kwargs = self._extract_call_args(kwargs)

        pruned_call_args = call_args
        for k, v in Command._call_args.items():
            try:
                if pruned_call_args[k] == v:
                    del pruned_call_args[k]
            except KeyError:
                continue

        fn._partial_call_args.update(self._partial_call_args)
        fn._partial_call_args.update(pruned_call_args)
        fn._partial_baked_args.extend(self._partial_baked_args)
        sep = pruned_call_args.get("long_sep", self._call_args["long_sep"])
        prefix = pruned_call_args.get("long_prefix",
                self._call_args["long_prefix"])
        fn._partial_baked_args.extend(compile_args(args, kwargs, sep, prefix))
        return fn

    def __str__(self):
        """ in python3, should return unicode.  in python2, should return a
        string of bytes """
        if IS_PY3:
            return self.__unicode__()
        else:
            return self.__unicode__().encode(DEFAULT_ENCODING)


    def __eq__(self, other):
        return str(self) == str(other)

    __hash__ = None  # Avoid DeprecationWarning in Python < 3


    def __repr__(self):
        """ in python3, should return unicode.  in python2, should return a
        string of bytes """
        return "<Command %r>" % str(self)


    def __unicode__(self):
        """ a magic method defined for python2.  calling unicode() on a
        self will call this """
        baked_args = " ".join(item.decode(DEFAULT_ENCODING) for item in self._partial_baked_args)
        if baked_args:
            baked_args = " " + baked_args
        return self._path.decode(DEFAULT_ENCODING) + baked_args

    def __enter__(self):
        self(_with=True)

    def __exit__(self, typ, value, traceback):
        get_prepend_stack().pop()


    def __call__(self, *args, **kwargs):

        kwargs = kwargs.copy()
        args = list(args)

        # this will hold our final command, including arguments, that will be
        # execd
        cmd = []

        # this will hold a complete mapping of all our special keyword arguments
        # and their values
        call_args = Command._call_args.copy()

        # aggregate any 'with' contexts
        for prepend in get_prepend_stack():
            pcall_args = prepend.call_args.copy()
            # don't pass the 'with' call arg
            pcall_args.pop("with", None)

            call_args.update(pcall_args)
            cmd.extend(prepend.cmd)

        cmd.append(self._path)

        # do we have an argument pre-processor?  if so, run it.  we need to do
        # this early, so that args, kwargs are accurate
        preprocessor = self._partial_call_args.get("arg_preprocess", None)
        if preprocessor:
            args, kwargs = preprocessor(args, kwargs)

        # here we extract the special kwargs and override any
        # special kwargs from the possibly baked command
        extracted_call_args, kwargs = self._extract_call_args(kwargs)

        call_args.update(self._partial_call_args)
        call_args.update(extracted_call_args)


        # handle a None.  this is added back only to not break the api in the
        # 1.* version.  TODO remove this in 2.0, as "ok_code", if specified,
        # should always be a definitive value or list of values, and None is
        # ambiguous
        if call_args["ok_code"] is None:
            call_args["ok_code"] = 0

        if not getattr(call_args["ok_code"], "__iter__", None):
            call_args["ok_code"] = [call_args["ok_code"]]


        # check if we're piping via composition
        stdin = call_args["in"]
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, RunningCommand):
                if first_arg.call_args["piped"]:
                    stdin = first_arg.process
                else:
                    stdin = first_arg.process._pipe_queue

            else:
                args.insert(0, first_arg)

        processed_args = compile_args(args, kwargs, call_args["long_sep"],
                call_args["long_prefix"])

        # makes sure our arguments are broken up correctly
        split_args = self._partial_baked_args + processed_args

        final_args = split_args

        cmd.extend(final_args)

        # if we're running in foreground mode, we need to completely bypass
        # launching a RunningCommand and OProc and just do a spawn
        if call_args["fg"]:
            if call_args["env"] is None:
                launch = lambda: os.spawnv(os.P_WAIT, cmd[0], cmd)
            else:
                launch = lambda: os.spawnve(os.P_WAIT, cmd[0], cmd, call_args["env"])

            exit_code = launch()
            exc_class = get_exc_exit_code_would_raise(exit_code, call_args["ok_code"])
            if exc_class:
                if IS_PY3:
                    ran = " ".join([arg.decode(DEFAULT_ENCODING, "ignore") for arg in cmd])
                else:
                    ran = " ".join(cmd)
                exc = exc_class(ran, b"", b"", call_args["truncate_exc"])
                raise exc
            return None


        # stdout redirection
        stdout = call_args["out"]
        if output_redirect_is_filename(stdout):
            stdout = open(str(stdout), "wb")

        # stderr redirection
        stderr = call_args["err"]
        if output_redirect_is_filename(stderr):
            stderr = open(str(stderr), "wb")
    
        return RunningCommand(cmd, call_args, stdin, stdout, stderr)


def compile_args(args, kwargs, sep, prefix):
    """ takes args and kwargs, as they were passed into the command instance
    being executed with __call__, and compose them into a flat list that
    will eventually be fed into exec.  example:

    with this call:

        sh.ls("-l", "/tmp", color="never")

    this function receives

        args = ['-l', '/tmp']
        kwargs = {'color': 'never'}

    and produces

        ['-l', '/tmp', '--color=never']
        
    """
    processed_args = []
    encode = encode_to_py3bytes_or_py2str

    # aggregate positional args
    for arg in args:
        if isinstance(arg, (list, tuple)):
            if isinstance(arg, GlobResults) and not arg:
                arg = [arg.path]

            for sub_arg in arg:
                processed_args.append(encode(sub_arg))
        elif isinstance(arg, dict):
            processed_args += aggregate_keywords(arg, sep, prefix, raw=True)
        else:
            processed_args.append(encode(arg))

    # aggregate the keyword arguments
    processed_args += aggregate_keywords(kwargs, sep, prefix)

    return processed_args


def aggregate_keywords(keywords, sep, prefix, raw=False):
    """ take our keyword arguments, and a separator, and compose the list of
    flat long (and short) arguments.  example

        {'color': 'never', 't': True, 'something': True} with sep '='

    becomes

        ['--color=never', '-t', '--something']

    the `raw` argument indicates whether or not we should leave the argument
    name alone, or whether we should replace "_" with "-".  if we pass in a
    dictionary, like this:

        sh.command({"some_option": 12})

    then `raw` gets set to True, because we want to leave the key as-is, to
    produce:

        ['--some_option=12']

    but if we just use a command's kwargs, `raw` is False, which means this:

        sh.command(some_option=12)

    becomes:

        ['--some-option=12']

    eessentially, using kwargs is a convenience, but it lacks the ability to
    put a '-' in the name, so we do the replacement of '_' to '-' for you.
    but when you really don't want that to happen, you should use a
    dictionary instead with the exact names you want
    """

    processed = []
    encode = encode_to_py3bytes_or_py2str

    for k, v in keywords.items():
        # we're passing a short arg as a kwarg, example:
        # cut(d="\t")
        if len(k) == 1:
            if v is not False:
                processed.append(encode("-" + k))
                if v is not True:
                    processed.append(encode(v))

        # we're doing a long arg
        else:
            if not raw:
                k = k.replace("_", "-")

            if v is True:
                processed.append(encode("--" + k))
            elif v is False:
                pass
            elif sep is None or sep == " ":
                processed.append(encode(prefix + k))
                processed.append(encode(v))
            else:
                arg = encode("%s%s%s%s" % (prefix, k, sep, v))
                processed.append(arg)

    return processed


def _start_daemon_thread(fn, name, exc_queue, *args):
    def wrap(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception as e:
            exc_queue.put(e)
            raise

    thrd = threading.Thread(target=wrap, name=name, args=args)
    thrd.daemon = True
    thrd.start()
    return thrd


def setwinsize(fd, rows_cols):
    """ set the terminal size of a tty file descriptor.  borrowed logic
    from pexpect.py """
    rows, cols = rows_cols
    TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)

    s = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(fd, TIOCSWINSZ, s)

def construct_streamreader_callback(process, handler):
    """ here we're constructing a closure for our streamreader callback.  this
    is used in the case that we pass a callback into _out or _err, meaning we
    want to our callback to handle each bit of output

    we construct the closure based on how many arguments it takes.  the reason
    for this is to make it as easy as possible for people to use, without
    limiting them.  a new user will assume the callback takes 1 argument (the
    data).  as they get more advanced, they may want to terminate the process,
    or pass some stdin back, and will realize that they can pass a callback of
    more args """


    # implied arg refers to the "self" that methods will pass in.  we need to
    # account for this implied arg when figuring out what function the user
    # passed in based on number of args
    implied_arg = 0

    partial_args = 0
    handler_to_inspect = handler

    if isinstance(handler, partial):
        partial_args = len(handler.args)
        handler_to_inspect = handler.func

    if inspect.ismethod(handler_to_inspect):
        implied_arg = 1
        num_args = get_num_args(handler_to_inspect)

    else:
        if inspect.isfunction(handler_to_inspect):
            num_args = get_num_args(handler_to_inspect)

        # is an object instance with __call__ method
        else:
            implied_arg = 1
            num_args = get_num_args(handler_to_inspect.__call__)


    net_args = num_args - implied_arg - partial_args

    handler_args = ()

    # just the chunk
    if net_args == 1:
        handler_args = ()

    # chunk, stdin
    if net_args == 2:
        handler_args = (process.stdin,)

    # chunk, stdin, process
    elif net_args == 3:
        # notice we're only storing a weakref, to prevent cyclic references
        # (where the process holds a streamreader, and a streamreader holds a
        # handler-closure with a reference to the process
        handler_args = (process.stdin, weakref.ref(process))

    def fn(chunk):
        # this is pretty ugly, but we're evaluating the process at call-time,
        # because it's a weakref
        args = handler_args
        if len(args) == 2:
            args = (handler_args[0], handler_args[1]())
        return handler(chunk, *args)

    return fn


def get_exc_exit_code_would_raise(exit_code, ok_codes):
    exc = None
    success = exit_code in ok_codes
    bad_sig = -exit_code in SIGNALS_THAT_SHOULD_THROW_EXCEPTION

    if not success or bad_sig:
        exc = get_rc_exc(exit_code)
    return exc


def handle_process_exit_code(exit_code):
    """ this should only ever be called once for each child process """
    # if we exited from a signal, let our exit code reflect that
    if os.WIFSIGNALED(exit_code):
        exit_code = -os.WTERMSIG(exit_code)
    # otherwise just give us a normal exit code
    elif os.WIFEXITED(exit_code):
        exit_code = os.WEXITSTATUS(exit_code)
    else:
        raise RuntimeError("Unknown child exit status!")

    return exit_code


def no_interrupt(syscall, *args, **kwargs):
    """ a helper for making system calls immune to EINTR """
    ret = None

    while True:
        try:
            ret = syscall(*args, **kwargs)
        except OSError as e:
            if e.errno == errno.EINTR:
                continue
            else:
                raise
        else:
            break

    return ret


class OProc(object):
    """ this class is instantiated by RunningCommand for a command to be exec'd.
    it handles all the nasty business involved with correctly setting up the
    input/output to the child process.  it gets its name for subprocess.Popen
    (process open) but we're calling ours OProc (open process) """

    _default_window_size = (24, 80)

    # used in redirecting
    STDOUT = -1
    STDERR = -2

    def __init__(self, command, parent_log, cmd, stdin, stdout, stderr,
            call_args, pipe, process_assign_lock):
        """
            cmd is the full string that will be exec'd.  it includes the program
            name and all its arguments

            stdin, stdout, stderr are what the child will use for standard
            input/output/err

            call_args is a mapping of all the special keyword arguments to apply
            to the child process
        """
        self.command = command
        self.call_args = call_args

        # convenience
        ca = self.call_args

        if ca["uid"] is not None:
            if os.getuid() != 0:
                raise RuntimeError("UID setting requires root privileges")

            target_uid = ca["uid"]

            pwrec = pwd.getpwuid(ca["uid"])
            target_gid = pwrec.pw_gid

        # I had issues with getting 'Input/Output error reading stdin' from dd,
        # until I set _tty_out=False
        if ca["piped"]:
            ca["tty_out"] = False

        self._stdin_process = None


        # if the objects that we are passing to the OProc happen to be a
        # file-like object that is a tty, for example `sys.stdin`, then, later
        # on in this constructor, we're going to skip out on setting up pipes
        # and pseudoterminals for those endpoints
        stdin_is_tty_or_pipe = ob_is_tty(stdin) or ob_is_pipe(stdin)
        stdout_is_tty_or_pipe = ob_is_tty(stdout) or ob_is_pipe(stdout)
        stderr_is_tty_or_pipe = ob_is_tty(stderr) or ob_is_pipe(stderr)

        # if we're passing in a custom stdout/out/err value, we obviously have
        # to force not using single_tty
        custom_in_out_err = stdin or stdout or stderr

        single_tty = (ca["tty_in"] and ca["tty_out"]) and not custom_in_out_err

        # this logic is a little convoluted, but basically this top-level
        # if/else is for consolidating input and output TTYs into a single
        # TTY.  this is the only way some secure programs like ssh will
        # output correctly (is if stdout and stdin are both the same TTY)
        if single_tty:
            self._stdin_read_fd, self._stdin_write_fd = pty.openpty()

            self._stdout_read_fd = os.dup(self._stdin_read_fd)
            self._stdout_write_fd = os.dup(self._stdin_write_fd)

            self._stderr_read_fd = os.dup(self._stdin_read_fd)
            self._stderr_write_fd = os.dup(self._stdin_write_fd)

        # do not consolidate stdin and stdout.  this is the most common use-
        # case
        else:
            # this check here is because we may be doing piping and so our stdin
            # might be an instance of OProc
            if isinstance(stdin, OProc) and stdin.call_args["piped"]:
                self._stdin_write_fd = stdin._pipe_fd
                self._stdin_read_fd = None
                self._stdin_process = stdin

            elif stdin_is_tty_or_pipe:
                self._stdin_write_fd = os.dup(get_fileno(stdin))
                self._stdin_read_fd = None

            elif ca["tty_in"]:
                self._stdin_read_fd, self._stdin_write_fd = pty.openpty()

            # tty_in=False is the default
            else:
                self._stdin_write_fd, self._stdin_read_fd = os.pipe()


            if stdout_is_tty_or_pipe:
                self._stdout_write_fd = os.dup(get_fileno(stdout))
                self._stdout_read_fd = None

            # tty_out=True is the default
            elif ca["tty_out"]:
                self._stdout_read_fd, self._stdout_write_fd = pty.openpty()

            else:
                self._stdout_read_fd, self._stdout_write_fd = os.pipe()

            # unless STDERR is going to STDOUT, it ALWAYS needs to be a pipe,
            # and never a PTY.  the reason for this is not totally clear to me,
            # but it has to do with the fact that if STDERR isn't set as the
            # CTTY (because STDOUT is), the STDERR buffer won't always flush
            # by the time the process exits, and the data will be lost.
            # i've only seen this on OSX.
            if stderr is OProc.STDOUT:
                self._stderr_read_fd = os.dup(self._stdout_read_fd)
                self._stderr_write_fd = os.dup(self._stdout_write_fd)

            elif stderr_is_tty_or_pipe:
                self._stderr_write_fd = os.dup(get_fileno(stderr))
                self._stderr_read_fd = None

            else:
                self._stderr_read_fd, self._stderr_write_fd = os.pipe()


        piped = ca["piped"]
        self._pipe_fd = None
        if piped:
            fd_to_use = self._stdout_read_fd
            if piped == "err":
                fd_to_use = self._stderr_read_fd
            self._pipe_fd = os.dup(fd_to_use)


        new_session = ca["new_session"]
        needs_ctty = ca["tty_in"] and new_session

        self.ctty = None
        if needs_ctty:
            self.ctty = os.ttyname(self._stdin_write_fd)

        # this is a hack, but what we're doing here is intentionally throwing an
        # OSError exception if our child processes's directory doesn't exist,
        # but we're doing it BEFORE we fork.  the reason for before the fork is
        # error handling.  i'm currently too lazy to implement what
        # subprocess.py did and set up a error pipe to handle exceptions that
        # happen in the child between fork and exec.  it has only been seen in
        # the wild for a missing cwd, so we'll handle it here.
        cwd = ca["cwd"]
        if cwd is not None and not os.path.exists(cwd):
            os.chdir(cwd)

        gc_enabled = gc.isenabled()
        if gc_enabled:
            gc.disable()

        # for synchronizing
        session_pipe_read, session_pipe_write = os.pipe()
        exc_pipe_read, exc_pipe_write = os.pipe()

        # this pipe is for synchronzing with the child that the parent has
        # closed its in/out/err fds.  this is a bug on OSX (but not linux),
        # where we can lose output sometimes, due to a race, if we do
        # os.close(self._stdout_write_fd) in the parent after the child starts
        # writing.
        if IS_OSX:
            close_pipe_read, close_pipe_write = os.pipe()


        # session id, group id, process id
        self.sid = None
        self.pgid = None
        self.pid = os.fork()

        # child
        if self.pid == 0: # pragma: no cover
            if IS_OSX:
                os.read(close_pipe_read, 1)
                os.close(close_pipe_read)
                os.close(close_pipe_write)

            try:
                # ignoring SIGHUP lets us persist even after the parent process
                # exits.  only ignore if we're backgrounded
                if ca["bg"] is True:
                    signal.signal(signal.SIGHUP, signal.SIG_IGN)

                # put our forked process in a new session?  this will relinquish
                # any control of our inherited CTTY and also make our parent
                # process init
                if new_session:
                    os.setsid()
                # if we're not going in a new session, we should go in a new
                # process group.  this way, our process, and any children it
                # spawns, are alone, contained entirely in one group.  if we
                # didn't do this, and didn't use a new session, then our exec'd
                # process *could* exist in the same group as our python process,
                # depending on how we launch the process (from a shell, or some
                # other way)
                else:
                    os.setpgrp()

                sid = os.getsid(0)
                pgid = os.getpgid(0)
                payload = ("%d,%d" % (sid, pgid)).encode(DEFAULT_ENCODING)
                os.write(session_pipe_write, payload)

                if ca["tty_out"] and not stdout_is_tty_or_pipe and not single_tty:
                    # set raw mode, so there isn't any weird translation of
                    # newlines to \r\n and other oddities.  we're not outputting
                    # to a terminal anyways
                    #
                    # we HAVE to do this here, and not in the parent process,
                    # because we have to guarantee that this is set before the
                    # child process is run, and we can't do it twice.
                    tty.setraw(self._stdout_write_fd)


                # if the parent-side fd for stdin exists, close it.  the case
                # where it may not exist is if we're using piping
                if self._stdin_read_fd:
                    os.close(self._stdin_read_fd)

                if self._stdout_read_fd:
                    os.close(self._stdout_read_fd)

                if self._stderr_read_fd:
                    os.close(self._stderr_read_fd)

                os.close(session_pipe_read)
                os.close(exc_pipe_read)

                if cwd:
                    os.chdir(cwd)

                os.dup2(self._stdin_write_fd, 0)
                os.dup2(self._stdout_write_fd, 1)
                os.dup2(self._stderr_write_fd, 2)


                # set our controlling terminal, but only if we're using a tty
                # for stdin.  it doesn't make sense to have a ctty otherwise
                if needs_ctty:
                    tmp_fd = os.open(os.ttyname(0), os.O_RDWR)
                    os.close(tmp_fd)

                if ca["tty_out"] and not stdout_is_tty_or_pipe:
                    setwinsize(1, ca["tty_size"])

                if ca["uid"] is not None:
                    os.setgid(target_gid)
                    os.setuid(target_uid)

                preexec_fn = ca["preexec_fn"]
                if callable(preexec_fn):
                    preexec_fn()


                # don't inherit file descriptors
                max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                os.closerange(3, max_fd)

                # actually execute the process
                if ca["env"] is None:
                    os.execv(cmd[0], cmd)
                else:
                    os.execve(cmd[0], cmd, ca["env"])

            # we must ensure that we carefully exit the child process on
            # exception, otherwise the parent process code will be executed
            # twice on exception https://github.com/amoffat/sh/issues/202
            #
            # if your parent process experiences an exit code 255, it is most
            # likely that an exception occurred between the fork of the child
            # and the exec.  this should be reported.
            except:
                # some helpful debugging
                try:
                    tb = traceback.format_exc().encode("utf8", "ignore")
                    os.write(exc_pipe_write, tb)

                finally:
                    os._exit(255)

        # parent
        else:
            if gc_enabled:
                gc.enable()

            os.close(self._stdin_write_fd)
            os.close(self._stdout_write_fd)
            os.close(self._stderr_write_fd)

            # tell our child process that we've closed our write_fds, so it is
            # ok to proceed towards exec.  see the comment where this pipe is
            # opened, for why this is necessary
            if IS_OSX:
                os.close(close_pipe_read)
                os.write(close_pipe_write, str(1).encode(DEFAULT_ENCODING))
                os.close(close_pipe_write)

            os.close(exc_pipe_write)
            fork_exc = os.read(exc_pipe_read, 1024**2)
            os.close(exc_pipe_read)
            if fork_exc:
                fork_exc = fork_exc.decode(DEFAULT_ENCODING)
                raise ForkException(fork_exc)

            os.close(session_pipe_write)
            sid, pgid = os.read(session_pipe_read,
                    1024).decode(DEFAULT_ENCODING).split(",")
            os.close(session_pipe_read)
            self.sid = int(sid)
            self.pgid = int(pgid)

            # used to determine what exception to raise.  if our process was
            # killed via a timeout counter, we'll raise something different than
            # a SIGKILL exception
            self.timed_out = False

            self.started = time.time()
            self.cmd = cmd

            # exit code should only be manipulated from within self._wait_lock
            # to prevent race conditions
            self.exit_code = None

            self.stdin = stdin or Queue()

            # _pipe_queue is used internally to hand off stdout from one process
            # to another.  by default, all stdout from a process gets dumped
            # into this pipe queue, to be consumed in real time (hence the
            # thread-safe Queue), or at a potentially later time
            self._pipe_queue = Queue()

            # this is used to prevent a race condition when we're waiting for
            # a process to end, and the OProc's internal threads are also checking
            # for the processes's end
            self._wait_lock = threading.Lock()

            # these are for aggregating the stdout and stderr.  we use a deque
            # because we don't want to overflow
            self._stdout = deque(maxlen=ca["internal_bufsize"])
            self._stderr = deque(maxlen=ca["internal_bufsize"])

            if ca["tty_in"] and not stdin_is_tty_or_pipe:
                setwinsize(self._stdin_read_fd, ca["tty_size"])


            self.log = parent_log.get_child("process", repr(self))


            self.log.debug("started process")

            # disable echoing, but only if it's a tty that we created ourselves
            if ca["tty_in"] and not stdin_is_tty_or_pipe:
                attr = termios.tcgetattr(self._stdin_read_fd)
                attr[3] &= ~termios.ECHO
                termios.tcsetattr(self._stdin_read_fd, termios.TCSANOW, attr)

            # we're only going to create a stdin thread iff we have potential
            # for stdin to come in.  this would be through a stdout callback or
            # through an object we've passed in for stdin
            potentially_has_input = callable(stdout) or stdin

            # this represents the connection from a Queue object (or whatever
            # we're using to feed STDIN) to the process's STDIN fd
            self._stdin_stream = None
            if self._stdin_read_fd and potentially_has_input:
                log = self.log.get_child("streamwriter", "stdin")
                self._stdin_stream =  StreamWriter(log, self._stdin_read_fd,
                        self.stdin, ca["in_bufsize"], ca["encoding"],
                        ca["tty_in"])

            stdout_pipe = None
            if pipe is OProc.STDOUT and not ca["no_pipe"]:
                stdout_pipe = self._pipe_queue


            # this represents the connection from a process's STDOUT fd to
            # wherever it has to go, sometimes a pipe Queue (that we will use
            # to pipe data to other processes), and also an internal deque
            # that we use to aggregate all the output
            save_stdout = not ca["no_out"] and \
                (ca["tee"] in (True, "out") or stdout is None)


            pipe_out = ca["piped"] in ("out", True)
            pipe_err = ca["piped"] in ("err",)

            # if we're piping directly into another process's filedescriptor, we
            # bypass reading from the stdout stream altogether, because we've
            # already hooked up this processes's stdout fd to the other
            # processes's stdin fd
            self._stdout_stream = None
            if not pipe_out and self._stdout_read_fd:
                if callable(stdout):
                    stdout = construct_streamreader_callback(self, stdout)
                self._stdout_stream = \
                        StreamReader(
                                self.log.get_child("streamreader", "stdout"),
                                self._stdout_read_fd, stdout, self._stdout,
                                ca["out_bufsize"], ca["encoding"],
                                ca["decode_errors"], stdout_pipe,
                                save_data=save_stdout)

            elif self._stdout_read_fd:
                os.close(self._stdout_read_fd)


            # if stderr is going to one place (because it's grouped with stdout,
            # or we're dealing with a single tty), then we don't actually need a
            # stream reader for stderr, because we've already set one up for
            # stdout above
            self._stderr_stream = None
            if stderr is not OProc.STDOUT and not single_tty and not pipe_err \
                    and self._stderr_read_fd:

                stderr_pipe = None
                if pipe is OProc.STDERR and not ca["no_pipe"]:
                    stderr_pipe = self._pipe_queue

                save_stderr = not ca["no_err"] and \
                    (ca["tee"] in ("err",) or stderr is None)

                if callable(stderr):
                    stderr = construct_streamreader_callback(self, stderr)

                self._stderr_stream = StreamReader(Logger("streamreader"),
                        self._stderr_read_fd, stderr, self._stderr,
                        ca["err_bufsize"], ca["encoding"], ca["decode_errors"],
                        stderr_pipe, save_data=save_stderr)

            elif self._stderr_read_fd:
                os.close(self._stderr_read_fd)


            def timeout_fn():
                self.timed_out = True
                self.signal(ca["timeout_signal"])


            self._timeout_event = None
            self._timeout_timer = None
            if ca["timeout"]:
                self._timeout_event = threading.Event()
                self._timeout_timer = threading.Timer(ca["timeout"],
                        self._timeout_event.set)
                self._timeout_timer.start()

            # this is for cases where we know that the RunningCommand that was
            # launched was not .wait()ed on to complete.  in those unique cases,
            # we allow the thread that processes output to report exceptions in
            # that thread.  it's important that we only allow reporting of the
            # exception, and nothing else (like the additional stuff that
            # RunningCommand.wait() does), because we want the exception to be
            # re-raised in the future, if we DO call .wait()
            handle_exit_code = None
            if not self.command._spawned_and_waited and ca["bg_exc"]:
                def fn(exit_code):
                    with process_assign_lock:
                        return self.command.handle_command_exit_code(exit_code)
                handle_exit_code = fn

            self._quit_threads = threading.Event()

            thread_name = "background thread for pid %d" % self.pid
            self._bg_thread_exc_queue = Queue(1)
            self._background_thread = _start_daemon_thread(background_thread,
                    thread_name, self._bg_thread_exc_queue, timeout_fn,
                    self._timeout_event, handle_exit_code, self.is_alive,
                    self._quit_threads)


            # start the main io threads. stdin thread is not needed if we are
            # connecting from another process's stdout pipe
            self._input_thread = None
            self._input_thread_exc_queue = Queue(1)
            if self._stdin_stream:
                close_before_term = not needs_ctty
                thread_name = "STDIN thread for pid %d" % self.pid
                self._input_thread = _start_daemon_thread(input_thread,
                        thread_name, self._input_thread_exc_queue, self.log,
                        self._stdin_stream, self.is_alive, self._quit_threads,
                        close_before_term)


            # this event is for cases where the subprocess that we launch
            # launches its OWN subprocess and dups the stdout/stderr fds to that
            # new subprocess.  in that case, stdout and stderr will never EOF,
            # so our output_thread will never finish and will hang.  this event
            # prevents that hanging
            self._stop_output_event = threading.Event()

            self._output_thread_exc_queue = Queue(1)
            thread_name = "STDOUT/ERR thread for pid %d" % self.pid
            self._output_thread = _start_daemon_thread(output_thread,
                    thread_name, self._output_thread_exc_queue, self.log,
                    self._stdout_stream, self._stderr_stream,
                    self._timeout_event, self.is_alive, self._quit_threads,
                    self._stop_output_event)


    def __repr__(self):
        return "<Process %d %r>" % (self.pid, self.cmd[:500])


    # these next 3 properties are primary for tests
    @property
    def output_thread_exc(self):
        exc = None
        try:
            exc = self._output_thread_exc_queue.get(False)
        except Empty:
            pass
        return exc

    @property
    def input_thread_exc(self):
        exc = None
        try:
            exc = self._input_thread_exc_queue.get(False)
        except Empty:
            pass
        return exc

    @property
    def bg_thread_exc(self):
        exc = None
        try:
            exc = self._bg_thread_exc_queue.get(False)
        except Empty:
            pass
        return exc


    def change_in_bufsize(self, buf):
        self._stdin_stream.stream_bufferer.change_buffering(buf)

    def change_out_bufsize(self, buf):
        self._stdout_stream.stream_bufferer.change_buffering(buf)

    def change_err_bufsize(self, buf):
        self._stderr_stream.stream_bufferer.change_buffering(buf)



    @property
    def stdout(self):
        return "".encode(self.call_args["encoding"]).join(self._stdout)

    @property
    def stderr(self):
        return "".encode(self.call_args["encoding"]).join(self._stderr)

    def get_pgid(self):
        """ return the CURRENT group id of the process. this differs from
        self.pgid in that this refects the current state of the process, where
        self.pgid is the group id at launch """
        return os.getpgid(self.pid)

    def get_sid(self):
        """ return the CURRENT session id of the process. this differs from
        self.sid in that this refects the current state of the process, where
        self.sid is the session id at launch """
        return os.getsid(self.pid)

    def signal_group(self, sig):
        self.log.debug("sending signal %d to group", sig)
        os.killpg(self.get_pgid(), sig)

    def signal(self, sig):
        self.log.debug("sending signal %d", sig)
        os.kill(self.pid, sig)

    def kill_group(self):
        self.log.debug("killing group")
        self.signal_group(signal.SIGKILL)

    def kill(self):
        self.log.debug("killing")
        self.signal(signal.SIGKILL)

    def terminate(self):
        self.log.debug("terminating")
        self.signal(signal.SIGTERM)


    def is_alive(self):
        """ polls if our child process has completed, without blocking.  this
        method has side-effects, such as setting our exit_code, if we happen to
        see our child exit while this is running """

        if self.exit_code is not None:
            return False, self.exit_code

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
            if self.exit_code is not None:
                return False, self.exit_code
            return True, self.exit_code

        try:
            # WNOHANG is just that...we're calling waitpid without hanging...
            # essentially polling the process.  the return result is (0, 0) if
            # there's no process status, so we check that pid == self.pid below
            # in order to determine how to proceed
            pid, exit_code = no_interrupt(os.waitpid, self.pid, os.WNOHANG)
            if pid == self.pid:
                self.exit_code = handle_process_exit_code(exit_code)
                self._process_just_ended()

                return False, self.exit_code

        # no child process
        except OSError:
            return False, self.exit_code
        else:
            return True, self.exit_code
        finally:
            self._wait_lock.release()


    def _process_just_ended(self):
        if self._timeout_timer:
            self._timeout_timer.cancel()

        done_callback = self.call_args["done"]
        if done_callback:
            success = self.exit_code in self.call_args["ok_code"]
            done_callback(success, self.exit_code)

        # this can only be closed at the end of the process, because it might be
        # the CTTY, and closing it prematurely will send a SIGHUP.  we also
        # don't want to close it if there's a self._stdin_stream, because that
        # is in charge of closing it also
        if self._stdin_read_fd and not self._stdin_stream:
            os.close(self._stdin_read_fd)


    def wait(self):
        """ waits for the process to complete, handles the exit code """

        self.log.debug("acquiring wait lock to wait for completion")
        # using the lock in a with-context blocks, which is what we want if
        # we're running wait()
        with self._wait_lock:
            self.log.debug("got wait lock")
            witnessed_end = False

            if self.exit_code is None:
                self.log.debug("exit code not set, waiting on pid")
                pid, exit_code = no_interrupt(os.waitpid, self.pid, 0) # blocks
                self.exit_code = handle_process_exit_code(exit_code)
                witnessed_end = True

            else:
                self.log.debug("exit code already set (%d), no need to wait",
                        self.exit_code)

            self._quit_threads.set()

            # we may not have a thread for stdin, if the pipe has been connected
            # via _piped="direct"
            if self._input_thread:
                self._input_thread.join()

            # wait, then signal to our output thread that the child process is
            # done, and we should have finished reading all the stdout/stderr
            # data that we can by now
            timer = threading.Timer(2.0, self._stop_output_event.set)
            timer.start()

            # wait for our stdout and stderr streamreaders to finish reading and
            # aggregating the process output
            self._output_thread.join()
            timer.cancel()

            self._background_thread.join()

            if witnessed_end:
                self._process_just_ended()

            return self.exit_code



def input_thread(log, stdin, is_alive, quit, close_before_term):
    """ this is run in a separate thread.  it writes into our process's
    stdin (a streamwriter) and waits the process to end AND everything that
    can be written to be written """

    done = False
    closed = False
    alive = True
    writers = [stdin]

    while writers and alive:
        _, to_write, _ = select.select([], writers, [], 1)

        if to_write:
            log.debug("%r ready for more input", stdin)
            done = stdin.write()

            if done:
                writers = []
                if close_before_term:
                    stdin.close()
                    closed = True

        alive, _ = is_alive()

    while alive:
        quit.wait(1)
        alive, _ = is_alive()

    if not closed:
        stdin.close()


def event_wait(ev, timeout=None):
    triggered = ev.wait(timeout)
    if IS_PY26:
        triggered = ev.is_set()
    return triggered


def background_thread(timeout_fn, timeout_event, handle_exit_code, is_alive,
        quit):
    """ handles the timeout logic """

    # if there's a timeout event, loop 
    if timeout_event:
        while not quit.is_set():
            timed_out = event_wait(timeout_event, 0.1)
            if timed_out:
                timeout_fn()
                break

    # handle_exit_code will be a function ONLY if our command was NOT waited on
    # as part of its spawning.  in other words, it's probably a background
    # command
    #
    # this reports the exit code exception in our thread.  it's purely for the
    # user's awareness, and cannot be caught or used in any way, so it's ok to
    # suppress this during the tests
    if handle_exit_code and not RUNNING_TESTS: # pragma: no cover
        alive = True
        while alive:
            quit.wait(1)
            alive, exit_code = is_alive()

        handle_exit_code(exit_code)


def output_thread(log, stdout, stderr, timeout_event, is_alive, quit,
        stop_output_event):
    """ this function is run in a separate thread.  it reads from the
    process's stdout stream (a streamreader), and waits for it to claim that
    its done """

    readers = []
    errors = []

    if stdout is not None:
        readers.append(stdout)
        errors.append(stdout)
    if stderr is not None:
        readers.append(stderr)
        errors.append(stderr)

    # this is our select loop for polling stdout or stderr that is ready to
    # be read and processed.  if one of those streamreaders indicate that it
    # is done altogether being read from, we remove it from our list of
    # things to poll.  when no more things are left to poll, we leave this
    # loop and clean up
    while readers:
        outputs, inputs, err = no_interrupt(select.select, readers, [], errors, 1)

        # stdout and stderr
        for stream in outputs:
            log.debug("%r ready to be read from", stream)
            done = stream.read()
            if done:
                readers.remove(stream)

        # for some reason, we have to just ignore streams that have had an
        # error.  i'm not exactly sure why, but don't remove this until we
        # figure that out, and create a test for it
        for stream in err:
            pass

        if timeout_event and timeout_event.is_set():
            break

        if stop_output_event.is_set():
            break

    # we need to wait until the process is guaranteed dead before closing our
    # outputs, otherwise SIGPIPE
    alive = True
    while alive:
        quit.wait(1)
        alive, _ = is_alive()

    if stdout:
        stdout.close()

    if stderr:
        stderr.close()


class DoneReadingForever(Exception): pass
class NotYetReadyToRead(Exception): pass


def determine_how_to_read_input(input_obj):
    """ given some kind of input object, return a function that knows how to
    read chunks of that input object.
    
    each reader function should return a chunk and raise a DoneReadingForever
    exception, or return None, when there's no more data to read

    NOTE: the function returned does not need to care much about the requested
    buffering type (eg, unbuffered vs newline-buffered).  the StreamBufferer
    will take care of that.  these functions just need to return a
    reasonably-sized chunk of data. """

    get_chunk = None

    if isinstance(input_obj, Queue):
        log_msg = "queue"
        get_chunk = get_queue_chunk_reader(input_obj)

    elif callable(input_obj):
        log_msg = "callable"
        get_chunk = get_callable_chunk_reader(input_obj)

    # also handles stringio
    elif hasattr(input_obj, "read"):
        log_msg = "file descriptor"
        get_chunk = get_file_chunk_reader(input_obj)

    elif isinstance(input_obj, basestring):
        log_msg = "string"
        get_chunk = get_iter_string_reader(input_obj)

    elif isinstance(input_obj, bytes):
        log_msg = "bytes"
        get_chunk = get_iter_string_reader(input_obj)

    elif isinstance(input_obj, GeneratorType):
        log_msg = "generator"
        get_chunk = get_iter_chunk_reader(iter(input_obj))

    else:
        try:
            it = iter(input_obj)
        except TypeError:
            raise Exception("unknown input object")
        else:
            log_msg = "general iterable"
            get_chunk = get_iter_chunk_reader(it)

    return get_chunk, log_msg



def get_queue_chunk_reader(stdin):
    def fn():
        try:
            chunk = stdin.get(True, 0.1)
        except Empty:
            raise NotYetReadyToRead
        if chunk is None:
            raise DoneReadingForever
        return chunk
    return fn


def get_callable_chunk_reader(stdin):
    def fn():
        try:
            data = stdin()
        except DoneReadingForever:
            raise

        if not data:
            raise DoneReadingForever

        return data

    return fn


def get_iter_string_reader(stdin):
    """ return an iterator that returns a chunk of a string every time it is
    called.  notice that even though bufsize_type might be line buffered, we're
    not doing any line buffering here.  that's because our StreamBufferer
    handles all buffering.  we just need to return a reasonable-sized chunk. """
    bufsize = 1024
    iter_str = (stdin[i:i + bufsize] for i in range(0, len(stdin), bufsize))
    return get_iter_chunk_reader(iter_str)


def get_iter_chunk_reader(stdin):
    def fn():
        try:
            if IS_PY3:
                chunk = stdin.__next__()
            else:
                chunk = stdin.next()
            return chunk
        except StopIteration:
            raise DoneReadingForever
    return fn

def get_file_chunk_reader(stdin):
    bufsize = 1024

    def fn():
        # python 3.* includes a fileno on stringios, but accessing it throws an
        # exception.  that exception is how we'll know we can't do a select on
        # stdin
        is_real_file = True
        if IS_PY3:
            try:
                stdin.fileno()
            except UnsupportedOperation:
                is_real_file = False

        # this select is for files that may not yet be ready to read.  we test
        # for fileno because StringIO/BytesIO cannot be used in a select
        if is_real_file and hasattr(stdin, "fileno"):
            outputs, _, _ = select.select([stdin], [], [], 0.1)
            if not outputs:
                raise NotYetReadyToRead

        chunk = stdin.read(bufsize)
        if not chunk:
            raise DoneReadingForever
        else:
            return chunk

    return fn


def bufsize_type_to_bufsize(bf_type):
    """ for a given bufsize type, return the actual bufsize we will read.
    notice that although 1 means "newline-buffered", we're reading a chunk size
    of 1024.  this is because we have to read something.  we let a
    StreamBufferer instance handle splitting our chunk on newlines """

    # newlines
    if bf_type == 1:
        bufsize = 1024
    # unbuffered
    elif bf_type == 0:
        bufsize = 1
    # or buffered by specific amount
    else:
        bufsize = bf_type

    return bufsize



class StreamWriter(object):
    """ StreamWriter reads from some input (the stdin param) and writes to a fd
    (the stream param).  the stdin may be a Queue, a callable, something with
    the "read" method, a string, or an iterable """

    def __init__(self, log, stream, stdin, bufsize_type, encoding, tty_in):

        self.stream = stream
        self.stdin = stdin

        self.log = log
        self.encoding = encoding
        self.tty_in = tty_in

        self.stream_bufferer = StreamBufferer(bufsize_type, self.encoding)
        self.get_chunk, log_msg = determine_how_to_read_input(stdin)
        self.log.debug("parsed stdin as a %s", log_msg)


    def fileno(self):
        """ defining this allows us to do select.select on an instance of this
        class """
        return self.stream



    def write(self):
        """ attempt to get a chunk of data to write to our child process's
        stdin, then write it.  the return value answers the questions "are we
        done writing forever?" """

        # get_chunk may sometimes return bytes, and sometimes return strings
        # because of the nature of the different types of STDIN objects we
        # support
        try:
            chunk = self.get_chunk()
            if chunk is None:
                raise DoneReadingForever

        except DoneReadingForever:
            self.log.debug("done reading")

            if self.tty_in:
                # EOF time
                try:
                    char = termios.tcgetattr(self.stream)[6][termios.VEOF]
                except:
                    char = chr(4).encode()

                # normally, one EOF should be enough to signal to an program
                # that is read()ing, to return 0 and be on your way.  however,
                # some programs are misbehaved, like python3.1 and python3.2.
                # they don't stop reading sometimes after read() returns 0.
                # this can be demonstrated with the following program:
                #
                # import sys
                # sys.stdout.write(sys.stdin.read())
                #
                # then type 'a' followed by ctrl-d 3 times.  in python
                # 2.6,2.7,3.3,3.4,3.5, it only takes 2 ctrl-d to terminate.
                # however, in python 3.1 and 3.2, it takes all 3.
                #
                # so here we send an extra EOF along, just in case.  i don't
                # believe it can hurt anything
                os.write(self.stream, char)
                os.write(self.stream, char)

            return True

        except NotYetReadyToRead:
            self.log.debug("received no data")
            return False

        # if we're not bytes, make us bytes
        if IS_PY3 and hasattr(chunk, "encode"):
            chunk = chunk.encode(self.encoding)

        for proc_chunk in self.stream_bufferer.process(chunk):
            self.log.debug("got chunk size %d: %r", len(proc_chunk),
                    proc_chunk[:30])

            self.log.debug("writing chunk to process")
            try:
                os.write(self.stream, proc_chunk)
            except OSError:
                self.log.debug("OSError writing stdin chunk")
                return True


    def close(self):
        self.log.debug("closing, but flushing first")
        chunk = self.stream_bufferer.flush()
        self.log.debug("got chunk size %d to flush: %r", len(chunk), chunk[:30])
        try:
            if chunk:
                os.write(self.stream, chunk)

        except OSError:
            pass

        os.close(self.stream)


def determine_how_to_feed_output(handler, encoding, decode_errors):
    if callable(handler):
        process, finish = get_callback_chunk_consumer(handler, encoding,
                decode_errors)

    # in py3, this is used for bytes
    elif isinstance(handler, (cStringIO, iocStringIO)):
        process, finish = get_cstringio_chunk_consumer(handler)

    # in py3, this is used for unicode
    elif isinstance(handler, (StringIO, ioStringIO)):
        process, finish = get_stringio_chunk_consumer(handler, encoding,
                decode_errors)

    elif hasattr(handler, "write"):
        process, finish = get_file_chunk_consumer(handler)

    else:
        process = lambda chunk: False
        finish = lambda: None

    return process, finish


def get_file_chunk_consumer(handler):
    encode = lambda chunk: chunk
    if getattr(handler, "encoding", None):
        encode = lambda chunk: chunk.decode(handler.encoding)

    flush = lambda: None
    if hasattr(handler, "flush"):
        flush = handler.flush

    def process(chunk):
        handler.write(encode(chunk))
        # we should flush on an fd.  chunk is already the correctly-buffered
        # size, so we don't need the fd buffering as well
        flush()
        return False

    def finish():
        flush()

    return process, finish

def get_callback_chunk_consumer(handler, encoding, decode_errors):
    def process(chunk):
        # try to use the encoding first, if that doesn't work, send
        # the bytes, because it might be binary
        try:
            chunk = chunk.decode(encoding, decode_errors)
        except UnicodeDecodeError:
            pass
        return handler(chunk)

    def finish():
        pass

    return process, finish

def get_cstringio_chunk_consumer(handler):
    def process(chunk):
        handler.write(chunk)
        return False

    def finish():
        pass

    return process, finish


def get_stringio_chunk_consumer(handler, encoding, decode_errors):
    def process(chunk):
        handler.write(chunk.decode(encoding, decode_errors))
        return False

    def finish():
        pass

    return process, finish


class StreamReader(object):
    """ reads from some output (the stream) and sends what it just read to the
    handler.  """
    def __init__(self, log, stream, handler, buffer, bufsize_type, encoding,
            decode_errors, pipe_queue=None, save_data=True):
        self.stream = stream
        self.buffer = buffer
        self.save_data = save_data
        self.encoding = encoding
        self.decode_errors = decode_errors

        self.pipe_queue = None
        if pipe_queue:
            self.pipe_queue = weakref.ref(pipe_queue)

        self.log = log

        self.stream_bufferer = StreamBufferer(bufsize_type, self.encoding,
                self.decode_errors)
        self.bufsize = bufsize_type_to_bufsize(bufsize_type)

        self.process_chunk, self.finish_chunk_processor = \
                determine_how_to_feed_output(handler, encoding, decode_errors)

        self.should_quit = False


    def fileno(self):
        """ defining this allows us to do select.select on an instance of this
        class """
        return self.stream

    def close(self):
        chunk = self.stream_bufferer.flush()
        self.log.debug("got chunk size %d to flush: %r", len(chunk), chunk[:30])
        if chunk:
            self.write_chunk(chunk)

        self.finish_chunk_processor()

        if self.pipe_queue and self.save_data:
            self.pipe_queue().put(None)

        os.close(self.stream)


    def write_chunk(self, chunk):
        # in PY3, the chunk coming in will be bytes, so keep that in mind

        if not self.should_quit:
            self.should_quit = self.process_chunk(chunk)


        if self.save_data:
            self.buffer.append(chunk)

            if self.pipe_queue:
                self.log.debug("putting chunk onto pipe: %r", chunk[:30])
                self.pipe_queue().put(chunk)


    def read(self):
        # if we're PY3, we're reading bytes, otherwise we're reading
        # str
        try:
            chunk = no_interrupt(os.read, self.stream, self.bufsize)
        except OSError as e:
            self.log.debug("got errno %d, done reading", e.errno)
            return True
        if not chunk:
            self.log.debug("got no chunk, done reading")
            return True

        self.log.debug("got chunk size %d: %r", len(chunk), chunk[:30])
        for chunk in self.stream_bufferer.process(chunk):
            self.write_chunk(chunk)




class StreamBufferer(object):
    """ this is used for feeding in chunks of stdout/stderr, and breaking it up
    into chunks that will actually be put into the internal buffers.  for
    example, if you have two processes, one being piped to the other, and you
    want that, first process to feed lines of data (instead of the chunks
    however they come in), OProc will use an instance of this class to chop up
    the data and feed it as lines to be sent down the pipe """

    def __init__(self, buffer_type, encoding=DEFAULT_ENCODING,
            decode_errors="strict"):
        # 0 for unbuffered, 1 for line, everything else for that amount
        self.type = buffer_type
        self.buffer = []
        self.n_buffer_count = 0
        self.encoding = encoding
        self.decode_errors = decode_errors

        # this is for if we change buffering types.  if we change from line
        # buffered to unbuffered, its very possible that our self.buffer list
        # has data that was being saved up (while we searched for a newline).
        # we need to use that up, so we don't lose it
        self._use_up_buffer_first = False

        # the buffering lock is used because we might change the buffering
        # types from a different thread.  for example, if we have a stdout
        # callback, we might use it to change the way stdin buffers.  so we
        # lock
        self._buffering_lock = threading.RLock()
        self.log = Logger("stream_bufferer")


    def change_buffering(self, new_type):
        # TODO, when we stop supporting 2.6, make this a with context
        self.log.debug("acquiring buffering lock for changing buffering")
        self._buffering_lock.acquire()
        self.log.debug("got buffering lock for changing buffering")
        try:
            if new_type == 0:
                self._use_up_buffer_first = True

            self.type = new_type
        finally:
            self._buffering_lock.release()
            self.log.debug("released buffering lock for changing buffering")


    def process(self, chunk):
        # MAKE SURE THAT THE INPUT IS PY3 BYTES
        # THE OUTPUT IS ALWAYS PY3 BYTES

        # TODO, when we stop supporting 2.6, make this a with context
        self.log.debug("acquiring buffering lock to process chunk (buffering: %d)", self.type)
        self._buffering_lock.acquire()
        self.log.debug("got buffering lock to process chunk (buffering: %d)", self.type)
        try:
            # unbuffered
            if self.type == 0:
                if self._use_up_buffer_first:
                    self._use_up_buffer_first = False
                    to_write = self.buffer
                    self.buffer = []
                    to_write.append(chunk)
                    return to_write

                return [chunk]

            # line buffered
            elif self.type == 1:
                total_to_write = []
                nl = "\n".encode(self.encoding)
                while True:
                    newline = chunk.find(nl)
                    if newline == -1:
                        break

                    chunk_to_write = chunk[:newline + 1]
                    if self.buffer:
                        chunk_to_write = b"".join(self.buffer) + chunk_to_write

                        self.buffer = []
                        self.n_buffer_count = 0

                    chunk = chunk[newline + 1:]
                    total_to_write.append(chunk_to_write)

                if chunk:
                    self.buffer.append(chunk)
                    self.n_buffer_count += len(chunk)
                return total_to_write

            # N size buffered
            else:
                total_to_write = []
                while True:
                    overage = self.n_buffer_count + len(chunk) - self.type
                    if overage >= 0:
                        ret = "".encode(self.encoding).join(self.buffer) + chunk
                        chunk_to_write = ret[:self.type]
                        chunk = ret[self.type:]
                        total_to_write.append(chunk_to_write)
                        self.buffer = []
                        self.n_buffer_count = 0
                    else:
                        self.buffer.append(chunk)
                        self.n_buffer_count += len(chunk)
                        break
                return total_to_write
        finally:
            self._buffering_lock.release()
            self.log.debug("released buffering lock for processing chunk (buffering: %d)", self.type)


    def flush(self):
        self.log.debug("acquiring buffering lock for flushing buffer")
        self._buffering_lock.acquire()
        self.log.debug("got buffering lock for flushing buffer")
        try:
            ret = "".encode(self.encoding).join(self.buffer)
            self.buffer = []
            return ret
        finally:
            self._buffering_lock.release()
            self.log.debug("released buffering lock for flushing buffer")



def with_lock(lock):
    def wrapped(fn):
        fn = contextmanager(fn)
        @contextmanager
        def wrapped2(*args, **kwargs):
            with lock:
                with fn(*args, **kwargs):
                    yield
        return wrapped2
    return wrapped


@with_lock(PUSHD_LOCK)
def pushd(path):
    """ pushd changes the actual working directory for the duration of the
    context, unlike the _cwd arg this will work with other built-ins such as
    sh.glob correctly """
    orig_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(orig_path)


@contextmanager
def args(**kwargs):
    """ allows us to temporarily override all the special keyword parameters in
    a with context """

    kwargs_str = ",".join(["%s=%r" % (k,v) for k,v in kwargs.items()])

    raise DeprecationWarning("""

sh.args() has been deprecated because it was never thread safe.  use the
following instead:

    sh2 = sh({kwargs})
    sh2.your_command()

or

    sh2 = sh({kwargs})
    from sh2 import your_command
    your_command()

""".format(kwargs=kwargs_str))



class Environment(dict):
    """ this allows lookups to names that aren't found in the global scope to be
    searched for as a program name.  for example, if "ls" isn't found in this
    module's scope, we consider it a system program and try to find it.

    we use a dict instead of just a regular object as the base class because the
    exec() statement used in the run_repl requires the "globals" argument to be a
    dictionary """


    # this is a list of all of the names that the sh module exports that will
    # not resolve to functions.  we don't want to accidentally shadow real
    # commands with functions/imports that we define in sh.py.  for example,
    # "import time" may override the time system program
    whitelist = set([
        "Command",
        "RunningCommand",
        "CommandNotFound",
        "DEFAULT_ENCODING",
        "DoneReadingForever",
        "ErrorReturnCode",
        "NotYetReadyToRead",
        "SignalException",
        "ForkException",
        "TimeoutException",
        "__project_url__",
        "__version__",
        "__file__",
        "args",
        "pushd",
        "glob",
        "contrib",
    ])


    def __init__(self, globs, baked_args={}):
        """ baked_args are defaults for the 'sh' execution context.  for
        example:
            
            tmp = sh(_out=StringIO())

        'out' would end up in here as an entry in the baked_args dict """

        self.globs = globs
        self.baked_args = baked_args
        self.disable_whitelist = False

    def __getitem__(self, k):
        # if we first import "_disable_whitelist" from sh, we can import
        # anything defined in the global scope of sh.py.  this is useful for our
        # tests
        if k == "_disable_whitelist":
            self.disable_whitelist = True
            return None

        # we're trying to import something real (maybe), see if it's in our
        # global scope
        if k in self.whitelist or self.disable_whitelist:
            return self.globs[k]

        # somebody tried to be funny and do "from sh import *"
        if k == "__all__":
            raise RuntimeError("Cannot import * from sh. \
Please import sh or import programs individually.")


        # check if we're naming a dynamically generated ReturnCode exception
        exc = get_exc_from_name(k)
        if exc:
            return exc


        # https://github.com/ipython/ipython/issues/2577
        # https://github.com/amoffat/sh/issues/97#issuecomment-10610629
        if k.startswith("__") and k.endswith("__"):
            raise AttributeError


        # is it a custom builtin?
        builtin = getattr(self, "b_" + k, None)
        if builtin:
            return builtin


        # is it a command?
        cmd = resolve_command(k, self.baked_args)
        if cmd:
            return cmd


        # how about an environment variable?
        # this check must come after testing if its a command, because on some
        # systems, there are an environment variables that can conflict with
        # command names.
        # https://github.com/amoffat/sh/issues/238
        try:
            return os.environ[k]
        except KeyError:
            pass


        # nothing found, raise an exception
        raise CommandNotFound(k)


    # methods that begin with "b_" are custom builtins and will override any
    # program that exists in our path.  this is useful for things like
    # common shell builtins that people are used to, but which aren't actually
    # full-fledged system binaries

    def b_cd(self, path=None):
        if path:
            os.chdir(path)
        else:
            os.chdir(os.path.expanduser('~'))

    def b_which(self, program, paths=None):
        return which(program, paths)


class Contrib(ModuleType): # pragma: no cover
    @classmethod
    def __call__(cls, name):
        def wrapper1(fn):

            @property
            def cmd_getter(self):
                cmd = resolve_command(name)

                if not cmd:
                    raise CommandNotFound(name)

                new_cmd = fn(cmd)
                return new_cmd

            setattr(cls, name, cmd_getter)
            return fn

        return wrapper1


mod_name = __name__ + ".contrib"
contrib = Contrib(mod_name)
sys.modules[mod_name] = contrib


@contrib("git")
def git(orig): # pragma: no cover
    """ most git commands play nicer without a TTY """
    cmd = orig.bake(_tty_out=False)
    return cmd

@contrib("sudo")
def sudo(orig): # pragma: no cover
    """ a nicer version of sudo that uses getpass to ask for a password, or
    allows the first argument to be a string password """

    prompt = "[sudo] password for %s: " % getpass.getuser()

    def stdin():
        pw = getpass.getpass(prompt=prompt) + "\n"
        yield pw


    def process(args, kwargs):
        password = kwargs.pop("password", None)

        if password is None:
            pass_getter = stdin()
        else:
            pass_getter = password.rstrip("\n") + "\n"

        kwargs["_in"] = pass_getter
        return args, kwargs

    cmd = orig.bake("-S", _arg_preprocess=process)
    return cmd




def run_repl(env): # pragma: no cover
    banner = "\n>> sh v{version}\n>> https://github.com/amoffat/sh\n"

    print(banner.format(version=__version__))
    while True:
        try:
            line = raw_input("sh> ")
        except (ValueError, EOFError):
            break

        try:
            exec(compile(line, "<dummy>", "single"), env, env)
        except SystemExit:
            break
        except:
            print(traceback.format_exc())

    # cleans up our last line
    print("")




# this is a thin wrapper around THIS module (we patch sys.modules[__name__]).
# this is in the case that the user does a "from sh import whatever"
# in other words, they only want to import certain programs, not the whole
# system PATH worth of commands.  in this case, we just proxy the
# import lookup to our Environment class
class SelfWrapper(ModuleType):
    def __init__(self, self_module, baked_args={}):
        # this is super ugly to have to copy attributes like this,
        # but it seems to be the only way to make reload() behave
        # nicely.  if i make these attributes dynamic lookups in
        # __getattr__, reload sometimes chokes in weird ways...
        for attr in ["__builtins__", "__doc__", "__file__", "__name__", "__package__"]:
            setattr(self, attr, getattr(self_module, attr, None))

        # python 3.2 (2.7 and 3.3 work fine) breaks on osx (not ubuntu)
        # if we set this to None.  and 3.3 needs a value for __path__
        self.__path__ = []
        self.__self_module = self_module
        self.__env = Environment(globals(), baked_args=baked_args)

    def __getattr__(self, name):
        return self.__env[name]

    def __call__(self, **kwargs):
        """ returns a new SelfWrapper object, where all commands spawned from it
        have the baked_args kwargs set on them by default """
        baked_args = self.__env.baked_args.copy()
        baked_args.update(kwargs)
        new_mod = self.__class__(self.__self_module, baked_args)

        # inspect the line in the parent frame that calls and assigns the new sh
        # variable, and get the name of the new variable we're assigning to.
        # this is very brittle and pretty much a sin.  but it works in 99% of
        # the time and the tests pass
        #
        # the reason we need to do this is because we need to remove the old
        # cached module from sys.modules.  if we don't, it gets re-used, and any
        # old baked params get used, which is not what we want
        parent = inspect.stack()[1]
        code = parent[4][0].strip()
        parsed = ast.parse(code)
        module_name = parsed.body[0].targets[0].id

        if module_name == __name__:
            raise RuntimeError("Cannot use the name 'sh' as an execution context")

        sys.modules.pop(module_name, None)

        return new_mod


def in_importlib(frame):
    """ helper for checking if a filename is in importlib guts """
    return frame.f_code.co_filename == "<frozen importlib._bootstrap>"


def register_importer():
    """ registers our fancy importer that can let us import from a module name,
    like:

        import sh
        tmp = sh()
        from tmp import ls
    """

    def test(importer):
        return importer.__class__.__name__ == ModuleImporterFromVariables.__name__
    already_registered = any([True for i in sys.meta_path if test(i)])

    if not already_registered:
        importer = ModuleImporterFromVariables(
            restrict_to=["SelfWrapper"],
        )
        sys.meta_path.insert(0, importer)

    return not already_registered

def fetch_module_from_frame(name, frame):
    mod = frame.f_locals.get(name, frame.f_globals.get(name, None))
    return mod

class ModuleImporterFromVariables(object):
    """ a fancy importer that allows us to import from a variable that was
    recently set in either the local or global scope, like this:

        sh2 = sh(_timeout=3)
        from sh2 import ls
    
    """

    def __init__(self, restrict_to=None):
        self.restrict_to = set(restrict_to or set())


    def find_module(self, mod_fullname, path=None):
        """ mod_fullname doubles as the name of the VARIABLE holding our new sh
        context.  for example:

            derp = sh()
            from derp import ls

        here, mod_fullname will be "derp".  keep that in mind as we go throug
        the rest of this function """

        parent_frame = inspect.currentframe().f_back
        while in_importlib(parent_frame):
            parent_frame = parent_frame.f_back

        # this line is saying "hey, does mod_fullname exist as a name we've
        # defind previously?"  the purpose of this is to ensure that
        # mod_fullname is really a thing we've defined.  if we haven't defined
        # it before, then we "can't" import from it
        module = fetch_module_from_frame(mod_fullname, parent_frame)
        if not module:
            return None

        # make sure it's a class we're allowed to import from
        if module.__class__.__name__ not in self.restrict_to:
            return None

        return self


    def load_module(self, mod_fullname):
        parent_frame = inspect.currentframe().f_back

        while in_importlib(parent_frame):
            parent_frame = parent_frame.f_back

        module = fetch_module_from_frame(mod_fullname, parent_frame)

        # we HAVE to include the module in sys.modules, per the import PEP.
        # older verions of python were more lenient about this being set, but
        # not in >= python3.3, unfortunately.  this requirement necessitates the
        # ugly code in SelfWrapper.__call__
        sys.modules[mod_fullname] = module
        module.__loader__ = self

        return module


def run_tests(env, locale, args, version, **extra_env): # pragma: no cover
    py_version = "python"
    py_version += str(version)

    py_bin = which(py_version)
    return_code = None

    if py_bin:
        print("Testing %s, locale %r" % (py_version.capitalize(),
            locale))

        env["LANG"] = locale

        for k,v in extra_env.items():
            env[k] = str(v)

        cmd = [py_bin, "-W", "ignore", os.path.join(THIS_DIR, "test.py")] + args[1:]
        launch = lambda: os.spawnve(os.P_WAIT, cmd[0], cmd, env)
        return_code = launch()

    return return_code



# we're being run as a stand-alone script
if __name__ == "__main__": # pragma: no cover
    def parse_args():
        from optparse import OptionParser

        parser = OptionParser()
        parser.add_option("-e", "--envs", dest="envs", action="append")
        parser.add_option("-l", "--locales", dest="constrain_locales", action="append")
        options, args = parser.parse_args()

        envs = options.envs or []
        constrain_locales = options.constrain_locales or []

        return args, envs, constrain_locales

    # these are essentially restrictions on what envs/constrain_locales to restrict to for
    # the tests.  if they're empty lists, it means use all available
    args, constrain_versions, constrain_locales = parse_args()
    action = None
    if args:
        action = args[0]

    if action in ("test", "travis"):
        import test
        coverage = None
        if test.HAS_UNICODE_LITERAL:
            import coverage

        env = os.environ.copy()
        env["SH_TESTS_RUNNING"] = "1"
        if coverage:
            test.append_module_path(env, coverage)

        # if we're testing locally, run all versions of python on the system
        if action == "test":
            all_versions = ("2.6", "2.7", "3.1", "3.2", "3.3", "3.4", "3.5")

        # if we're testing on travis, just use the system's default python,
        # since travis will spawn a vm per python version in our .travis.yml
        # file
        elif action == "travis":
            v = sys.version_info
            sys_ver = "%d.%d" % (v[0], v[1])
            all_versions = (sys_ver,)

        all_locales = ("en_US.UTF-8", "C")
        i = 0
        for locale in all_locales:
            if constrain_locales and locale not in constrain_locales:
                continue

            for version in all_versions:
                if constrain_versions and version not in constrain_versions:
                    continue

                env_copy = env.copy()
                exit_code = run_tests(env_copy, locale, args, version,
                        SH_TEST_RUN_IDX=i)

                if exit_code is None:
                    print("Couldn't find %s, skipping" % version)

                elif exit_code != 0:
                    print("Failed for %s, %s" % (version, locale))
                    exit(1)

                i += 1

        ran_versions = ",".join(all_versions)
        print("Tested Python versions: %s" % ran_versions)

    else:
        env = Environment(globals())
        run_repl(env)

# we're being imported from somewhere
else:
    self = sys.modules[__name__]
    sys.modules[__name__] = SelfWrapper(self)
    register_importer()

