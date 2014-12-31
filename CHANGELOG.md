# Changelog

## 1.10 - 12/30/14

*   partially applied functions with `functools.partial` have been fixed for `_out` and `_err` callbacks [#160](https://github.com/amoffat/sh/issues/160)
*   `_out` or `_err` being callables no longer puts the running command in the background.  to achieve the previous behavior, pass `_bg=True` to your command.
*   deprecated `_with` contexts [#195](https://github.com/amoffat/sh/issues/195)
*   `_timeout_signal` allows you to specify your own signal to kill a timed-out process with.  use a constant from the `signal` stdlib module. [#171](https://github.com/amoffat/sh/issues/171)
*   signal exceptions can now be caught by number or name.  `SignalException_9 == SignalException_SIGKILL`
*   child processes that timeout via `_timeout` raise `sh.TimeoutException` instead of `sh.SignalExeception_9` [#172](https://github.com/amoffat/sh/issues/172)
*   fixed `help(sh)` from the python shell and `pydoc sh` from the command line. [#173](https://github.com/amoffat/sh/issues/173)
*   program names can no longer be shadowed by names that sh.py defines internally. removed the requirement of trailing underscores for programs that could have their names shadowed, like `id`.
*   memory optimization when a child process's stdin is a newline-delimted string and our bufsize is newlines
*   feature, `_done` special keyword argument that accepts a callback to be called when the command completes successfully [#185](https://github.com/amoffat/sh/issues/185)
*   bugfix for being unable to print a baked command in python3+ [#176](https://github.com/amoffat/sh/issues/176)
*   bugfix for cwd not existing and causing the child process to continue running parent process code [#202](https://github.com/amoffat/sh/issues/202)
*   child process is now guaranteed to exit on exception between fork and exec.
*   fix python2 deprecation warning when running with -3 [PR #165](https://github.com/amoffat/sh/pull/165)
*   bugfix where sh.py was attempting to execute directories [#196](https://github.com/amoffat/sh/issues/196), [PR #189](https://github.com/amoffat/sh/pull/189)
*   only backgrounded processes will ignore SIGHUP
*   allowed `ok_code` to take a `range` object. [#PR 210](https://github.com/amoffat/sh/pull/210/files)
*   added `sh.args` with context which allows overriding of all command defaults for the duration of that context.
*   added `sh.pushd` with context which takes a directory name and changes to that directory for the duration of that with context. [PR #206](https://github.com/amoffat/sh/pull/206)
*   tests now include python 3.4 if available.  tests also stop on the first
    python that suite that fails.
*   SIGABRT, SIGBUS, SIGFPE, SIGILL, SIGPIPE, SIGSYS have been added to the list of signals that throw an exception [PR #201](https://github.com/amoffat/sh/pull/201)
*   "callable" builtin has been faked for python3.1, which lacks it.
*   "direct" option added to `_piped` special keyword argument, which allows sh to hand off a process's stdout fd directly to another process, instead of buffering its stdout internally, then handing it off.  [#119](https://github.com/amoffat/sh/issues/119)

## 1.09 - 9/08/13

*   Fixed encoding errors related to a system encoding "ascii". [#123](https://github.com/amoffat/sh/issues/123)
*   Added exit_code attribute to SignalException and ErrorReturnCode exception classes. [#127](https://github.com/amoffat/sh/issues/127)
*   Making the default behavior of spawned processes to not be explicitly killed when the parent python process ends. Also making the spawned process ignore SIGHUP. [#139](https://github.com/amoffat/sh/issues/139)
*   Made OSX sleep hack to apply to PY2 as well as PY3.


## 1.08 - 1/29/12

*	Added SignalException class and made all commands that end terminate by a signal defined in SIGNALS_THAT_SHOULD_THROW_EXCEPTION raise it. [#91](https://github.com/amoffat/sh/issues/91)
*   Bugfix where CommandNotFound was not being raised if Command was created by instantiation.  [#113](https://github.com/amoffat/sh/issues/113)
*   Bugfix for Commands that are wrapped with functools.wraps() [#121](https://github.com/amoffat/sh/issues/121]
*   Bugfix where input arguments were being assumed as ascii or unicode, but never as a string in a different encoding.
*   _long_sep keyword argument added joining together a dictionary of arguments passed in to a command
*   Commands can now be passed a dictionary of args, and the keys will be interpretted "raw", with no underscore-to-hyphen conversion
*   Reserved Python keywords can now be used as subcommands by appending an underscore `_` to them 


## 1.07 - 11/21/12

*   Bugfix for PyDev when `locale.getpreferredencoding()` is empty.
*   Fixes for IPython3 that involve `sh.<tab>` and `sh?`
*   Added `_tee` special keyword argument to force stdout/stderr to store internally and make available for piping data that is being redirected.
*   Added `_decode_errors` to be passed to all stdout/stderr decoding of a process.
*   Added `_no_out`, `_no_err`, and `_no_pipe` special keyword arguments.  These are used for long-running processes with lots of output.
*   Changed custom loggers that were created for each process to fixed loggers, so there are no longer logger references laying around in the logging module after the process ends and it garbage collected.
    

## 1.06 - 11/10/12

*   Removed old undocumented cruft of ARG1..ARGN and ARGV.
*   Bugfix where `logging_enabled` could not be set from the importing module.
*   Disabled garbage collection before fork to prevent garbage collection in child process.
*   Major bugfix where cyclical references were preventing process objects (and their associated stdout/stderr buffers) from being garbage collected.
*   Bugfix in RunningCommand and OProc loggers, which could get really huge if a command was called that had a large number of arguments.


## 1.05 - 10/20/12

*   Changing status from alpha to beta.
*   Python 3.3 officially supported.
*   Documentation fix.  The section on exceptions now references the fact that signals do not raise an exception, even for signals that might seem like they should, e.g. segfault.  
*   Bugfix with Python 3.3 where importing commands from the sh namespace resulted in an error related to `__path__`
*   Long-form and short-form options to commands may now be given False to disable the option from being passed into the command.  This is useful to pass in a boolean flag that you flip to either True or False to enable or disable some functionality at runtime.

## 1.04 - 10/07/12

*   Making `Command` class resolve the `path` parameter with `which` by default instead of expecting it to be resolved before it is passed in.  This change shouldn't affect backwards compatibility.  
*   Fixing a bug when an exception is raised from a program, and the error output has non-ascii text.  This didn't work in Python < 3.0, because .decode()'s default encoding is typically ascii.
