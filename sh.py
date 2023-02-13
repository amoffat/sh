"""
http://amoffat.github.io/sh/
"""
# ===============================================================================
# Copyright (C) 2011-2023 by Andrew Moffat
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
# ===============================================================================
__version__ = "2.0.0"
__project_url__ = "https://github.com/amoffat/sh"

import asyncio
from collections import deque

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

import errno
import fcntl
import gc
import getpass
import glob as glob_module
import inspect
import logging
import os
import platform
import pty
import pwd
import re
import select
import signal
import stat
import struct
import sys
import termios
import threading
import time
import traceback
import tty
import warnings
import weakref
from asyncio import Queue as AQueue
from contextlib import contextmanager
from functools import partial
from io import BytesIO, StringIO, UnsupportedOperation
from io import open as fdopen
from locale import getpreferredencoding
from queue import Empty, Queue
from shlex import quote as shlex_quote
from types import GeneratorType, ModuleType
from typing import Any, Dict, Type, Union

if "windows" in platform.system().lower():  # pragma: no cover
    raise ImportError(
        "sh %s is currently only supported on linux and osx. \
please install pbs 0.110 (http://pypi.python.org/pypi/pbs) for windows \
support."
        % __version__
    )

TEE_STDOUT = {True, "out", 1}
TEE_STDERR = {"err", 2}

DEFAULT_ENCODING = getpreferredencoding() or "UTF-8"

IS_MACOS = platform.system() in ("AIX", "Darwin")
SH_LOGGER_NAME = __name__

# normally i would hate this idea of using a global to signify whether we are
# running tests, because it breaks the assumption that what is running in the
# tests is what will run live, but we ONLY use this in a place that has no
# serious side-effects that could change anything.  as long as we do that, it
# should be ok
RUNNING_TESTS = bool(int(os.environ.get("SH_TESTS_RUNNING", "0")))
FORCE_USE_SELECT = bool(int(os.environ.get("SH_TESTS_USE_SELECT", "0")))

# a re-entrant lock for pushd.  this way, multiple threads that happen to use
# pushd will all see the current working directory for the duration of the
# with-context
PUSHD_LOCK = threading.RLock()


def get_num_args(fn):
    return len(inspect.getfullargspec(fn).args)


_unicode_methods = set(dir(str()))

HAS_POLL = hasattr(select, "poll")
POLLER_EVENT_READ = 1
POLLER_EVENT_WRITE = 2
POLLER_EVENT_HUP = 4
POLLER_EVENT_ERROR = 8


class PollPoller(object):
    def __init__(self):
        self._poll = select.poll()
        # file descriptor <-> file object bidirectional maps
        self.fd_lookup = {}
        self.fo_lookup = {}

    def __nonzero__(self):
        return len(self.fd_lookup) != 0

    def __len__(self):
        return len(self.fd_lookup)

    def _set_fileobject(self, f):
        if hasattr(f, "fileno"):
            fd = f.fileno()
            self.fd_lookup[fd] = f
            self.fo_lookup[f] = fd
        else:
            self.fd_lookup[f] = f
            self.fo_lookup[f] = f

    def _remove_fileobject(self, f):
        if hasattr(f, "fileno"):
            fd = f.fileno()
            del self.fd_lookup[fd]
            del self.fo_lookup[f]
        else:
            del self.fd_lookup[f]
            del self.fo_lookup[f]

    def _get_file_descriptor(self, f):
        return self.fo_lookup.get(f)

    def _get_file_object(self, fd):
        return self.fd_lookup.get(fd)

    def _register(self, f, events):
        # f can be a file descriptor or file object
        self._set_fileobject(f)
        fd = self._get_file_descriptor(f)
        self._poll.register(fd, events)

    def register_read(self, f):
        self._register(f, select.POLLIN | select.POLLPRI)

    def register_write(self, f):
        self._register(f, select.POLLOUT)

    def register_error(self, f):
        self._register(f, select.POLLERR | select.POLLHUP | select.POLLNVAL)

    def unregister(self, f):
        fd = self._get_file_descriptor(f)
        self._poll.unregister(fd)
        self._remove_fileobject(f)

    def poll(self, timeout):
        if timeout is not None:
            # convert from seconds to milliseconds
            timeout *= 1000
        changes = self._poll.poll(timeout)
        results = []
        for fd, events in changes:
            f = self._get_file_object(fd)
            if events & (select.POLLIN | select.POLLPRI):
                results.append((f, POLLER_EVENT_READ))
            elif events & select.POLLOUT:
                results.append((f, POLLER_EVENT_WRITE))
            elif events & select.POLLHUP:
                results.append((f, POLLER_EVENT_HUP))
            elif events & (select.POLLERR | select.POLLNVAL):
                results.append((f, POLLER_EVENT_ERROR))
        return results


class SelectPoller(object):
    def __init__(self):
        self.rlist = []
        self.wlist = []
        self.xlist = []

    def __nonzero__(self):
        return len(self.rlist) + len(self.wlist) + len(self.xlist) != 0

    def __len__(self):
        return len(self.rlist) + len(self.wlist) + len(self.xlist)

    @staticmethod
    def _register(f, events):
        if f not in events:
            events.append(f)

    @staticmethod
    def _unregister(f, events):
        if f in events:
            events.remove(f)

    def register_read(self, f):
        self._register(f, self.rlist)

    def register_write(self, f):
        self._register(f, self.wlist)

    def register_error(self, f):
        self._register(f, self.xlist)

    def unregister(self, f):
        self._unregister(f, self.rlist)
        self._unregister(f, self.wlist)
        self._unregister(f, self.xlist)

    def poll(self, timeout):
        _in, _out, _err = select.select(self.rlist, self.wlist, self.xlist, timeout)
        results = []
        for f in _in:
            results.append((f, POLLER_EVENT_READ))
        for f in _out:
            results.append((f, POLLER_EVENT_WRITE))
        for f in _err:
            results.append((f, POLLER_EVENT_ERROR))
        return results


# here we use an use a poller interface that transparently selects the most
# capable poller (out of either select.select or select.poll).  this was added
# by zhangyafeikimi when he discovered that if the fds created internally by sh
# numbered > 1024, select.select failed (a limitation of select.select).  this
# can happen if your script opens a lot of files
Poller: Union[Type[SelectPoller], Type[PollPoller]] = SelectPoller
if HAS_POLL and not FORCE_USE_SELECT:
    Poller = PollPoller


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
    """a metaclass which provides the ability for an ErrorReturnCode (or
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

    def __reduce__(self):
        return self.__class__, (self.full_cmd, self.stdout, self.stderr, self.truncate)

    def __init__(self, full_cmd, stdout, stderr, truncate=True):
        self.exit_code = self.exit_code  # makes pylint happy
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr
        self.truncate = truncate

        exc_stdout = self.stdout
        if truncate:
            exc_stdout = exc_stdout[: self.truncate_cap]
            out_delta = len(self.stdout) - len(exc_stdout)
            if out_delta:
                exc_stdout += (
                    "... (%d more, please see e.stdout)" % out_delta
                ).encode()

        exc_stderr = self.stderr
        if truncate:
            exc_stderr = exc_stderr[: self.truncate_cap]
            err_delta = len(self.stderr) - len(exc_stderr)
            if err_delta:
                exc_stderr += (
                    "... (%d more, please see e.stderr)" % err_delta
                ).encode()

        msg_tmpl = str("\n\n  RAN: {cmd}\n\n  STDOUT:\n{stdout}\n\n  STDERR:\n{stderr}")

        msg = msg_tmpl.format(
            cmd=self.full_cmd,
            stdout=exc_stdout.decode(DEFAULT_ENCODING, "replace"),
            stderr=exc_stderr.decode(DEFAULT_ENCODING, "replace"),
        )

        super(ErrorReturnCode, self).__init__(msg)


class SignalException(ErrorReturnCode):
    pass


class TimeoutException(Exception):
    """the exception thrown when a command is killed because a specified
    timeout (via _timeout or .wait(timeout)) was hit"""

    def __init__(self, exit_code, full_cmd):
        self.exit_code = exit_code
        self.full_cmd = full_cmd
        super(Exception, self).__init__()


SIGNALS_THAT_SHOULD_THROW_EXCEPTION = {
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
}


# we subclass AttributeError because:
# https://github.com/ipython/ipython/issues/2577
# https://github.com/amoffat/sh/issues/97#issuecomment-10610629
class CommandNotFound(AttributeError):
    pass


rc_exc_regex = re.compile(r"(ErrorReturnCode|SignalException)_((\d+)|SIG[a-zA-Z]+)")
rc_exc_cache: Dict[str, Type[ErrorReturnCode]] = {}

SIGNAL_MAPPING = dict(
    [(v, k) for k, v in signal.__dict__.items() if re.match(r"SIG[a-zA-Z]+", k)]
)


def get_exc_from_name(name):
    """takes an exception name, like:

        ErrorReturnCode_1
        SignalException_9
        SignalException_SIGHUP

    and returns the corresponding exception.  this is primarily used for
    importing exceptions from sh into user code, for instance, to capture those
    exceptions"""

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
    """takes a exit code or negative signal number and produces an exception
    that corresponds to that return code.  positive return codes yield
    ErrorReturnCode exception, negative return codes yield SignalException

    we also cache the generated exception so that only one signal of that type
    exists, preserving identity"""

    try:
        return rc_exc_cache[rc]
    except KeyError:
        pass

    if rc >= 0:
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


def glob(path, recursive=False):
    expanded = GlobResults(path, _old_glob(path, recursive=recursive))
    return expanded


glob_module.glob = glob


def canonicalize(path):
    return os.path.abspath(os.path.expanduser(path))


def _which(program, paths=None):
    """takes a program name or full path, plus an optional collection of search
    paths, and returns the full path of the requested executable.  if paths is
    specified, it is the entire list of search paths, and the PATH env is not
    used at all.  otherwise, PATH env is used to look for the program"""

    def is_exe(file_path):
        return (
            os.path.exists(file_path)
            and os.access(file_path, os.X_OK)
            and os.path.isfile(os.path.realpath(file_path))
        )

    found_path = None
    fpath, fname = os.path.split(program)

    # if there's a path component, then we've specified a path to the program,
    # and we should just test if that program is executable.  if it is, return
    if fpath:
        program = canonicalize(program)
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
            exe_file = os.path.join(canonicalize(path), program)
            if is_exe(exe_file):
                found_path = exe_file
                break

    return found_path


def resolve_command_path(program):
    path = _which(program)
    if not path:
        # our actual command might have a dash in it, but we can't call
        # that from python (we have to use underscores), so we'll check
        # if a dash version of our underscore command exists and use that
        # if it does
        if "_" in program:
            path = _which(program.replace("_", "-"))
        if not path:
            return None
    return path


def resolve_command(name, command_cls, baked_args=None):
    path = resolve_command_path(name)
    cmd = None
    if path:
        cmd = command_cls(path)
        if baked_args:
            cmd = cmd.bake(**baked_args)
    return cmd


class Logger(object):
    """provides a memory-inexpensive logger.  a gotcha about python's builtin
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
        self.context = self.sanitize_context(context)

    def _format_msg(self, msg, *a):
        if self.context:
            msg = "%s: %s" % (self.context, msg)
        return msg % a

    @staticmethod
    def sanitize_context(context):
        if context:
            context = context.replace("%", "%%")
        return context or ""

    def get_child(self, name, context):
        new_name = self.name + "." + name
        new_context = self.context + "." + context
        return Logger(new_name, new_context)

    def info(self, msg, *a):
        self.log.info(self._format_msg(msg, *a))

    def debug(self, msg, *a):
        self.log.debug(self._format_msg(msg, *a))

    def error(self, msg, *a):
        self.log.error(self._format_msg(msg, *a))

    def exception(self, msg, *a):
        self.log.exception(self._format_msg(msg, *a))


def default_logger_str(cmd, call_args, pid=None):
    if pid:
        s = "<Command %r, pid %d>" % (cmd, pid)
    else:
        s = "<Command %r>" % cmd
    return s


class RunningCommand(object):
    """this represents an executing Command object.  it is returned as the
    result of __call__() being executed on a Command instance.  this creates a
    reference to a OProc instance, which is a low-level wrapper around the
    process that was exec'd

    this is the class that gets manipulated the most by user code, and so it
    implements various convenience methods and logical mechanisms for the
    underlying process.  for example, if a user tries to access a
    backgrounded-process's stdout/err, the RunningCommand object is smart enough
    to know to wait() on the process to finish first.  and when the process
    finishes, RunningCommand is smart enough to translate exit codes to
    exceptions."""

    # these are attributes that we allow to pass through to OProc
    _OProc_attr_allowlist = {
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
    }

    def __init__(self, cmd, call_args, stdin, stdout, stderr):
        # self.ran is used for auditing what actually ran.  for example, in
        # exceptions, or if you just want to know what was ran after the
        # command ran
        self.ran = " ".join([shlex_quote(str(arg)) for arg in cmd])

        self.call_args = call_args
        self.cmd = cmd

        self.process = None
        self._waited_until_completion = False
        should_wait = True
        spawn_process = True

        # if we're using an async for loop on this object, we need to put the underlying
        # iterable in no-block mode. however, we will only know if we're using an async
        # for loop after this object is constructed. so we'll set it to False now, but
        # then later set it to True if we need it
        self._force_noblock_iter = False

        # this event is used when we want to `await` a RunningCommand. see how it gets
        # used in self.__await__
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            self.aio_output_complete = None
        else:
            self.aio_output_complete = asyncio.Event()

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

        if call_args["async"]:
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

            self.log.debug("starting process")

            if should_wait:
                self._spawned_and_waited = True

            # this lock is needed because of a race condition where a background
            # thread, created in the OProc constructor, may try to access
            # self.process, but it has not been assigned yet
            process_assign_lock = threading.Lock()
            with process_assign_lock:
                self.process = OProc(
                    self,
                    self.log,
                    cmd,
                    stdin,
                    stdout,
                    stderr,
                    self.call_args,
                    pipe,
                    process_assign_lock,
                )

            logger_str = log_str_factory(self.ran, call_args, self.process.pid)
            self.log.context = self.log.sanitize_context(logger_str)
            self.log.info("process started")

            if should_wait:
                self.wait()

    def wait(self, timeout=None):
        """waits for the running command to finish.  this is called on all
        running commands, eventually, except for ones that run in the background

        if timeout is a number, it is the number of seconds to wait for the process to
        resolve. otherwise block on wait.

        this function can raise a TimeoutException, either because of a `_timeout` on
        the command itself as it was
        launched, or because of a timeout passed into this method.
        """
        if not self._waited_until_completion:
            # if we've been given a timeout, we need to poll is_alive()
            if timeout is not None:
                waited_for = 0
                sleep_amt = 0.1
                alive = False
                exit_code = None
                if timeout < 0:
                    raise RuntimeError("timeout cannot be negative")

                # while we still have time to wait, run this loop
                # notice that alive and exit_code are only defined in this loop, but
                # the loop is also guaranteed to run, defining them, given the
                # constraints that timeout is non-negative
                while waited_for <= timeout:
                    alive, exit_code = self.process.is_alive()

                    # if we're alive, we need to wait some more, but let's sleep
                    # before we poll again
                    if alive:
                        time.sleep(sleep_amt)
                        waited_for += sleep_amt

                    # but if we're not alive, we're done waiting
                    else:
                        break

                # if we've made it this far, and we're still alive, then it means we
                # timed out waiting
                if alive:
                    raise TimeoutException(None, self.ran)

                # if we didn't time out, we fall through and let the rest of the code
                # handle exit_code. notice that we set _waited_until_completion here,
                # only if we didn't time out. this allows us to re-wait again on
                # timeout, if we catch the TimeoutException in the parent frame
                self._waited_until_completion = True

            else:
                exit_code = self.process.wait()
                self._waited_until_completion = True

            if self.process.timed_out:
                # if we timed out, our exit code represents a signal, which is
                # negative, so let's make it positive to store in our
                # TimeoutException
                raise TimeoutException(-exit_code, self.ran)

            else:
                self.handle_command_exit_code(exit_code)

                # if an iterable command is using an instance of OProc for its stdin,
                # wait on it.  the process is probably set to "piped", which means it
                # won't be waited on, which means exceptions won't propagate up to the
                # main thread.  this allows them to bubble up
                if self.process._stdin_process:
                    self.process._stdin_process.command.wait()

            self.log.debug("process completed")
        return self

    def is_alive(self):
        """returns whether or not we're still alive. this call has side-effects on
        OProc"""
        return self.process.is_alive()[0]

    def handle_command_exit_code(self, code):
        """here we determine if we had an exception, or an error code that we
        weren't expecting to see.  if we did, we create and raise an exception
        """
        ca = self.call_args
        exc_class = get_exc_exit_code_would_raise(code, ca["ok_code"], ca["piped"])
        if exc_class:
            exc = exc_class(
                self.ran, self.process.stdout, self.process.stderr, ca["truncate_exc"]
            )
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
        """we don't actually do anything here because anything that should have
        been done would have been done in the Command.__call__ call.
        essentially all that has to happen is the command be pushed on the
        prepend stack."""
        pass

    def __iter__(self):
        return self

    def __next__(self):
        """allow us to iterate over the output of our command"""

        if self._stopped_iteration:
            raise StopIteration()

        pq = self.process._pipe_queue

        # the idea with this is, if we're using regular `_iter` (non-asyncio), then we
        # want to have blocking be True when we read from the pipe queue, so our cpu
        # doesn't spin too fast. however, if we *are* using asyncio (an async for loop),
        # then we want non-blocking pipe queue reads, because we'll do an asyncio.sleep,
        # in the coroutine that is doing the iteration, this way coroutines have better
        # yielding (see queue_connector in __aiter__).
        block_pq_read = not self._force_noblock_iter

        # we do this because if get blocks, we can't catch a KeyboardInterrupt
        # so the slight timeout allows for that.
        while True:
            try:
                chunk = pq.get(block_pq_read, self.call_args["iter_poll_time"])
            except Empty:
                if self.call_args["iter_noblock"] or self._force_noblock_iter:
                    return errno.EWOULDBLOCK
            else:
                if chunk is None:
                    self.wait()
                    self._stopped_iteration = True
                    raise StopIteration()
                try:
                    return chunk.decode(
                        self.call_args["encoding"], self.call_args["decode_errors"]
                    )
                except UnicodeDecodeError:
                    return chunk

    def __await__(self):
        async def wait_for_completion():
            await self.aio_output_complete.wait()
            return str(self)

        return wait_for_completion().__await__()

    def __aiter__(self):
        # maxsize is critical to making sure our queue_connector function below yields
        # when it awaits _aio_queue.put(chunk). if we didn't have a maxsize, our loop
        # would happily iterate through `chunk in self` and put onto the queue without
        # any blocking, and therefore no yielding, which would prevent other coroutines
        # from running.
        self._aio_queue = AQueue(maxsize=1)
        self._force_noblock_iter = True

        # the sole purpose of this coroutine is to connect our pipe_queue (which is
        # being populated by a thread) to an asyncio-friendly queue. then, in __anext__,
        # we can iterate over that asyncio queue.
        async def queue_connector():
            try:
                # this will spin as fast as possible if there's no data to read,
                # thanks to self._force_noblock_iter. so we sleep below.
                for chunk in self:
                    if chunk == errno.EWOULDBLOCK:
                        # let us have better coroutine yielding.
                        await asyncio.sleep(0.01)
                    else:
                        await self._aio_queue.put(chunk)
            finally:
                await self._aio_queue.put(None)

        if sys.version_info < (3, 7, 0):
            task = asyncio.ensure_future(queue_connector())
        else:
            task = asyncio.create_task(queue_connector())

        self._aio_task = task
        return self

    async def __anext__(self):
        chunk = await self._aio_queue.get()
        if chunk is not None:
            return chunk
        else:
            exc = self._aio_task.exception()
            if exc is not None:
                raise exc
            raise StopAsyncIteration

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.call_args["with"] and get_prepend_stack():
            get_prepend_stack().pop()

    def __str__(self):
        if self.process and self.stdout:
            return self.stdout.decode(
                self.call_args["encoding"], self.call_args["decode_errors"]
            )
        return ""

    def __eq__(self, other):
        return id(self) == id(other)

    def __contains__(self, item):
        return item in str(self)

    def __getattr__(self, p):
        # let these three attributes pass through to the OProc object
        if p in self._OProc_attr_allowlist:
            if self.process:
                return getattr(self.process, p)
            else:
                raise AttributeError

        # see if strings have what we're looking for
        if p in _unicode_methods:
            return getattr(str(self), p)

        raise AttributeError

    def __repr__(self):
        try:
            return str(self)
        except UnicodeDecodeError:
            if self.process:
                if self.stdout:
                    return repr(self.stdout)
            return repr("")

    def __long__(self):
        return int(str(self).strip())

    def __float__(self):
        return float(str(self).strip())

    def __int__(self):
        return int(str(self).strip())


def output_redirect_is_filename(out):
    return isinstance(out, str) or hasattr(out, "__fspath__")


def get_prepend_stack():
    tl = Command.thread_local
    if not hasattr(tl, "_prepend_stack"):
        tl._prepend_stack = []
    return tl._prepend_stack


def special_kwarg_validator(passed_kwargs, merged_kwargs, invalid_list):
    s1 = set(passed_kwargs.keys())
    invalid_args = []

    for elem in invalid_list:
        if callable(elem):
            fn = elem
            ret = fn(passed_kwargs, merged_kwargs)
            invalid_args.extend(ret)

        else:
            elem, error_msg = elem

            if s1.issuperset(elem):
                invalid_args.append((elem, error_msg))

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
    elif isinstance(ob, (int,)) and ob >= 0:
        fileno = ob

    return fileno


def ob_is_fd_based(ob):
    return get_fileno(ob) is not None


def ob_is_tty(ob):
    """checks if an object (like a file-like object) is a tty."""
    fileno = get_fileno(ob)
    is_tty = False
    if fileno is not None:
        is_tty = os.isatty(fileno)
    return is_tty


def ob_is_pipe(ob):
    fileno = get_fileno(ob)
    is_pipe = False
    if fileno:
        fd_stat = os.fstat(fileno)
        is_pipe = stat.S_ISFIFO(fd_stat.st_mode)
    return is_pipe


def output_iterator_validator(passed_kwargs, merged_kwargs):
    invalid = []
    if passed_kwargs.get("no_out") and passed_kwargs.get("iter") in (True, "out"):
        error = "You cannot iterate over output if there is no output"
        invalid.append((("no_out", "iter"), error))
    return invalid


def tty_in_validator(passed_kwargs, merged_kwargs):
    # here we'll validate that people aren't randomly shotgun-debugging different tty
    # options and hoping that they'll work, without understanding what they do
    pairs = (("tty_in", "in"), ("tty_out", "out"))
    invalid = []
    for tty_type, std in pairs:
        if tty_type in passed_kwargs and ob_is_tty(passed_kwargs.get(std, None)):
            error = (
                "`_%s` is a TTY already, so so it doesn't make sense to set up a"
                " TTY with `_%s`" % (std, tty_type)
            )
            invalid.append(((tty_type, std), error))

    # if unify_ttys is set, then both tty_in and tty_out must both be True
    if merged_kwargs["unify_ttys"] and not (
        merged_kwargs["tty_in"] and merged_kwargs["tty_out"]
    ):
        invalid.append(
            (
                ("unify_ttys", "tty_in", "tty_out"),
                "`_tty_in` and `_tty_out` must both be True if `_unify_ttys` is True",
            )
        )

    return invalid


def fg_validator(passed_kwargs, merged_kwargs):
    """fg is not valid with basically every other option"""

    invalid = []
    msg = """\
_fg is invalid with nearly every other option, see warning and workaround here:

    https://amoffat.github.io/sh/sections/special_arguments.html#fg"""
    allowlist = {"env", "fg", "cwd"}
    offending = set(passed_kwargs.keys()) - allowlist

    if "fg" in passed_kwargs and passed_kwargs["fg"] and offending:
        invalid.append(("fg", msg))
    return invalid


def bufsize_validator(passed_kwargs, merged_kwargs):
    """a validator to prevent a user from saying that they want custom
    buffering when they're using an in/out object that will be os.dup'ed to the
    process, and has its own buffering.  an example is a pipe or a tty.  it
    doesn't make sense to tell them to have a custom buffering, since the os
    controls this."""
    invalid = []

    in_ob = passed_kwargs.get("in", None)
    out_ob = passed_kwargs.get("out", None)

    in_buf = passed_kwargs.get("in_bufsize", None)
    out_buf = passed_kwargs.get("out_bufsize", None)

    in_no_buf = ob_is_fd_based(in_ob)
    out_no_buf = ob_is_fd_based(out_ob)

    err = "Can't specify an {target} bufsize if the {target} target is a pipe or TTY"

    if in_no_buf and in_buf is not None:
        invalid.append((("in", "in_bufsize"), err.format(target="in")))

    if out_no_buf and out_buf is not None:
        invalid.append((("out", "out_bufsize"), err.format(target="out")))

    return invalid


def env_validator(passed_kwargs, merged_kwargs):
    """a validator to check that env is a dictionary and that all environment variable
    keys and values are strings. Otherwise, we would exit with a confusing exit code
    255."""
    invalid = []

    env = passed_kwargs.get("env", None)
    if env is None:
        return invalid

    if not isinstance(env, Mapping):
        invalid.append(("env", "env must be dict-like. Got {!r}".format(env)))
        return invalid

    for k, v in passed_kwargs["env"].items():
        if not isinstance(k, str):
            invalid.append(("env", "env key {!r} must be a str".format(k)))
        if not isinstance(v, str):
            invalid.append(
                ("env", "value {!r} of env key {!r} must be a str".format(v, k))
            )

    return invalid


class Command(object):
    """represents an un-run system program, like "ls" or "cd".  because it
    represents the program itself (and not a running instance of it), it should
    hold very little state.  in fact, the only state it does hold is baked
    arguments.

    when a Command object is called, the result that is returned is a
    RunningCommand object, which represents the Command put into an execution
    state."""

    thread_local = threading.local()
    RunningCommandCls = RunningCommand

    _call_args: Dict[str, Any] = {
        "fg": False,  # run command in foreground
        # run a command in the background.  commands run in the background
        # ignore SIGHUP and do not automatically exit when the parent process
        # ends
        "bg": False,
        # automatically report exceptions for background commands
        "bg_exc": True,
        "with": False,  # prepend the command to every command after it
        "in": None,
        "out": None,  # redirect STDOUT
        "err": None,  # redirect STDERR
        "err_to_out": None,  # redirect STDERR to STDOUT
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
        "internal_bufsize": 3 * 1024**2,
        "env": None,
        "piped": None,
        "iter": None,
        "iter_noblock": None,
        # the amount of time to sleep between polling for the iter output queue
        "iter_poll_time": 0.1,
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
        "unify_ttys": False,
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
        "tty_size": (24, 80),
        # whether or not our exceptions should be truncated
        "truncate_exc": True,
        # a function to call after the child forks but before the process execs
        "preexec_fn": None,
        # UID to set after forking. Requires root privileges. Not supported on
        # Windows.
        "uid": None,
        # put the forked process in its own process session?
        "new_session": False,
        # put the forked process in its own process group?
        "new_group": False,
        # pre-process args passed into __call__.  only really useful when used
        # in .bake()
        "arg_preprocess": None,
        # a callable that produces a log message from an argument tuple of the
        # command and the args
        "log_msg": None,
        # whether or not to close all inherited fds. typically, this should be True,
        # as inheriting fds can be a security vulnerability
        "close_fds": True,
        # a allowlist of the integer fds to pass through to the child process. setting
        # this forces close_fds to be True
        "pass_fds": set(),
        # return an instance of RunningCommand always. if this isn't True, then
        # sometimes we may return just a plain unicode string
        "return_cmd": False,
        "async": False,
    }

    # this is a collection of validators to make sure the special kwargs make
    # sense
    _kwarg_validators = (
        (("err", "err_to_out"), "Stderr is already being redirected"),
        (("piped", "iter"), "You cannot iterate when this command is being piped"),
        (
            ("piped", "no_pipe"),
            "Using a pipe doesn't make sense if you've disabled the pipe",
        ),
        output_iterator_validator,
        (("close_fds", "pass_fds"), "Passing `pass_fds` forces `close_fds` to be True"),
        tty_in_validator,
        bufsize_validator,
        env_validator,
        fg_validator,
    )

    def __init__(self, path, search_paths=None):
        found = _which(path, search_paths)

        self._path = ""

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
        self._path = found
        self.__name__ = str(self)

    def __getattribute__(self, name):
        # convenience
        get_attr = partial(object.__getattribute__, self)
        val = None

        if name.startswith("_"):
            val = get_attr(name)

        elif name == "bake":
            val = get_attr("bake")

        # here we have a way of getting past shadowed subcommands.  for example,
        # if "git bake" was a thing, we wouldn't be able to do `git.bake()`
        # because `.bake()` is already a method.  so we allow `git.bake_()`
        elif name.endswith("_"):
            name = name[:-1]

        if val is None:
            val = get_attr("bake")(name)

        return val

    @classmethod
    def _extract_call_args(cls, kwargs):
        """takes kwargs that were passed to a command's __call__ and extracts
        out the special keyword arguments, we return a tuple of special keyword
        args, and kwargs that will go to the exec'ed command"""

        kwargs = kwargs.copy()
        call_args = {}
        for parg, default in cls._call_args.items():
            key = "_" + parg

            if key in kwargs:
                call_args[parg] = kwargs[key]
                del kwargs[key]

        merged_args = cls._call_args.copy()
        merged_args.update(call_args)
        invalid_kwargs = special_kwarg_validator(
            call_args, merged_args, cls._kwarg_validators
        )

        if invalid_kwargs:
            exc_msg = []
            for kwarg, error_msg in invalid_kwargs:
                exc_msg.append("  %r: %s" % (kwarg, error_msg))
            exc_msg = "\n".join(exc_msg)
            raise TypeError("Invalid special arguments:\n\n%s\n" % exc_msg)

        return call_args, kwargs

    def bake(self, *args, **kwargs):
        """returns a new Command object after baking(freezing) the given
        command arguments which are used automatically when its exec'ed

        special keyword arguments can be temporary baked and additionally be
        overridden in __call__ or in subsequent bakes (basically setting
        defaults)"""

        # construct the base Command
        fn = type(self)(self._path)
        fn._partial = True

        call_args, kwargs = self._extract_call_args(kwargs)

        fn._partial_call_args.update(self._partial_call_args)
        fn._partial_call_args.update(call_args)
        fn._partial_baked_args.extend(self._partial_baked_args)
        sep = call_args.get("long_sep", self._call_args["long_sep"])
        prefix = call_args.get("long_prefix", self._call_args["long_prefix"])
        fn._partial_baked_args.extend(compile_args(args, kwargs, sep, prefix))
        return fn

    def __str__(self):
        baked_args = " ".join(self._partial_baked_args)
        if baked_args:
            baked_args = " " + baked_args
        return self._path + baked_args

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return "<Command %r>" % str(self)

    def __enter__(self):
        self(_with=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        get_prepend_stack().pop()

    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        args = list(args)

        # this will hold our final command, including arguments, that will be
        # exec'ed
        cmd = []

        # this will hold a complete mapping of all our special keyword arguments
        # and their values
        call_args = self.__class__._call_args.copy()

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

        # determine what our real STDIN is. is it something explicitly passed into
        # _in?
        stdin = call_args["in"]

        # now that we have our stdin, let's figure out how we should handle it
        if isinstance(stdin, RunningCommand):
            if stdin.call_args["piped"]:
                stdin = stdin.process
            else:
                stdin = stdin.process._pipe_queue

        processed_args = compile_args(
            args, kwargs, call_args["long_sep"], call_args["long_prefix"]
        )

        # makes sure our arguments are broken up correctly
        split_args = self._partial_baked_args + processed_args

        final_args = split_args

        cmd.extend(final_args)

        # if we're running in foreground mode, we need to completely bypass
        # launching a RunningCommand and OProc and just do a spawn
        if call_args["fg"]:
            cwd = call_args["cwd"] or os.getcwd()
            with pushd(cwd):
                if call_args["env"] is None:
                    exit_code = os.spawnv(os.P_WAIT, cmd[0], cmd)
                else:
                    exit_code = os.spawnve(os.P_WAIT, cmd[0], cmd, call_args["env"])

            exc_class = get_exc_exit_code_would_raise(
                exit_code, call_args["ok_code"], call_args["piped"]
            )
            if exc_class:
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

        rc = self.__class__.RunningCommandCls(cmd, call_args, stdin, stdout, stderr)
        if rc._spawned_and_waited and not call_args["return_cmd"]:
            return str(rc)
        else:
            return rc


def compile_args(a, kwargs, sep, prefix):
    """takes args and kwargs, as they were passed into the command instance
    being executed with __call__, and compose them into a flat list that
    will eventually be fed into exec.  example:

    with this call:

        sh.ls("-l", "/tmp", color="never")

    this function receives

        args = ['-l', '/tmp']
        kwargs = {'color': 'never'}

    and produces

        ['-l', '/tmp', '--color=geneticnever']

    """
    processed_args = []

    # aggregate positional args
    for arg in a:
        if isinstance(arg, (list, tuple)):
            if isinstance(arg, GlobResults) and not arg:
                arg = [arg.path]

            for sub_arg in arg:
                processed_args.append(sub_arg)
        elif isinstance(arg, dict):
            processed_args += _aggregate_keywords(arg, sep, prefix, raw=True)

        # see https://github.com/amoffat/sh/issues/522
        elif arg is None or arg is False:
            pass
        else:
            processed_args.append(str(arg))

    # aggregate the keyword arguments
    processed_args += _aggregate_keywords(kwargs, sep, prefix)

    return processed_args


def _aggregate_keywords(keywords, sep, prefix, raw=False):
    """take our keyword arguments, and a separator, and compose the list of
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

    essentially, using kwargs is a convenience, but it lacks the ability to
    put a '-' in the name, so we do the replacement of '_' to '-' for you.
    but when you really don't want that to happen, you should use a
    dictionary instead with the exact names you want
    """

    processed = []

    for k, maybe_list_of_v in keywords.items():
        # turn our value(s) into a list of values so that we can process them
        # all individually under the same key
        list_of_v = [maybe_list_of_v]
        if isinstance(maybe_list_of_v, (list, tuple)):
            list_of_v = maybe_list_of_v

        for v in list_of_v:
            # we're passing a short arg as a kwarg, example:
            # cut(d="\t")
            if len(k) == 1:
                if v is not False:
                    processed.append("-" + k)
                    if v is not True:
                        processed.append(str(v))

            # we're doing a long arg
            else:
                if not raw:
                    k = k.replace("_", "-")

                # if it's true, it has no value, just pass the name
                if v is True:
                    processed.append(prefix + k)
                # if it's false, skip passing it
                elif v is False:
                    pass

                # we may need to break the argument up into multiple arguments
                elif sep is None or sep == " ":
                    processed.append(prefix + k)
                    processed.append(str(v))
                # otherwise just join it together into a single argument
                else:
                    arg = f"{prefix}{k}{sep}{v}"
                    processed.append(arg)

    return processed


def _start_daemon_thread(fn, name, exc_queue, *a):
    def wrap(*rgs, **kwargs):
        try:
            fn(*rgs, **kwargs)
        except Exception as e:
            exc_queue.put(e)
            raise

    thread = threading.Thread(target=wrap, name=name, args=a)
    thread.daemon = True
    thread.start()
    return thread


def setwinsize(fd, rows_cols):
    """set the terminal size of a tty file descriptor.  borrowed logic
    from pexpect.py"""
    rows, cols = rows_cols
    winsize = getattr(termios, "TIOCSWINSZ", -2146929561)

    s = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, winsize, s)


def construct_streamreader_callback(process, handler):
    """here we're constructing a closure for our streamreader callback.  this
    is used in the case that we pass a callback into _out or _err, meaning we
    want to our callback to handle each bit of output

    we construct the closure based on how many arguments it takes.  the reason
    for this is to make it as easy as possible for people to use, without
    limiting them.  a new user will assume the callback takes 1 argument (the
    data).  as they get more advanced, they may want to terminate the process,
    or pass some stdin back, and will realize that they can pass a callback of
    more args"""

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
        a = handler_args
        if len(a) == 2:
            a = (handler_args[0], handler_args[1]())
        return handler(chunk, *a)

    return fn


def get_exc_exit_code_would_raise(exit_code, ok_codes, sigpipe_ok):
    exc = None
    success = exit_code in ok_codes
    bad_sig = -exit_code in SIGNALS_THAT_SHOULD_THROW_EXCEPTION

    # if this is a piped command, SIGPIPE must be ignored by us and not raise an
    # exception, since it's perfectly normal for the consumer of a process's
    # pipe to terminate early
    if sigpipe_ok and -exit_code == signal.SIGPIPE:
        bad_sig = False
        success = True

    if not success or bad_sig:
        exc = get_rc_exc(exit_code)
    return exc


def handle_process_exit_code(exit_code):
    """this should only ever be called once for each child process"""
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
    """a helper for making system calls immune to EINTR"""
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
    """this class is instantiated by RunningCommand for a command to be exec'd.
    it handles all the nasty business involved with correctly setting up the
    input/output to the child process.  it gets its name for subprocess.Popen
    (process open) but we're calling ours OProc (open process)"""

    _default_window_size = (24, 80)

    # used in redirecting
    STDOUT = -1
    STDERR = -2

    def __init__(
        self,
        command,
        parent_log,
        cmd,
        stdin,
        stdout,
        stderr,
        call_args,
        pipe,
        process_assign_lock,
    ):
        """
        cmd is the full list of arguments that will be exec'd.  it includes the program
        name and all its arguments.

        stdin, stdout, stderr are what the child will use for standard input/output/err.

        call_args is a mapping of all the special keyword arguments to apply to the
        child process.
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
        else:
            target_uid, target_gid = None, None

        # I had issues with getting 'Input/Output error reading stdin' from dd,
        # until I set _tty_out=False
        if ca["piped"]:
            ca["tty_out"] = False

        self._stdin_process = None

        # if the objects that we are passing to the OProc happen to be a
        # file-like object that is a tty, for example `sys.stdin`, then, later
        # on in this constructor, we're going to skip out on setting up pipes
        # and pseudoterminals for those endpoints
        stdin_is_fd_based = ob_is_fd_based(stdin)
        stdout_is_fd_based = ob_is_fd_based(stdout)
        stderr_is_fd_based = ob_is_fd_based(stderr)

        if isinstance(ca["tee"], (str, bool, int)) or ca["tee"] is None:
            tee = {ca["tee"]}
        else:
            tee = set(ca["tee"])
        tee_out = TEE_STDOUT.intersection(tee)
        tee_err = TEE_STDERR.intersection(tee)

        single_tty = ca["tty_in"] and ca["tty_out"] and ca["unify_ttys"]

        # this logic is a little convoluted, but basically this top-level
        # if/else is for consolidating input and output TTYs into a single
        # TTY.  this is the only way some secure programs like ssh will
        # output correctly (is if stdout and stdin are both the same TTY)
        if single_tty:
            # master_fd, slave_fd = pty.openpty()
            #
            # Anything that is written on the master end is provided to the process on
            # the slave end as though it was
            # input typed on a terminal. -"man 7 pty"
            #
            # later, in the child process, we're going to do this, so keep it in mind:
            #
            #    os.dup2(self._stdin_child_fd, 0)
            #    os.dup2(self._stdout_child_fd, 1)
            #    os.dup2(self._stderr_child_fd, 2)
            self._stdin_parent_fd, self._stdin_child_fd = pty.openpty()

            # this makes our parent fds behave like a terminal. it says that the very
            # same fd that we "type" to (for stdin) is the same one that we see output
            # printed to (for stdout)
            self._stdout_parent_fd = os.dup(self._stdin_parent_fd)

            # this line is what makes stdout and stdin attached to the same pty. in
            # other words the process will write to the same underlying fd as stdout
            # as it uses to read from for stdin. this makes programs like ssh happy
            self._stdout_child_fd = os.dup(self._stdin_child_fd)

            self._stderr_parent_fd = os.dup(self._stdin_parent_fd)
            self._stderr_child_fd = os.dup(self._stdin_child_fd)

        # do not consolidate stdin and stdout.  this is the most common use-
        # case
        else:
            # this check here is because we may be doing piping and so our stdin
            # might be an instance of OProc
            if isinstance(stdin, OProc) and stdin.call_args["piped"]:
                self._stdin_child_fd = stdin._pipe_fd
                self._stdin_parent_fd = None
                self._stdin_process = stdin

            elif stdin_is_fd_based:
                self._stdin_child_fd = os.dup(get_fileno(stdin))
                self._stdin_parent_fd = None

            elif ca["tty_in"]:
                self._stdin_parent_fd, self._stdin_child_fd = pty.openpty()

            # tty_in=False is the default
            else:
                self._stdin_child_fd, self._stdin_parent_fd = os.pipe()

            if stdout_is_fd_based and not tee_out:
                self._stdout_child_fd = os.dup(get_fileno(stdout))
                self._stdout_parent_fd = None

            # tty_out=True is the default
            elif ca["tty_out"]:
                self._stdout_parent_fd, self._stdout_child_fd = pty.openpty()

            else:
                self._stdout_parent_fd, self._stdout_child_fd = os.pipe()

            # unless STDERR is going to STDOUT, it ALWAYS needs to be a pipe,
            # and never a PTY.  the reason for this is not totally clear to me,
            # but it has to do with the fact that if STDERR isn't set as the
            # CTTY (because STDOUT is), the STDERR buffer won't always flush
            # by the time the process exits, and the data will be lost.
            # i've only seen this on OSX.
            if stderr is OProc.STDOUT:
                # if stderr is going to stdout, but stdout is a tty or a pipe,
                # we should not specify a read_fd, because stdout is os.dup'ed
                # directly to the stdout fd (no pipe), and so stderr won't have
                # a slave end of a pipe either to dup
                if stdout_is_fd_based and not tee_out:
                    self._stderr_parent_fd = None
                else:
                    self._stderr_parent_fd = os.dup(self._stdout_parent_fd)
                self._stderr_child_fd = os.dup(self._stdout_child_fd)

            elif stderr_is_fd_based and not tee_err:
                self._stderr_child_fd = os.dup(get_fileno(stderr))
                self._stderr_parent_fd = None

            else:
                self._stderr_parent_fd, self._stderr_child_fd = os.pipe()

        piped = ca["piped"]
        self._pipe_fd = None
        if piped:
            fd_to_use = self._stdout_parent_fd
            if piped == "err":
                fd_to_use = self._stderr_parent_fd
            self._pipe_fd = os.dup(fd_to_use)

        new_session = ca["new_session"]
        new_group = ca["new_group"]
        needs_ctty = ca["tty_in"]

        # if we need a controlling terminal, we have to be in a new session where we
        # are the session leader, otherwise we would need to take over the existing
        # process session, and we can't do that(?)
        if needs_ctty:
            new_session = True

        self.ctty = None
        if needs_ctty:
            self.ctty = os.ttyname(self._stdin_child_fd)

        gc_enabled = gc.isenabled()
        if gc_enabled:
            gc.disable()

        # for synchronizing
        session_pipe_read, session_pipe_write = os.pipe()
        exc_pipe_read, exc_pipe_write = os.pipe()

        # this pipe is for synchronizing with the child that the parent has
        # closed its in/out/err fds.  this is a bug on OSX (but not linux),
        # where we can lose output sometimes, due to a race, if we do
        # os.close(self._stdout_child_fd) in the parent after the child starts
        # writing.
        if IS_MACOS:
            close_pipe_read, close_pipe_write = os.pipe()
        else:
            close_pipe_read, close_pipe_write = None, None

        # session id, group id, process id
        self.sid = None
        self.pgid = None
        self.pid = os.fork()

        # child
        if self.pid == 0:  # pragma: no cover
            if IS_MACOS:
                os.read(close_pipe_read, 1)
                os.close(close_pipe_read)
                os.close(close_pipe_write)

            # this is critical
            # our exc_pipe_write must have CLOEXEC enabled. the reason for this is
            # tricky: if our child (the block we're in now), has an exception, we need
            # to be able to write to exc_pipe_write, so that when the parent does
            # os.read(exc_pipe_read), it gets our traceback.  however,
            # os.read(exc_pipe_read) in the parent blocks, so if our child *doesn't*
            # have an exception, and doesn't close the writing end, it hangs forever.
            # not good!  but obviously the child can't close the writing end until it
            # knows it's not going to have an exception, which is impossible to know
            # because but what if os.execv has an exception?  so the answer is CLOEXEC,
            # so that the writing end of the pipe gets closed upon successful exec,
            # and the parent reading the read end won't block (close breaks the block).
            flags = fcntl.fcntl(exc_pipe_write, fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(exc_pipe_write, fcntl.F_SETFD, flags)

            try:
                # ignoring SIGHUP lets us persist even after the controlling terminal
                # is closed
                if ca["bg"] is True:
                    signal.signal(signal.SIGHUP, signal.SIG_IGN)

                # python ignores SIGPIPE by default.  we must make sure to put
                # this behavior back to the default for spawned processes,
                # otherwise SIGPIPE won't kill piped processes, which is what we
                # need, so that we can check the error code of the killed
                # process to see that SIGPIPE killed it
                signal.signal(signal.SIGPIPE, signal.SIG_DFL)

                # put our forked process in a new session?  this will relinquish
                # any control of our inherited CTTY and also make our parent
                # process init
                if new_session:
                    os.setsid()
                elif new_group:
                    os.setpgrp()

                sid = os.getsid(0)
                pgid = os.getpgid(0)
                payload = ("%d,%d" % (sid, pgid)).encode(DEFAULT_ENCODING)
                os.write(session_pipe_write, payload)

                if ca["tty_out"] and not stdout_is_fd_based and not single_tty:
                    # set raw mode, so there isn't any weird translation of
                    # newlines to \r\n and other oddities.  we're not outputting
                    # to a terminal anyways
                    #
                    # we HAVE to do this here, and not in the parent process,
                    # because we have to guarantee that this is set before the
                    # child process is run, and we can't do it twice.
                    tty.setraw(self._stdout_child_fd)

                # if the parent-side fd for stdin exists, close it.  the case
                # where it may not exist is if we're using piping
                if self._stdin_parent_fd:
                    os.close(self._stdin_parent_fd)

                if self._stdout_parent_fd:
                    os.close(self._stdout_parent_fd)

                if self._stderr_parent_fd:
                    os.close(self._stderr_parent_fd)

                os.close(session_pipe_read)
                os.close(exc_pipe_read)

                cwd = ca["cwd"]
                if cwd:
                    os.chdir(cwd)

                os.dup2(self._stdin_child_fd, 0)
                os.dup2(self._stdout_child_fd, 1)
                os.dup2(self._stderr_child_fd, 2)

                # set our controlling terminal, but only if we're using a tty
                # for stdin.  it doesn't make sense to have a ctty otherwise
                if needs_ctty:
                    tmp_fd = os.open(os.ttyname(0), os.O_RDWR)
                    os.close(tmp_fd)

                if ca["tty_out"] and not stdout_is_fd_based:
                    setwinsize(1, ca["tty_size"])

                if ca["uid"] is not None:
                    os.setgid(target_gid)
                    os.setuid(target_uid)

                preexec_fn = ca["preexec_fn"]
                if callable(preexec_fn):
                    preexec_fn()

                close_fds = ca["close_fds"]
                if ca["pass_fds"]:
                    close_fds = True

                if close_fds:
                    pass_fds = {0, 1, 2, exc_pipe_write}
                    pass_fds.update(ca["pass_fds"])

                    # don't inherit file descriptors
                    try:
                        inherited_fds = os.listdir("/dev/fd")
                    except (IOError, OSError):
                        # Some systems don't have /dev/fd. Raises OSError in
                        # Python2, FileNotFoundError on Python3. The latter doesn't
                        # exist on Python2, but inherits from IOError, which does.
                        inherited_fds = os.listdir("/proc/self/fd")
                    inherited_fds = set(int(fd) for fd in inherited_fds) - pass_fds
                    for fd in inherited_fds:
                        try:
                            os.close(fd)
                        except OSError:
                            pass

                # python=3.6, locale=c will fail test_unicode_arg if we don't
                # explicitly encode to bytes via our desired encoding. this does
                # not seem to be the case in other python versions, even if locale=c
                bytes_cmd = [c.encode(ca["encoding"]) for c in cmd]

                # actually execute the process
                if ca["env"] is None:
                    os.execv(bytes_cmd[0], bytes_cmd)
                else:
                    os.execve(bytes_cmd[0], bytes_cmd, ca["env"])

            # we must ensure that we carefully exit the child process on
            # exception, otherwise the parent process code will be executed
            # twice on exception https://github.com/amoffat/sh/issues/202
            #
            # if your parent process experiences an exit code 255, it is most
            # likely that an exception occurred between the fork of the child
            # and the exec.  this should be reported.
            except Exception:  # noqa: E722
                # some helpful debugging
                tb = traceback.format_exc().encode("utf8", "ignore")

                try:
                    os.write(exc_pipe_write, tb)

                except Exception as e:
                    # dump to stderr if we cannot save it to exc_pipe_write
                    sys.stderr.write("\nFATAL SH ERROR: %s\n" % e)

                finally:
                    os._exit(255)

        # parent
        else:
            if gc_enabled:
                gc.enable()

            os.close(self._stdin_child_fd)
            os.close(self._stdout_child_fd)
            os.close(self._stderr_child_fd)

            # tell our child process that we've closed our write_fds, so it is
            # ok to proceed towards exec.  see the comment where this pipe is
            # opened, for why this is necessary
            if IS_MACOS:
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
            sid, pgid = (
                os.read(session_pipe_read, 1024).decode(DEFAULT_ENCODING).split(",")
            )
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

            self.stdin = stdin

            # this accounts for when _out is a callable that is passed stdin.  in that
            # case, if stdin is unspecified, we must set it to a queue, so callbacks can
            # put things on it
            if callable(ca["out"]) and self.stdin is None:
                self.stdin = Queue()

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

            if ca["tty_in"] and not stdin_is_fd_based:
                setwinsize(self._stdin_parent_fd, ca["tty_size"])

            self.log = parent_log.get_child("process", repr(self))

            self.log.debug("started process")

            # disable echoing, but only if it's a tty that we created ourselves
            if ca["tty_in"] and not stdin_is_fd_based:
                attr = termios.tcgetattr(self._stdin_parent_fd)
                attr[3] &= ~termios.ECHO
                termios.tcsetattr(self._stdin_parent_fd, termios.TCSANOW, attr)

            # this represents the connection from a Queue object (or whatever
            # we're using to feed STDIN) to the process's STDIN fd
            self._stdin_stream = None
            if self._stdin_parent_fd:
                log = self.log.get_child("streamwriter", "stdin")
                self._stdin_stream = StreamWriter(
                    log,
                    self._stdin_parent_fd,
                    self.stdin,
                    ca["in_bufsize"],
                    ca["encoding"],
                    ca["tty_in"],
                )

            stdout_pipe = None
            if pipe is OProc.STDOUT and not ca["no_pipe"]:
                stdout_pipe = self._pipe_queue

            # this represents the connection from a process's STDOUT fd to
            # wherever it has to go, sometimes a pipe Queue (that we will use
            # to pipe data to other processes), and also an internal deque
            # that we use to aggregate all the output
            save_stdout = not ca["no_out"] and (tee_out or stdout is None)

            pipe_out = ca["piped"] in ("out", True)
            pipe_err = ca["piped"] in ("err",)

            # if we're piping directly into another process's file descriptor, we
            # bypass reading from the stdout stream altogether, because we've
            # already hooked up this processes's stdout fd to the other
            # processes's stdin fd
            self._stdout_stream = None
            if not pipe_out and self._stdout_parent_fd:
                if callable(stdout):
                    stdout = construct_streamreader_callback(self, stdout)
                self._stdout_stream = StreamReader(
                    self.log.get_child("streamreader", "stdout"),
                    self._stdout_parent_fd,
                    stdout,
                    self._stdout,
                    ca["out_bufsize"],
                    ca["encoding"],
                    ca["decode_errors"],
                    stdout_pipe,
                    save_data=save_stdout,
                )

            elif self._stdout_parent_fd:
                os.close(self._stdout_parent_fd)

            # if stderr is going to one place (because it's grouped with stdout,
            # or we're dealing with a single tty), then we don't actually need a
            # stream reader for stderr, because we've already set one up for
            # stdout above
            self._stderr_stream = None
            if (
                stderr is not OProc.STDOUT
                and not single_tty
                and not pipe_err
                and self._stderr_parent_fd
            ):
                stderr_pipe = None
                if pipe is OProc.STDERR and not ca["no_pipe"]:
                    stderr_pipe = self._pipe_queue

                save_stderr = not ca["no_err"] and (tee_err or stderr is None)

                if callable(stderr):
                    stderr = construct_streamreader_callback(self, stderr)

                self._stderr_stream = StreamReader(
                    Logger("streamreader"),
                    self._stderr_parent_fd,
                    stderr,
                    self._stderr,
                    ca["err_bufsize"],
                    ca["encoding"],
                    ca["decode_errors"],
                    stderr_pipe,
                    save_data=save_stderr,
                )

            elif self._stderr_parent_fd:
                os.close(self._stderr_parent_fd)

            def timeout_fn():
                self.timed_out = True
                self.signal(ca["timeout_signal"])

            self._timeout_event = None
            self._timeout_timer = None
            if ca["timeout"]:
                self._timeout_event = threading.Event()
                self._timeout_timer = threading.Timer(
                    ca["timeout"], self._timeout_event.set
                )
                self._timeout_timer.start()

            # this is for cases where we know that the RunningCommand that was
            # launched was not .wait()ed on to complete.  in those unique cases,
            # we allow the thread that processes output to report exceptions in
            # that thread.  it's important that we only allow reporting of the
            # exception, and nothing else (like the additional stuff that
            # RunningCommand.wait() does), because we want the exception to be
            # re-raised in the future, if we DO call .wait()
            handle_exit_code = None
            if (
                not self.command._spawned_and_waited
                and ca["bg_exc"]
                # we don't want background exceptions if we're doing async stuff,
                # because we want those to bubble up.
                and not ca["async"]
            ):

                def fn(exit_code):
                    with process_assign_lock:
                        return self.command.handle_command_exit_code(exit_code)

                handle_exit_code = fn

            self._quit_threads = threading.Event()

            thread_name = "background thread for pid %d" % self.pid
            self._bg_thread_exc_queue = Queue(1)
            self._background_thread = _start_daemon_thread(
                background_thread,
                thread_name,
                self._bg_thread_exc_queue,
                timeout_fn,
                self._timeout_event,
                handle_exit_code,
                self.is_alive,
                self._quit_threads,
            )

            # start the main io threads. stdin thread is not needed if we are
            # connecting from another process's stdout pipe
            self._input_thread = None
            self._input_thread_exc_queue = Queue(1)
            if self._stdin_stream:
                close_before_term = not needs_ctty
                thread_name = "STDIN thread for pid %d" % self.pid
                self._input_thread = _start_daemon_thread(
                    input_thread,
                    thread_name,
                    self._input_thread_exc_queue,
                    self.log,
                    self._stdin_stream,
                    self.is_alive,
                    self._quit_threads,
                    close_before_term,
                )

            # this event is for cases where the subprocess that we launch
            # launches its OWN subprocess and os.dup's the stdout/stderr fds to that
            # new subprocess.  in that case, stdout and stderr will never EOF,
            # so our output_thread will never finish and will hang.  this event
            # prevents that hanging
            self._stop_output_event = threading.Event()

            # we need to set up a callback to fire when our `output_thread` is about
            # to exit. this callback will set an asyncio Event, so that coroutiens can
            # be notified that our output is finished.
            # if the `sh` command was launched from within a thread (so we're not in
            # the main thread), then we won't have an event loop.
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:

                def output_complete():
                    pass

            else:

                def output_complete():
                    loop.call_soon_threadsafe(self.command.aio_output_complete.set)

            self._output_thread_exc_queue = Queue(1)
            thread_name = "STDOUT/ERR thread for pid %d" % self.pid
            self._output_thread = _start_daemon_thread(
                output_thread,
                thread_name,
                self._output_thread_exc_queue,
                self.log,
                self._stdout_stream,
                self._stderr_stream,
                self._timeout_event,
                self.is_alive,
                self._quit_threads,
                self._stop_output_event,
                output_complete,
            )

    def __repr__(self):
        return "<Process %d %r>" % (self.pid, self.cmd[:500])

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
        """return the CURRENT group id of the process. this differs from
        self.pgid in that this reflects the current state of the process, where
        self.pgid is the group id at launch"""
        return os.getpgid(self.pid)

    def get_sid(self):
        """return the CURRENT session id of the process. this differs from
        self.sid in that this reflects the current state of the process, where
        self.sid is the session id at launch"""
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
        """polls if our child process has completed, without blocking.  this
        method has side-effects, such as setting our exit_code, if we happen to
        see our child exit while this is running"""

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
        #
        # Using a small timeout provides backpressure against code that spams
        # calls to .is_alive() which may block the main thread from acquiring
        # the lock otherwise.
        acquired = self._wait_lock.acquire(timeout=0.00001)
        if not acquired:
            if self.exit_code is not None:
                return False, self.exit_code
            return True, self.exit_code

        witnessed_end = False
        try:
            # WNOHANG is just that...we're calling waitpid without hanging...
            # essentially polling the process.  the return result is (0, 0) if
            # there's no process status, so we check that pid == self.pid below
            # in order to determine how to proceed
            pid, exit_code = no_interrupt(os.waitpid, self.pid, os.WNOHANG)
            if pid == self.pid:
                self.exit_code = handle_process_exit_code(exit_code)
                witnessed_end = True

                return False, self.exit_code

        # no child process
        except OSError:
            return False, self.exit_code
        else:
            return True, self.exit_code
        finally:
            self._wait_lock.release()
            if witnessed_end:
                self._process_just_ended()

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
        if self._stdin_parent_fd and not self._stdin_stream:
            os.close(self._stdin_parent_fd)

    def wait(self):
        """waits for the process to complete, handles the exit code"""

        self.log.debug("acquiring wait lock to wait for completion")
        # using the lock in a with-context blocks, which is what we want if
        # we're running wait()
        with self._wait_lock:
            self.log.debug("got wait lock")
            witnessed_end = False

            if self.exit_code is None:
                self.log.debug("exit code not set, waiting on pid")
                pid, exit_code = no_interrupt(os.waitpid, self.pid, 0)  # blocks
                self.exit_code = handle_process_exit_code(exit_code)
                witnessed_end = True

            else:
                self.log.debug(
                    "exit code already set (%d), no need to wait", self.exit_code
                )
        self._process_exit_cleanup(witnessed_end=witnessed_end)
        return self.exit_code

    def _process_exit_cleanup(self, witnessed_end):
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


def input_thread(log, stdin, is_alive, quit_thread, close_before_term):
    """this is run in a separate thread.  it writes into our process's
    stdin (a streamwriter) and waits the process to end AND everything that
    can be written to be written"""

    closed = False
    alive = True
    poller = Poller()
    poller.register_write(stdin)

    while poller and alive:
        changed = poller.poll(1)
        for fd, events in changed:
            if events & (POLLER_EVENT_WRITE | POLLER_EVENT_HUP):
                log.debug("%r ready for more input", stdin)
                done = stdin.write()

                if done:
                    poller.unregister(stdin)
                    if close_before_term:
                        stdin.close()
                        closed = True

        alive, _ = is_alive()

    while alive:
        quit_thread.wait(1)
        alive, _ = is_alive()

    if not closed:
        stdin.close()


def event_wait(ev, timeout=None):
    triggered = ev.wait(timeout)
    return triggered


def background_thread(
    timeout_fn, timeout_event, handle_exit_code, is_alive, quit_thread
):
    """handles the timeout logic"""

    # if there's a timeout event, loop
    if timeout_event:
        while not quit_thread.is_set():
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
    if handle_exit_code and not RUNNING_TESTS:  # pragma: no cover
        alive = True
        exit_code = None
        while alive:
            quit_thread.wait(1)
            alive, exit_code = is_alive()

        handle_exit_code(exit_code)


def output_thread(
    log,
    stdout,
    stderr,
    timeout_event,
    is_alive,
    quit_thread,
    stop_output_event,
    output_complete,
):
    """this function is run in a separate thread.  it reads from the
    process's stdout stream (a streamreader), and waits for it to claim that
    its done"""

    poller = Poller()
    if stdout is not None:
        poller.register_read(stdout)
    if stderr is not None:
        poller.register_read(stderr)

    # this is our poll loop for polling stdout or stderr that is ready to
    # be read and processed.  if one of those streamreaders indicate that it
    # is done altogether being read from, we remove it from our list of
    # things to poll.  when no more things are left to poll, we leave this
    # loop and clean up
    while poller:
        changed = no_interrupt(poller.poll, 0.1)
        for f, events in changed:
            if events & (POLLER_EVENT_READ | POLLER_EVENT_HUP):
                log.debug("%r ready to be read from", f)
                done = f.read()
                if done:
                    poller.unregister(f)
            elif events & POLLER_EVENT_ERROR:
                # for some reason, we have to just ignore streams that have had an
                # error.  i'm not exactly sure why, but don't remove this until we
                # figure that out, and create a test for it
                pass

        if timeout_event and timeout_event.is_set():
            break

        if stop_output_event.is_set():
            break

    # we need to wait until the process is guaranteed dead before closing our
    # outputs, otherwise SIGPIPE
    alive, _ = is_alive()
    while alive:
        quit_thread.wait(1)
        alive, _ = is_alive()

    if stdout:
        stdout.close()

    if stderr:
        stderr.close()

    output_complete()


class DoneReadingForever(Exception):
    pass


class NotYetReadyToRead(Exception):
    pass


def determine_how_to_read_input(input_obj):
    """given some kind of input object, return a function that knows how to
    read chunks of that input object.

    each reader function should return a chunk and raise a DoneReadingForever
    exception, or return None, when there's no more data to read

    NOTE: the function returned does not need to care much about the requested
    buffering type (eg, unbuffered vs newline-buffered).  the StreamBufferer
    will take care of that.  these functions just need to return a
    reasonably-sized chunk of data."""

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

    elif isinstance(input_obj, str):
        log_msg = "string"
        get_chunk = get_iter_string_reader(input_obj)

    elif isinstance(input_obj, bytes):
        log_msg = "bytes"
        get_chunk = get_iter_string_reader(input_obj)

    elif isinstance(input_obj, GeneratorType):
        log_msg = "generator"
        get_chunk = get_iter_chunk_reader(iter(input_obj))

    elif input_obj is None:
        log_msg = "None"

        def raise_():
            raise DoneReadingForever

        get_chunk = raise_

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
    """return an iterator that returns a chunk of a string every time it is
    called.  notice that even though bufsize_type might be line buffered, we're
    not doing any line buffering here.  that's because our StreamBufferer
    handles all buffering.  we just need to return a reasonable-sized chunk."""
    bufsize = 1024
    iter_str = (stdin[i : i + bufsize] for i in range(0, len(stdin), bufsize))
    return get_iter_chunk_reader(iter_str)


def get_iter_chunk_reader(stdin):
    def fn():
        try:
            chunk = stdin.__next__()
            return chunk
        except StopIteration:
            raise DoneReadingForever

    return fn


def get_file_chunk_reader(stdin):
    bufsize = 1024

    def fn():
        # python 3.* includes a fileno on stringios, but accessing it throws an
        # exception.  that exception is how we'll know we can't do a poll on
        # stdin
        is_real_file = True
        try:
            stdin.fileno()
        except UnsupportedOperation:
            is_real_file = False

        # this poll is for files that may not yet be ready to read.  we test
        # for fileno because StringIO/BytesIO cannot be used in a poll
        if is_real_file and hasattr(stdin, "fileno"):
            poller = Poller()
            poller.register_read(stdin)
            changed = poller.poll(0.1)
            ready = False
            for fd, events in changed:
                if events & (POLLER_EVENT_READ | POLLER_EVENT_HUP):
                    ready = True
            if not ready:
                raise NotYetReadyToRead

        chunk = stdin.read(bufsize)
        if not chunk:
            raise DoneReadingForever
        else:
            return chunk

    return fn


def bufsize_type_to_bufsize(bf_type):
    """for a given bufsize type, return the actual bufsize we will read.
    notice that although 1 means "newline-buffered", we're reading a chunk size
    of 1024.  this is because we have to read something.  we let a
    StreamBufferer instance handle splitting our chunk on newlines"""

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
    """StreamWriter reads from some input (the stdin param) and writes to a fd
    (the stream param).  the stdin may be a Queue, a callable, something with
    the "read" method, a string, or an iterable"""

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
        """defining this allows us to do poll on an instance of this
        class"""
        return self.stream

    def write(self):
        """attempt to get a chunk of data to write to our child process's
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
                except:  # noqa: E722
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
                # 2.6,2.7,3.3,3.4,3.5,3.6, it only takes 2 ctrl-d to terminate.
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
        if not isinstance(chunk, bytes):
            chunk = chunk.encode(self.encoding)

        for proc_chunk in self.stream_bufferer.process(chunk):
            self.log.debug("got chunk size %d: %r", len(proc_chunk), proc_chunk[:30])

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
        process, finish = get_callback_chunk_consumer(handler, encoding, decode_errors)

    # in py3, this is used for bytes
    elif isinstance(handler, BytesIO):
        process, finish = get_cstringio_chunk_consumer(handler)

    # in py3, this is used for unicode
    elif isinstance(handler, StringIO):
        process, finish = get_stringio_chunk_consumer(handler, encoding, decode_errors)

    elif hasattr(handler, "write"):
        process, finish = get_file_chunk_consumer(handler, decode_errors)

    else:
        try:
            handler = int(handler)
        except (ValueError, TypeError):

            def process(chunk):
                return False  # noqa: E731

            def finish():
                return None  # noqa: E731

        else:
            process, finish = get_fd_chunk_consumer(handler, decode_errors)

    return process, finish


def get_fd_chunk_consumer(handler, decode_errors):
    handler = fdopen(handler, "w", closefd=False)
    return get_file_chunk_consumer(handler, decode_errors)


def get_file_chunk_consumer(handler, decode_errors):
    if getattr(handler, "encoding", None):

        def encode(chunk):
            return chunk.decode(handler.encoding, decode_errors)  # noqa: E731

    else:

        def encode(chunk):
            return chunk  # noqa: E731

    if hasattr(handler, "flush"):
        flush = handler.flush
    else:

        def flush():
            return None  # noqa: E731

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
    """reads from some output (the stream) and sends what it just read to the
    handler."""

    def __init__(
        self,
        log,
        stream,
        handler,
        buffer,
        bufsize_type,
        encoding,
        decode_errors,
        pipe_queue=None,
        save_data=True,
    ):
        self.stream = stream
        self.buffer = buffer
        self.save_data = save_data
        self.encoding = encoding
        self.decode_errors = decode_errors

        self.pipe_queue = None
        if pipe_queue:
            self.pipe_queue = weakref.ref(pipe_queue)

        self.log = log

        self.stream_bufferer = StreamBufferer(
            bufsize_type, self.encoding, self.decode_errors
        )
        self.bufsize = bufsize_type_to_bufsize(bufsize_type)

        self.process_chunk, self.finish_chunk_processor = determine_how_to_feed_output(
            handler, encoding, decode_errors
        )

        self.should_quit = False

    def fileno(self):
        """defining this allows us to do poll on an instance of this
        class"""
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
    """this is used for feeding in chunks of stdout/stderr, and breaking it up
    into chunks that will actually be put into the internal buffers.  for
    example, if you have two processes, one being piped to the other, and you
    want that, first process to feed lines of data (instead of the chunks
    however they come in), OProc will use an instance of this class to chop up
    the data and feed it as lines to be sent down the pipe"""

    def __init__(self, buffer_type, encoding=DEFAULT_ENCODING, decode_errors="strict"):
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
        self.log.debug(
            "acquiring buffering lock to process chunk (buffering: %d)", self.type
        )
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

                    chunk_to_write = chunk[: newline + 1]
                    if self.buffer:
                        chunk_to_write = b"".join(self.buffer) + chunk_to_write

                        self.buffer = []
                        self.n_buffer_count = 0

                    chunk = chunk[newline + 1 :]
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
                        chunk_to_write = ret[: self.type]
                        chunk = ret[self.type :]
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
            self.log.debug(
                "released buffering lock for processing chunk (buffering: %d)",
                self.type,
            )

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
    """pushd changes the actual working directory for the duration of the
    context, unlike the _cwd arg this will work with other built-ins such as
    sh.glob correctly"""
    orig_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(orig_path)


@contextmanager
def _args(**kwargs):
    """allows us to temporarily override all the special keyword parameters in
    a with context"""

    kwargs_str = ",".join(["%s=%r" % (k, v) for k, v in kwargs.items()])

    raise DeprecationWarning(
        """

sh.args() has been deprecated because it was never thread safe.  use the
following instead:

    sh2 = sh({kwargs})
    sh2.your_command()

or

    sh2 = sh({kwargs})
    from sh2 import your_command
    your_command()

""".format(
            kwargs=kwargs_str
        )
    )


class Environment(dict):
    """this allows lookups to names that aren't found in the global scope to be
    searched for as a program name.  for example, if "ls" isn't found in this
    module's scope, we consider it a system program and try to find it.

    we use a dict instead of just a regular object as the base class because the
    exec() statement used in the run_repl requires the "globals" argument to be a
    dictionary"""

    # this is a list of all of the names that the sh module exports that will
    # not resolve to functions.  we don't want to accidentally shadow real
    # commands with functions/imports that we define in sh.py.  for example,
    # "import time" may override the time system program
    allowlist = {
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
        "StreamBufferer",
        "_aggregate_keywords",
        "__project_url__",
        "__version__",
        "__file__",
        "_args",
        "pushd",
        "glob",
        "contrib",
    }

    def __init__(self, globs, baked_args=None):
        """baked_args are defaults for the 'sh' execution context.  for
        example:

            tmp = sh(_out=StringIO())

        'out' would end up in here as an entry in the baked_args dict"""
        super(dict, self).__init__()
        self.globs = globs
        self.baked_args = baked_args or {}

    def __getitem__(self, k):
        if k == "args":
            # Let the deprecated '_args' context manager be imported as 'args'
            k = "_args"

        # if we're trying to import something real, see if it's in our global scope.
        # what defines "real" is that it's in our allowlist
        if k in self.allowlist:
            return self.globs[k]

        # somebody tried to be funny and do "from sh import *"
        if k == "__all__":
            warnings.warn(
                "Cannot import * from sh. Please import sh or import programs "
                "individually."
            )
            return []

        # check if we're naming a dynamically generated ReturnCode exception
        exc = get_exc_from_name(k)
        if exc:
            return exc

        # https://github.com/ipython/ipython/issues/2577
        # https://github.com/amoffat/sh/issues/97#issuecomment-10610629
        if k.startswith("__") and k.endswith("__"):
            raise AttributeError

        # is it a command?
        cmd = resolve_command(k, self.globs[Command.__name__], self.baked_args)
        if cmd:
            return cmd

        # is it a custom builtin?
        builtin = getattr(self, "b_" + k, None)
        if builtin:
            return builtin

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

    # Methods that begin with "b_" are implementations of shell built-ins that
    # people are used to, but which may not have an executable equivalent.
    @staticmethod
    def b_which(program, paths=None):
        return _which(program, paths)


class Contrib(ModuleType):  # pragma: no cover
    @classmethod
    def __call__(cls, name):
        def wrapper1(fn):
            @property
            def cmd_getter(self):
                cmd = resolve_command(name, Command)

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
def git(orig):  # pragma: no cover
    """most git commands play nicer without a TTY"""
    cmd = orig.bake(_tty_out=False)
    return cmd


@contrib("sudo")
def sudo(orig):  # pragma: no cover
    """a nicer version of sudo that uses getpass to ask for a password, or
    allows the first argument to be a string password"""

    prompt = "[sudo] password for %s: " % getpass.getuser()

    def stdin():
        pw = getpass.getpass(prompt=prompt) + "\n"
        yield pw

    def process(a, kwargs):
        password = kwargs.pop("password", None)

        if password is None:
            pass_getter = stdin()
        else:
            pass_getter = password.rstrip("\n") + "\n"

        kwargs["_in"] = pass_getter
        return a, kwargs

    cmd = orig.bake("-S", _arg_preprocess=process)
    return cmd


@contrib("ssh")
def ssh(orig):  # pragma: no cover
    """An ssh command for automatic password login"""

    class SessionContent(object):
        def __init__(self):
            self.chars = deque(maxlen=50000)
            self.lines = deque(maxlen=5000)
            self.line_chars = []
            self.last_line = ""
            self.cur_char = ""

        def append_char(self, char):
            if char == "\n":
                line = self.cur_line
                self.last_line = line
                self.lines.append(line)
                self.line_chars = []
            else:
                self.line_chars.append(char)

            self.chars.append(char)
            self.cur_char = char

        @property
        def cur_line(self):
            line = "".join(self.line_chars)
            return line

    class SSHInteract(object):
        def __init__(self, prompt_match, pass_getter, out_handler, login_success):
            self.prompt_match = prompt_match
            self.pass_getter = pass_getter
            self.out_handler = out_handler
            self.login_success = login_success
            self.content = SessionContent()

            # some basic state
            self.pw_entered = False
            self.success = False

        def __call__(self, char, stdin):
            self.content.append_char(char)

            if self.pw_entered and not self.success:
                self.success = self.login_success(self.content)

            if self.success:
                return self.out_handler(self.content, stdin)

            if self.prompt_match(self.content):
                password = self.pass_getter()
                stdin.put(password + "\n")
                self.pw_entered = True

    def process(a, kwargs):
        real_out_handler = kwargs.pop("interact")
        password = kwargs.pop("password", None)
        login_success = kwargs.pop("login_success", None)
        prompt_match = kwargs.pop("prompt", None)
        prompt = "Please enter SSH password: "

        if prompt_match is None:

            def prompt_match(content):
                return content.cur_line.endswith("password: ")  # noqa: E731

        if password is None:

            def pass_getter():
                return getpass.getpass(prompt=prompt)  # noqa: E731

        else:

            def pass_getter():
                return password.rstrip("\n")  # noqa: E731

        if login_success is None:

            def login_success(content):
                return True  # noqa: E731

        kwargs["_out"] = SSHInteract(
            prompt_match, pass_getter, real_out_handler, login_success
        )
        return a, kwargs

    cmd = orig.bake(
        _out_bufsize=0, _tty_in=True, _unify_ttys=True, _arg_preprocess=process
    )
    return cmd


def run_repl(env):  # pragma: no cover
    banner = "\n>> sh v{version}\n>> https://github.com/amoffat/sh\n"

    print(banner.format(version=__version__))
    while True:
        try:
            line = input("sh> ")
        except (ValueError, EOFError):
            break

        try:
            exec(compile(line, "<dummy>", "single"), env, env)
        except SystemExit:
            break
        except:  # noqa: E722
            print(traceback.format_exc())

    # cleans up our last line
    print("")


# this is a thin wrapper around THIS module (we patch sys.modules[__name__]).
# this is in the case that the user does a "from sh import whatever"
# in other words, they only want to import certain programs, not the whole
# system PATH worth of commands.  in this case, we just proxy the
# import lookup to our Environment class
class SelfWrapper(ModuleType):
    def __init__(self, self_module, baked_args=None):
        # this is super ugly to have to copy attributes like this,
        # but it seems to be the only way to make reload() behave
        # nicely.  if i make these attributes dynamic lookups in
        # __getattr__, reload sometimes chokes in weird ways...
        super(SelfWrapper, self).__init__(
            name=getattr(self_module, "__name__", None),
            doc=getattr(self_module, "__doc__", None),
        )
        for attr in ["__builtins__", "__file__", "__package__"]:
            setattr(self, attr, getattr(self_module, attr, None))

        # python 3.2 (2.7 and 3.3 work fine) breaks on osx (not ubuntu)
        # if we set this to None.  and 3.3 needs a value for __path__
        self.__path__ = []
        self.__self_module = self_module

        # Copy the Command class and add any baked call kwargs to it
        command_cls = Command
        cls_attrs = command_cls.__dict__.copy()
        cls_attrs.pop("__dict__", None)
        if baked_args:
            call_args, _ = command_cls._extract_call_args(baked_args)
            cls_attrs["_call_args"] = cls_attrs["_call_args"].copy()
            cls_attrs["_call_args"].update(call_args)
        globs = globals().copy()
        globs[command_cls.__name__] = type(
            command_cls.__name__, command_cls.__bases__, cls_attrs
        )

        self.__env = Environment(globs, baked_args=baked_args)

    def __getattr__(self, name):
        return self.__env[name]

    def bake(self, **kwargs):
        baked_args = self.__env.baked_args.copy()
        baked_args.update(kwargs)
        new_sh = self.__class__(self.__self_module, baked_args)
        return new_sh


if __name__ == "__main__":  # pragma: no cover
    # we're being run as a stand-alone script
    env = Environment(globals())
    run_repl(env)
else:
    # we're being imported from somewhere
    sys.modules[__name__] = SelfWrapper(sys.modules[__name__])
