"""
http://amoffat.github.io/sh/
"""
#===============================================================================
# Copyright (C) 2011-2015 by Andrew Moffat
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


__version__ = "1.11"
__project_url__ = "https://github.com/amoffat/sh"



import platform

if "windows" in platform.system().lower():
    raise ImportError("sh %s is currently only supported on linux and osx. \
please install pbs 0.110 (http://pypi.python.org/pypi/pbs) for windows \
support." % __version__)


import sys
IS_PY3 = sys.version_info[0] == 3

import traceback
import os
import re
from glob import glob as original_glob
import time
from types import ModuleType
from functools import partial
import inspect
from contextlib import contextmanager

from locale import getpreferredencoding
DEFAULT_ENCODING = getpreferredencoding() or "UTF-8"


if IS_PY3:
    from io import StringIO
    from io import BytesIO as cStringIO
    from queue import Queue, Empty

    # for some reason, python 3.1 removed the builtin "callable", wtf
    if not hasattr(__builtins__, "callable"):
        def callable(ob):
            return hasattr(ob, "__call__")
else:
    from StringIO import StringIO
    from cStringIO import OutputType as cStringIO
    from Queue import Queue, Empty

IS_OSX = platform.system() == "Darwin"
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SH_LOGGER_NAME = "sh"


import errno
import warnings

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


# TODO remove with contexts in next version
def with_context_warning():
    warnings.warn("""
with contexts are deprecated because they are not thread safe.  they will be \
removed in the next version.  use subcommands instead \
http://amoffat.github.io/sh/#sub-commands. see \
https://github.com/amoffat/sh/issues/195
""".strip(), stacklevel=3)



if IS_PY3:
    raw_input = input
    unicode = str
    basestring = str


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
            s = s.encode(fallback_encoding)
    return s


class ErrorReturnCode(Exception):
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

    def __init__(self, full_cmd, stdout, stderr):
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr


        if self.stdout is None:
            exc_stdout = "<redirected>"
        else:
            exc_stdout = self.stdout[:self.truncate_cap]
            out_delta = len(self.stdout) - len(exc_stdout)
            if out_delta:
                exc_stdout += ("... (%d more, please see e.stdout)" % out_delta).encode()

        if self.stderr is None:
            exc_stderr = "<redirected>"
        else:
            exc_stderr = self.stderr[:self.truncate_cap]
            err_delta = len(self.stderr) - len(exc_stderr)
            if err_delta:
                exc_stderr += ("... (%d more, please see e.stderr)" % err_delta).encode()

        msg = "\n\n  RAN: %r\n\n  STDOUT:\n%s\n\n  STDERR:\n%s" % \
            (full_cmd, exc_stdout.decode(DEFAULT_ENCODING, "replace"),
             exc_stderr.decode(DEFAULT_ENCODING, "replace"))
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




rc_exc_regex = re.compile("(ErrorReturnCode|SignalException)_((\d+)|SIG\w+)")
rc_exc_cache = {}


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


def get_rc_exc(rc_or_sig_name):
    """ takes a exit code, signal number, or signal name, and produces an
    exception that corresponds to that return code.  positive return codes yield
    ErrorReturnCode exception, negative return codes yield SignalException

    we also cache the generated exception so that only one signal of that type
    exists, preserving identity """

    try:
        rc = int(rc_or_sig_name)
    except ValueError:
        rc = -getattr(signal, rc_or_sig_name)

    try:
        return rc_exc_cache[rc]
    except KeyError:
        pass

    if rc > 0:
        name = "ErrorReturnCode_%d" % rc
        base = ErrorReturnCode
    else:
        name = "SignalException_%d" % abs(rc)
        base = SignalException

    exc = type(name, (base,), {"exit_code": rc})
    rc_exc_cache[rc] = exc
    return exc




def which(program):
    def is_exe(fpath):
        return (os.path.exists(fpath) and
                os.access(fpath, os.X_OK) and
                os.path.isfile(os.path.realpath(fpath)))

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        if "PATH" not in os.environ:
            return None
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def resolve_program(program):
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


# we add this thin wrapper to glob.glob because of a specific edge case where
# glob does not expand to anything.  for example, if you try to do
# glob.glob("*.py") and there are no *.py files in the directory, glob.glob
# returns an empty list.  this empty list gets passed to the command, and
# then the command fails with a misleading error message.  this thin wrapper
# ensures that if there is no expansion, we pass in the original argument,
# so that when the command fails, the error message is clearer
def glob(arg):
    return original_glob(arg) or arg



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
        if context:
            context = context.replace("%", "%%")
        self.context = context 
        self.log = logging.getLogger("%s.%s" % (SH_LOGGER_NAME, name))

    def _format_msg(self, msg, *args):
        if self.context:
            msg = "%s: %s" % (self.context, msg)
        return msg % args

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


def friendly_truncate(s, max_len):
    if len(s) > max_len:
        s = "%s...(%d more)" % (s[:max_len], len(s) - max_len)
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

    def __init__(self, cmd, call_args, stdin, stdout, stderr):
        # self.ran is used for auditing what actually ran.  for example, in
        # exceptions, or if you just want to know what was ran after the
        # command ran
        if IS_PY3:
            self.ran = " ".join([arg.decode(DEFAULT_ENCODING, "ignore") for arg in cmd])
        else:
            self.ran = " ".join(cmd)


        friendly_cmd = friendly_truncate(self.ran, 20)
        friendly_call_args = friendly_truncate(str(call_args), 20)

        # we're setting up the logger string here, instead of __repr__ because
        # we reserve __repr__ to behave as if it was evaluating the child
        # process's output
        logger_str = "<Command %r call_args %s>" % (friendly_cmd,
                friendly_call_args)

        self.log = Logger("command", logger_str)
        self.call_args = call_args
        self.cmd = cmd

        self.process = None
        self._process_completed = False
        should_wait = True
        spawn_process = True


        # with contexts shouldn't run at all yet, they prepend
        # to every command in the context
        if call_args["with"]:
            spawn_process = False
            Command._prepend_stack.append(self)


        if call_args["piped"] or call_args["iter"] or call_args["iter_noblock"]:
            should_wait = False

        # we're running in the background, return self and let us lazily
        # evaluate
        if call_args["bg"]:
            should_wait = False

        # redirection
        if call_args["err_to_out"]:
            stderr = OProc.STDOUT


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
        if spawn_process:
            self.log.info("starting process")
            self.process = OProc(self.log, cmd, stdin, stdout, stderr,
                    self.call_args, pipe)

            if should_wait:
                self.wait()


    def wait(self):
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

            # https://github.com/amoffat/sh/issues/185
            if self.call_args["done"]:
                self.call_args["done"](self)

        return self


    def handle_command_exit_code(self, code):
        """ here we determine if we had an exception, or an error code that we
        weren't expecting to see.  if we did, we create and raise an exception
        """
        if (code not in self.call_args["ok_code"] and (code > 0 or -code in
            SIGNALS_THAT_SHOULD_THROW_EXCEPTION)):
            exc = get_rc_exc(code)
            raise exc(self.ran, self.process.stdout, self.process.stderr)



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

    @property
    def pid(self):
        return self.process.pid

    def __len__(self):
        return len(str(self))

    def __enter__(self):
        """ we don't actually do anything here because anything that should have
        been done would have been done in the Command.__call__ call.
        essentially all that has to happen is the comand be pushed on the
        prepend stack. """
        with_context_warning()

    def __iter__(self):
        return self

    def next(self):
        """ allow us to iterate over the output of our command """

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
                    raise StopIteration()
                try:
                    return chunk.decode(self.call_args["encoding"],
                        self.call_args["decode_errors"])
                except UnicodeDecodeError:
                    return chunk

    # python 3
    __next__ = next

    def __exit__(self, typ, value, traceback):
        if self.call_args["with"] and Command._prepend_stack:
            Command._prepend_stack.pop()

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
        if p in ("signal", "terminate", "kill"):
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
    return out \
        and not callable(out) \
        and not hasattr(out, "write") \
        and not isinstance(out, (cStringIO, StringIO))






class Command(object):
    """ represents an un-run system program, like "ls" or "cd".  because it
    represents the program itself (and not a running instance of it), it should
    hold very little state.  in fact, the only state it does hold is baked
    arguments.
    
    when a Command object is called, the result that is returned is a
    RunningCommand object, which represents the Command put into an execution
    state. """
    _prepend_stack = []

    _call_args = {
        # currently unsupported
        #"fg": False, # run command in foreground

        # run a command in the background.  commands run in the background
        # ignore SIGHUP and do not automatically exit when the parent process
        # ends
        "bg": False,

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
        # for example, --arg=derp, '=' is the long_sep
        "long_sep": "=",

        # this is for programs that expect their input to be from a terminal.
        # ssh is one of those programs
        "tty_in": False,
        "tty_out": True,

        "encoding": DEFAULT_ENCODING,
        "decode_errors": "strict",

        # how long the process should run before it is auto-killed
        "timeout": 0,
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

        # will be called when a process terminates without exception.  this
        # option also puts the command in the background, since it doesn't make
        # sense to have an un-backgrounded command with a done callback
        "done": None,

        # a tuple (rows, columns) of the desired size of both the stdout and
        # stdin ttys, if ttys are being used
        "tty_size": (20, 80),
    }

    # these are arguments that cannot be called together, because they wouldn't
    # make any sense
    _incompatible_call_args = (
        #("fg", "bg", "Command can't be run in the foreground and background"),
        ("err", "err_to_out", "Stderr is already being redirected"),
        ("piped", "iter", "You cannot iterate when this command is being piped"),
        ("piped", "no_pipe", "Using a pipe doesn't make sense if you've \
disabled the pipe"),
        ("no_out", "iter", "You cannot iterate over output if there is no \
output"),
    )


    # this method exists because of the need to have some way of letting
    # manual object instantiation not perform the underscore-to-dash command
    # conversion that resolve_program uses.
    #
    # there are 2 ways to create a Command object.  using sh.Command(<program>)
    # or by using sh.<program>.  the method fed into sh.Command must be taken
    # literally, and so no underscore-dash conversion is performed.  the one
    # for sh.<program> must do the underscore-dash converesion, because we
    # can't type dashes in method names
    @classmethod
    def _create(cls, program, **default_kwargs):
        path = resolve_program(program)
        if not path:
            raise CommandNotFound(program)

        cmd = cls(path)
        if default_kwargs:
            cmd = cmd.bake(**default_kwargs)

        return cmd


    def __init__(self, path):
        found = which(path)
        if not found:
            raise CommandNotFound(path)

        self._path = encode_to_py3bytes_or_py2str(found) 

        self._partial = False
        self._partial_baked_args = []
        self._partial_call_args = {}

        # bugfix for functools.wraps.  issue #121
        self.__name__ = str(self)


    def __getattribute__(self, name):
        # convenience
        getattr = partial(object.__getattribute__, self)

        if name.startswith("_"):
            return getattr(name)
        if name == "bake":
            return getattr("bake")
        if name.endswith("_"):
            name = name[:-1]

        return getattr("bake")(name)


    @staticmethod
    def _extract_call_args(kwargs, to_override={}):
        kwargs = kwargs.copy()
        call_args = {}
        for parg, default in Command._call_args.items():
            key = "_" + parg

            if key in kwargs:
                call_args[parg] = kwargs[key]
                del kwargs[key]
            elif parg in to_override:
                call_args[parg] = to_override[parg]

        # test for incompatible call args
        s1 = set(call_args.keys())
        for args in Command._incompatible_call_args:
            args = list(args)
            error = args.pop()

            if s1.issuperset(args):
                raise TypeError("Invalid special arguments %r: %s" % (args, error))

        return call_args, kwargs


    def _aggregate_keywords(self, keywords, sep, raw=False):
        processed = []
        for k, v in keywords.items():
            # we're passing a short arg as a kwarg, example:
            # cut(d="\t")
            if len(k) == 1:
                if v is not False:
                    processed.append(encode_to_py3bytes_or_py2str("-" + k))
                    if v is not True:
                        processed.append(encode_to_py3bytes_or_py2str(v))

            # we're doing a long arg
            else:
                if not raw:
                    k = k.replace("_", "-")

                if v is True:
                    processed.append(encode_to_py3bytes_or_py2str("--" + k))
                elif v is False:
                    pass
                else:
                    arg = encode_to_py3bytes_or_py2str("--%s%s%s" % (k, sep, v))
                    processed.append(arg)
        return processed


    def _compile_args(self, args, kwargs, sep):
        processed_args = []

        # aggregate positional args
        for arg in args:
            if isinstance(arg, (list, tuple)):
                if not arg:
                    warnings.warn("Empty list passed as an argument to %r. \
If you're using glob.glob(), please use sh.glob() instead." % self._path, stacklevel=3)
                for sub_arg in arg:
                    processed_args.append(encode_to_py3bytes_or_py2str(sub_arg))
            elif isinstance(arg, dict):
                processed_args += self._aggregate_keywords(arg, sep, raw=True)
            else:
                processed_args.append(encode_to_py3bytes_or_py2str(arg))

        # aggregate the keyword arguments
        processed_args += self._aggregate_keywords(kwargs, sep)

        return processed_args


    # TODO needs documentation
    def bake(self, *args, **kwargs):
        fn = Command(self._path)
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
        fn._partial_baked_args.extend(self._compile_args(args, kwargs, sep))
        return fn

    def __str__(self):
        """ in python3, should return unicode.  in python2, should return a
        string of bytes """
        if IS_PY3:
            return self.__unicode__()
        else:
            return self.__unicode__().encode(DEFAULT_ENCODING)


    def __eq__(self, other):
        try:
            return str(self) == str(other)
        except:
            return False
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
        with_context_warning()
        self(_with=True)

    def __exit__(self, typ, value, traceback):
        Command._prepend_stack.pop()


    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        args = list(args)

        cmd = []

        # aggregate any 'with' contexts
        call_args = Command._call_args.copy()
        for prepend in self._prepend_stack:
            # don't pass the 'with' call arg
            pcall_args = prepend.call_args.copy()
            try:
                del pcall_args["with"]
            except:
                pass

            call_args.update(pcall_args)
            cmd.extend(prepend.cmd)

        cmd.append(self._path)

        # here we extract the special kwargs and override any
        # special kwargs from the possibly baked command
        tmp_call_args, kwargs = self._extract_call_args(kwargs, self._partial_call_args)
        call_args.update(tmp_call_args)

        if not getattr(call_args["ok_code"], "__iter__", None):
            call_args["ok_code"] = [call_args["ok_code"]]


        if call_args["done"]:
            call_args["bg"] = True

        # check if we're piping via composition
        stdin = call_args["in"]
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, RunningCommand):
                # it makes sense that if the input pipe of a command is running
                # in the background, then this command should run in the
                # background as well
                if first_arg.call_args["bg"]:
                    call_args["bg"] = True

                if first_arg.call_args["piped"] == "direct":
                    stdin = first_arg.process
                else:
                    stdin = first_arg.process._pipe_queue

            else:
                args.insert(0, first_arg)

        processed_args = self._compile_args(args, kwargs, call_args["long_sep"])

        # makes sure our arguments are broken up correctly
        split_args = self._partial_baked_args + processed_args

        final_args = split_args

        cmd.extend(final_args)


        # stdout redirection
        stdout = call_args["out"]
        if output_redirect_is_filename(stdout):
            stdout = open(str(stdout), "wb")

        # stderr redirection
        stderr = call_args["err"]
        if output_redirect_is_filename(stderr):
            stderr = open(str(stderr), "wb")


        return RunningCommand(cmd, call_args, stdin, stdout, stderr)




def _start_daemon_thread(fn, *args):
    thrd = threading.Thread(target=fn, args=args)
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
        num_args = len(inspect.getargspec(handler_to_inspect).args)

    else:
        if inspect.isfunction(handler_to_inspect):
            num_args = len(inspect.getargspec(handler_to_inspect).args)

        # is an object instance with __call__ method
        else:
            implied_arg = 1
            num_args = len(inspect.getargspec(handler_to_inspect.__call__).args)


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



def handle_process_exit_code(exit_code):
    """ this should only ever be called once for each child process """
    # if we exited from a signal, let our exit code reflect that
    if os.WIFSIGNALED(exit_code):
        return -os.WTERMSIG(exit_code)
    # otherwise just give us a normal exit code
    elif os.WIFEXITED(exit_code):
        return os.WEXITSTATUS(exit_code)
    else:
        raise RuntimeError("Unknown child exit status!")




class OProc(object):
    """ this class is instantiated by RunningCommand for a command to be exec'd.
    it handles all the nasty business involved with correctly setting up the
    input/output to the child process.  it gets its name for subprocess.Popen
    (process open) but we're calling ours OProc (open process) """

    _default_window_size = (24, 80)

    # used in redirecting
    STDOUT = -1
    STDERR = -2

    def __init__(self, parent_log, cmd, stdin, stdout, stderr, call_args, pipe):
        """
            cmd is the full string that will be exec'd.  it includes the program
            name and all its arguments

            stdin, stdout, stderr are what the child will use for standard
            input/output/err

            call_args is a mapping of all the special keyword arguments to apply
            to the child process
        """

        self.call_args = call_args

        # I had issues with getting 'Input/Output error reading stdin' from dd,
        # until I set _tty_out=False
        if self.call_args["piped"] == "direct":
            self.call_args["tty_out"] = False

        self._single_tty = self.call_args["tty_in"] and self.call_args["tty_out"]

        # this logic is a little convoluted, but basically this top-level
        # if/else is for consolidating input and output TTYs into a single
        # TTY.  this is the only way some secure programs like ssh will
        # output correctly (is if stdout and stdin are both the same TTY)
        if self._single_tty:
            self._stdin_fd, self._slave_stdin_fd = pty.openpty()

            self._stdout_fd = self._stdin_fd
            self._slave_stdout_fd = self._slave_stdin_fd

            self._stderr_fd = self._stdin_fd
            self._slave_stderr_fd = self._slave_stdin_fd

        # do not consolidate stdin and stdout.  this is the most common use-
        # case
        else:
            # this check here is because we may be doing "direct" piping
            # (_piped="direct"), and so our stdin might be an instance of
            # OProc
            if isinstance(stdin, OProc):
                self._slave_stdin_fd = stdin._stdout_fd
                self._stdin_fd = None
            elif self.call_args["tty_in"]:
                self._slave_stdin_fd, self._stdin_fd = pty.openpty()
            # tty_in=False is the default
            else:
                self._slave_stdin_fd, self._stdin_fd = os.pipe()


            # tty_out=True is the default
            if self.call_args["tty_out"]:
                self._stdout_fd, self._slave_stdout_fd = pty.openpty()
            else:
                self._stdout_fd, self._slave_stdout_fd = os.pipe()

            # unless STDERR is going to STDOUT, it ALWAYS needs to be a pipe,
            # and never a PTY.  the reason for this is not totally clear to me,
            # but it has to do with the fact that if STDERR isn't set as the
            # CTTY (because STDOUT is), the STDERR buffer won't always flush
            # by the time the process exits, and the data will be lost.
            # i've only seen this on OSX.
            if stderr is not OProc.STDOUT:
                self._stderr_fd, self._slave_stderr_fd = os.pipe()


        # this is a hack, but what we're doing here is intentionally throwing an
        # OSError exception if our child processes's directory doesn't exist,
        # but we're doing it BEFORE we fork.  the reason for before the fork is
        # error handling.  i'm currently too lazy to implement what
        # subprocess.py did and set up a error pipe to handle exceptions that
        # happen in the child between fork and exec.  it has only been seen in
        # the wild for a missing cwd, so we'll handle it here.
        cwd = self.call_args["cwd"]
        if cwd is not None and not os.path.exists(cwd):
            os.chdir(cwd)


        gc_enabled = gc.isenabled()
        if gc_enabled:
            gc.disable()
        self.pid = os.fork()


        # child
        if self.pid == 0: # pragma: no cover
            try:
                # ignoring SIGHUP lets us persist even after the parent process
                # exits.  only ignore if we're backgrounded
                if self.call_args["bg"] is True:
                    signal.signal(signal.SIGHUP, signal.SIG_IGN)

                # this piece of ugliness is due to a bug where we can lose output
                # if we do os.close(self._slave_stdout_fd) in the parent after
                # the child starts writing.
                # see http://bugs.python.org/issue15898
                if IS_OSX:
                    time.sleep(0.01)

                os.setsid()

                if self.call_args["tty_out"]:
                    # set raw mode, so there isn't any weird translation of
                    # newlines to \r\n and other oddities.  we're not outputting
                    # to a terminal anyways
                    #
                    # we HAVE to do this here, and not in the parent process,
                    # because we have to guarantee that this is set before the
                    # child process is run, and we can't do it twice.
                    tty.setraw(self._slave_stdout_fd)


                # if the parent-side fd for stdin exists, close it.  the case
                # where it may not exist is if we're using piped="direct"
                if self._stdin_fd:
                    os.close(self._stdin_fd)

                if not self._single_tty:
                    os.close(self._stdout_fd)
                    if stderr is not OProc.STDOUT:
                        os.close(self._stderr_fd)


                if cwd:
                    os.chdir(cwd)

                os.dup2(self._slave_stdin_fd, 0)
                os.dup2(self._slave_stdout_fd, 1)

                # we're not directing stderr to stdout?  then set self._slave_stderr_fd to
                # fd 2, the common stderr fd
                if stderr is OProc.STDOUT:
                    os.dup2(self._slave_stdout_fd, 2)
                else:
                    os.dup2(self._slave_stderr_fd, 2)

                # don't inherit file descriptors
                max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                os.closerange(3, max_fd)


                # set our controlling terminal.  tty_out defaults to true
                if self.call_args["tty_out"]:
                    tmp_fd = os.open(os.ttyname(1), os.O_RDWR)
                    os.close(tmp_fd)


                if self.call_args["tty_out"]:
                    setwinsize(1, self.call_args["tty_size"])

                # actually execute the process
                if self.call_args["env"] is None:
                    os.execv(cmd[0], cmd)
                else:
                    os.execve(cmd[0], cmd, self.call_args["env"])

            # we must ensure that we ALWAYS exit the child process, otherwise
            # the parent process code will be executed twice on exception
            # https://github.com/amoffat/sh/issues/202
            #
            # if your parent process experiences an exit code 255, it is most
            # likely that an exception occurred between the fork of the child
            # and the exec.  this should be reported.
            finally:
                os._exit(255)

        # parent
        else:
            if gc_enabled:
                gc.enable()

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
            self._stdout = deque(maxlen=self.call_args["internal_bufsize"])
            self._stderr = deque(maxlen=self.call_args["internal_bufsize"])

            if self.call_args["tty_in"]:
                setwinsize(self._stdin_fd, self.call_args["tty_size"])


            self.log = parent_log.get_child("process", repr(self))

            os.close(self._slave_stdin_fd)
            if not self._single_tty:
                os.close(self._slave_stdout_fd)
                if stderr is not OProc.STDOUT:
                    os.close(self._slave_stderr_fd)

            self.log.debug("started process")


            if self.call_args["tty_in"]:
                attr = termios.tcgetattr(self._stdin_fd)
                attr[3] &= ~termios.ECHO
                termios.tcsetattr(self._stdin_fd, termios.TCSANOW, attr)

            # this represents the connection from a Queue object (or whatever
            # we're using to feed STDIN) to the process's STDIN fd
            self._stdin_stream = None
            if not isinstance(self.stdin, OProc):
                self._stdin_stream = \
                        StreamWriter(self.log.get_child("streamwriter",
                            "stdin"), self._stdin_fd, self.stdin,
                            self.call_args["in_bufsize"],
                            self.call_args["encoding"],
                            self.call_args["tty_in"])

            stdout_pipe = None
            if pipe is OProc.STDOUT and not self.call_args["no_pipe"]:
                stdout_pipe = self._pipe_queue


            # this represents the connection from a process's STDOUT fd to
            # wherever it has to go, sometimes a pipe Queue (that we will use
            # to pipe data to other processes), and also an internal deque
            # that we use to aggregate all the output
            save_stdout = not self.call_args["no_out"] and \
                (self.call_args["tee"] in (True, "out") or stdout is None)


            # if we're piping directly into another process's filedescriptor, we
            # bypass reading from the stdout stream altogether, because we've
            # already hooked up this processes's stdout fd to the other
            # processes's stdin fd
            self._stdout_stream = None
            if self.call_args["piped"] != "direct":
                if callable(stdout):
                    stdout = construct_streamreader_callback(self, stdout)
                self._stdout_stream = \
                        StreamReader(self.log.get_child("streamreader",
                            "stdout"), self._stdout_fd, stdout, self._stdout,
                            self.call_args["out_bufsize"],
                            self.call_args["encoding"],
                            self.call_args["decode_errors"], stdout_pipe,
                            save_data=save_stdout)

            if stderr is OProc.STDOUT or self._single_tty:
                self._stderr_stream = None
            else:
                stderr_pipe = None
                if pipe is OProc.STDERR and not self.call_args["no_pipe"]:
                    stderr_pipe = self._pipe_queue

                save_stderr = not self.call_args["no_err"] and \
                    (self.call_args["tee"] in ("err",) or stderr is None)

                if callable(stderr):
                    stderr = construct_streamreader_callback(self, stderr)

                self._stderr_stream = StreamReader(Logger("streamreader"),
                    self._stderr_fd, stderr, self._stderr,
                    self.call_args["err_bufsize"], self.call_args["encoding"],
                    self.call_args["decode_errors"], stderr_pipe,
                    save_data=save_stderr)


            # start the main io threads
            # stdin thread is not needed if we are connecting from another process's stdout pipe
            self._input_thread = None
            if self._stdin_stream:
                self._input_thread = _start_daemon_thread(self.input_thread,
                        self._stdin_stream)

            self._output_thread = _start_daemon_thread(self.output_thread,
                    self._stdout_stream, self._stderr_stream,
                    self.call_args["timeout"], self.started,
                    self.call_args["timeout_signal"])


    def __repr__(self):
        return "<Process %d %r>" % (self.pid, self.cmd[:500])


    def change_in_bufsize(self, buf):
        self._stdin_stream.stream_bufferer.change_buffering(buf)

    def change_out_bufsize(self, buf):
        self._stdout_stream.stream_bufferer.change_buffering(buf)

    def change_err_bufsize(self, buf):
        self._stderr_stream.stream_bufferer.change_buffering(buf)


    def input_thread(self, stdin):
        """ this is run in a separate thread.  it writes into our process's
        stdin (a streamwriter) and waits the process to end AND everything that
        can be written to be written """
        done = False
        while not done and self.is_alive():
            self.log.debug("%r ready for more input", stdin)
            done = stdin.write()

        stdin.close()


    def output_thread(self, stdout, stderr, timeout, started, timeout_exc):
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
            outputs, inputs, err = select.select(readers, [], errors, 0.1)

            # stdout and stderr
            for stream in outputs:
                self.log.debug("%r ready to be read from", stream)
                done = stream.read()
                if done:
                    readers.remove(stream)

            for stream in err:
                pass

            # test if the process has been running too long
            if timeout:
                now = time.time()
                if now - started > timeout:
                    self.log.debug("we've been running too long")
                    self.timed_out = True
                    self.signal(timeout_exc)


        # this is here because stdout may be the controlling TTY, and
        # we can't close it until the process has ended, otherwise the
        # child will get SIGHUP.  typically, if we've broken out of
        # the above loop, and we're here, the process is just about to
        # end, so it's probably ok to aggressively poll self.is_alive()
        #
        # the other option to this would be to do the CTTY close from
        # the method that does the actual os.waitpid() call, but the
        # problem with that is that the above loop might still be
        # running, and closing the fd will cause some operation to
        # fail.  this is less complex than wrapping all the ops
        # in the above loop with out-of-band fd-close exceptions
        while self.is_alive():
            time.sleep(0.001)

        if stdout:
            stdout.close()

        if stderr:
            stderr.close()


    @property
    def stdout(self):
        return "".encode(self.call_args["encoding"]).join(self._stdout)

    @property
    def stderr(self):
        return "".encode(self.call_args["encoding"]).join(self._stderr)


    def signal(self, sig):
        self.log.debug("sending signal %d", sig)
        try:
            os.kill(self.pid, sig)
        except OSError:
            pass

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
            return False

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
                return False
            return True

        try:
            # WNOHANG is just that...we're calling waitpid without hanging...
            # essentially polling the process.  the return result is (0, 0) if
            # there's no process status, so we check that pid == self.pid below
            # in order to determine how to proceed
            pid, exit_code = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                self.exit_code = handle_process_exit_code(exit_code)
                return False

        # no child process
        except OSError:
            return False
        else:
            return True
        finally:
            self._wait_lock.release()


    def wait(self):
        """ waits for the process to complete, handles the exit code """

        self.log.debug("acquiring wait lock to wait for completion")
        # using the lock in a with-context blocks, which is what we want if
        # we're running wait()
        with self._wait_lock:
            self.log.debug("got wait lock")

            if self.exit_code is None:
                self.log.debug("exit code not set, waiting on pid")
                pid, exit_code = os.waitpid(self.pid, 0) # blocks
                self.exit_code = handle_process_exit_code(exit_code)
            else:
                self.log.debug("exit code already set (%d), no need to wait", self.exit_code)

            # we may not have a thread for stdin, if the pipe has been connected
            # via _piped="direct"
            if self._input_thread:
                self._input_thread.join()

            # wait for our stdout and stderr streamreaders to finish reading and
            # aggregating the process output
            self._output_thread.join()

            return self.exit_code




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

    else:
        log_msg = "general iterable"
        get_chunk = get_iter_chunk_reader(iter(input_obj))

    return get_chunk, log_msg



def get_queue_chunk_reader(stdin):
    def fn():
        try:
            chunk = stdin.get(True, 0.01)
        except Empty:
            raise NotYetReadyToRead
        if chunk is None:
            raise DoneReadingForever
        return chunk
    return fn


def get_callable_chunk_reader(stdin):
    def fn():
        try:
            return stdin()
        except:
            raise DoneReadingForever
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

        # get_chunk may sometimes return bytes, and sometimes returns trings
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

            if not self.tty_in:
                self.log.debug("we used a TTY, so closing the stream")
                os.close(self.stream)

        except OSError:
            pass



def determine_how_to_feed_output(handler, encoding, decode_errors):
    if callable(handler):
        process, finish = get_callback_chunk_consumer(handler, encoding,
                decode_errors)
    elif isinstance(handler, cStringIO):
        process, finish = get_cstringio_chunk_consumer(handler)
    elif isinstance(handler, StringIO):
        process, finish = get_stringio_chunk_consumer(handler, encoding,
                decode_errors)
    elif hasattr(handler, "write"):
        process, finish = get_file_chunk_consumer(handler)
    else:
        process = lambda chunk: False
        finish = lambda: None

    return process, finish


def get_file_chunk_consumer(handler):
    def process(chunk):
        handler.write(chunk)
        # we should flush on an fd.  chunk is already the correctly-buffered
        # size, so we don't need the fd buffering as well
        handler.flush()
        return False

    def finish():
        if hasattr(handler, "flush"):
            handler.flush()

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

        try:
            os.close(self.stream)
        except OSError:
            pass


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
            chunk = os.read(self.stream, self.bufsize)
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

        # the buffering lock is used because we might chance the buffering
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
            # we've encountered binary, permanently switch to N size buffering
            # since matching on newline doesn't make sense anymore
            if self.type == 1:
                try:
                    chunk.decode(self.encoding, self.decode_errors)
                except:
                    self.log.debug("detected binary data, changing buffering")
                    self.change_buffering(1024)

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
            # we must decode the bytes before we try to match on newline
            elif self.type == 1:
                total_to_write = []
                chunk = chunk.decode(self.encoding, self.decode_errors)
                while True:
                    newline = chunk.find("\n")
                    if newline == -1:
                        break

                    chunk_to_write = chunk[:newline + 1]
                    if self.buffer:
                        # this is ugly, but it's designed to take the existing
                        # bytes buffer, join it together, tack on our latest
                        # chunk, then convert the whole thing to a string.
                        # it's necessary, i'm sure.  read the whole block to
                        # see why.
                        chunk_to_write = "".encode(self.encoding).join(self.buffer) \
                            + chunk_to_write.encode(self.encoding)
                        chunk_to_write = chunk_to_write.decode(self.encoding)

                        self.buffer = []
                        self.n_buffer_count = 0

                    chunk = chunk[newline + 1:]
                    total_to_write.append(chunk_to_write.encode(self.encoding))

                if chunk:
                    self.buffer.append(chunk.encode(self.encoding))
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



@contextmanager
def pushd(path):
    """ pushd is just a specialized form of args, where we're passing in the
    current working directory """
    with args(_cwd=path):
        yield


@contextmanager
def args(*args, **kwargs):
    """ allows us to temporarily override all the special keyword parameters in
    a with context """
    call_args = Command._call_args
    old_args = call_args.copy()

    for key,value in kwargs.items():
        key = key.lstrip("_")
        call_args[key] = value

    yield
    call_args.update(old_args)



class Environment(dict):
    """ this allows lookups to names that aren't found in the global scope to be
    searched for as a program name.  for example, if "ls" isn't found in this
    module's scope, we consider it a system program and try to find it.

    we use a dict instead of just a regular object as the base class because the
    exec() statement used in this file requires the "globals" argument to be a
    dictionary """


    # this is a list of all of the names that the sh module exports that will
    # not resolve to functions.  we don't want to accidentally shadow real
    # commands with functions/imports that we define in sh.py.  for example,
    # "import time" may override the time system program
    whitelist = set([
        "Command",
        "CommandNotFound",
        "DEFAULT_ENCODING",
        "DoneReadingForever",
        "ErrorReturnCode",
        "NotYetReadyToRead",
        "SignalException",
        "TimeoutException",
        "__project_url__",
        "__version__",
        "args",
        "glob",
        "pushd",
    ])

    def __init__(self, globs, baked_args={}):
        self.globs = globs
        self.baked_args = baked_args
        self.disable_whitelist = False

    def __setitem__(self, k, v):
        self.globs[k] = v

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
            try:
                return self.globs[k]
            except KeyError:
                pass

        # somebody tried to be funny and do "from sh import *"
        if k == "__all__":
            raise AttributeError("Cannot import * from sh. \
Please import sh or import programs individually.")


        # check if we're naming a dynamically generated ReturnCode exception
        exc = get_exc_from_name(k)
        if exc:
            return exc


        # https://github.com/ipython/ipython/issues/2577
        # https://github.com/amoffat/sh/issues/97#issuecomment-10610629
        if k.startswith("__") and k.endswith("__"):
            raise AttributeError

        # how about an environment variable?
        try:
            return os.environ[k]
        except KeyError:
            pass

        # is it a custom builtin?
        builtin = getattr(self, "b_" + k, None)
        if builtin:
            return builtin

        # it must be a command then
        # we use _create instead of instantiating the class directly because
        # _create uses resolve_program, which will automatically do underscore-
        # to-dash conversions.  instantiating directly does not use that
        return Command._create(k, **self.baked_args)


    # methods that begin with "b_" are custom builtins and will override any
    # program that exists in our path.  this is useful for things like
    # common shell builtins that people are used to, but which aren't actually
    # full-fledged system binaries

    def b_cd(self, path):
        os.chdir(path)

    def b_which(self, program):
        return which(program)




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
        for attr in ["__builtins__", "__doc__", "__name__", "__package__"]:
            setattr(self, attr, getattr(self_module, attr, None))

        # python 3.2 (2.7 and 3.3 work fine) breaks on osx (not ubuntu)
        # if we set this to None.  and 3.3 needs a value for __path__
        self.__path__ = []
        self.__self_module = self_module
        self.__env = Environment(globals(), baked_args)

    def __setattr__(self, name, value):
        if hasattr(self, "__env"):
            self.__env[name] = value
        else:
            ModuleType.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name == "__env":
            raise AttributeError
        return self.__env[name]

    # accept special keywords argument to define defaults for all operations
    # that will be processed with given by return SelfWrapper
    def __call__(self, **kwargs):
        return SelfWrapper(self.__self_module, kwargs)



# we're being run as a stand-alone script
if __name__ == "__main__": # pragma: no cover
    try:
        arg = sys.argv.pop(1)
    except:
        arg = None

    if arg == "test":
        import subprocess

        def run_test(version, locale):
            py_version = "python%s" % version
            py_bin = which(py_version)

            if py_bin:
                print("Testing %s, locale %r" % (py_version.capitalize(),
                    locale))

                env = os.environ.copy()
                env["LANG"] = locale
                p = subprocess.Popen([py_bin, os.path.join(THIS_DIR, "test.py")]
                    + sys.argv[1:], env=env)
                return_code = p.wait()

                if return_code != 0:
                    exit(1)
            else:
                print("Couldn't find %s, skipping" % py_version.capitalize())

        versions = ("2.6", "2.7", "3.1", "3.2", "3.3", "3.4")
        locales = ("en_US.UTF-8", "C")
        for locale in locales:
            for version in versions:
                run_test(version, locale)

    else:
        env = Environment(globals())
        run_repl(env)

# we're being imported from somewhere
else:
    self = sys.modules[__name__]
    sys.modules[__name__] = SelfWrapper(self)
