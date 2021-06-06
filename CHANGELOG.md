# Changelog
## 1.14.3
*   bugfix where `Command` was not aware of default call args when wrapping the module [#559](https://github.com/amoffat/sh/pull/573)

## 1.14.1 - 10/24/20
*   bugfix where setting `_ok_code` to not include 0, but 0 was the exit code [#545](https://github.com/amoffat/sh/pull/545)

## 1.14.0 - 8/28/20
*   `_env` now more lenient in accepting dictionary-like objects [#527](https://github.com/amoffat/sh/issues/527)
*   `None` and `False` arguments now do not pass through to underlying command [#525](https://github.com/amoffat/sh/pull/525)
*   Implemented `find_spec` on the fancy importer, which fixes some Python3.4+ issues [#536](https://github.com/amoffat/sh/pull/536)

## 1.13.1 - 4/28/20
*   regression fix if `_fg=False` [#520](https://github.com/amoffat/sh/issues/520)

## 1.13.0 - 4/27/20
*   minor Travis CI fixes [#492](https://github.com/amoffat/sh/pull/492)
*   bugfix for boolean long options not respecting `_long_prefix` [#488](https://github.com/amoffat/sh/pull/488)
*   fix deprecation warning on Python 3.6 regexes [#482](https://github.com/amoffat/sh/pull/482)
*   `_pass_fds` and `_close_fds` special kwargs for controlling file descriptor inheritance in child.
*   more efficiently closing inherited fds [#406](https://github.com/amoffat/sh/issues/406)
*   bugfix where passing invalid dictionary to `_env` will cause a mysterious child 255 exit code. [#497](https://github.com/amoffat/sh/pull/497)
*   bugfix where `_in` using 0 or `sys.stdin` wasn't behaving like a TTY, if it was in fact a TTY. [#514](https://github.com/amoffat/sh/issues/514)
*   bugfix where `help(sh)` raised an exception [#455](https://github.com/amoffat/sh/issues/455)
*   bugfix fixing broken interactive ssh tutorial from docs
*   change to automatic tty merging into a single pty if `_tty_in=True` and `_tty_out=True`
*   introducing `_unify_ttys`, default False, which allows explicit tty merging into single pty
*   contrib command for `ssh` connections requiring passwords
*   performance fix for polling output too fast when using `_iter` [#462](https://github.com/amoffat/sh/issues/462)
*   execution contexts can now be used in python shell [#466](https://github.com/amoffat/sh/pull/466)
*   bugfix `ErrorReturnCode` instances can now be pickled
*   bugfix passing empty string or `None` for `_in` hanged [#427](https://github.com/amoffat/sh/pull/427)
*   bugfix where passing a filename or file-like object to `_out` wasn't using os.dup2 [#449](https://github.com/amoffat/sh/issues/449)
*   regression make `_fg` work with `_cwd` again [#330](https://github.com/amoffat/sh/issues/330)
*   an invalid `_cwd` now raises a `ForkException` not an `OSError`.
*   AIX support [#477](https://github.com/amoffat/sh/issues/477)
*   added a `timeout=None` param to `RunningCommand.wait()` [#515](https://github.com/amoffat/sh/issues/515)

## 1.12.14 - 6/6/17
*   bugfix for poor sleep performance [#378](https://github.com/amoffat/sh/issues/378)
*   allow passing raw integer file descriptors for `_out` and `_err` handlers
*   bugfix for when `_tee` and `_out` are used, and the `_out` is a tty or pipe [#384](https://github.com/amoffat/sh/issues/384)
*   bugfix where python 3.3+ detected different arg counts for bound method output callbacks [#380](https://github.com/amoffat/sh/issues/380)

## 1.12.12, 1.12.13 - 3/30/17
*   pypi readme doc bugfix [PR#377](https://github.com/amoffat/sh/pull/377)

## 1.12.11 - 3/13/17

*   bugfix for relative paths to `sh.Command` not expanding to absolute paths [#372](https://github.com/amoffat/sh/issues/372)
*   updated for python 3.6
*   bugfix for SIGPIPE not being handled correctly on pipelined processes [#373](https://github.com/amoffat/sh/issues/373)

## 1.12.10 - 3/02/17

*   bugfix for file descriptors over 1024 [#356](https://github.com/amoffat/sh/issues/356)
*   bugfix when `_err_to_out` is True and `_out` is pipe or tty [#365](https://github.com/amoffat/sh/issues/365)

## 1.12.9 - 1/04/17

*   added `_bg_exc` for silencing exceptions in background threads [#350](https://github.com/amoffat/sh/pull/350)

## 1.12.8 - 12/16/16

*   bugfix for patched glob.glob on python3.5 [#341](https://github.com/amoffat/sh/issues/341)

## 1.12.7 - 12/07/16

*   added `_out` and `_out_bufsize` validator [#346](https://github.com/amoffat/sh/issues/346)
*   bugfix for internal stdout thread running when it shouldn't [#346](https://github.com/amoffat/sh/issues/346)

## 1.12.6 - 12/02/16

*   regression bugfix on timeout [#344](https://github.com/amoffat/sh/issues/344)
*   regression bugfix on `_ok_code=None`

## 1.12.5 - 12/01/16

*   further improvements on cpu usage

## 1.12.4 - 11/30/16

*   regression in cpu usage [#339](https://github.com/amoffat/sh/issues/339)

## 1.12.3 - 11/29/16

*   fd leak regression and fix for flawed fd leak detection test [#337](https://github.com/amoffat/sh/pull/337)

## 1.12.2 - 11/28/16

*   support for `io.StringIO` in python2

## 1.12.1 - 11/28/16

*   added support for using raw file descriptors for `_in`, `_out`, and `_err`
*   removed `.close()`ing `_out` handler if FIFO detected

## 1.12.0 - 11/21/16

*   composed commands no longer propagate `_bg`
*   better support for using `sys.stdin` and `sys.stdout` for `_in` and `_out`
*   bugfix where `which()` would not stop searching at the first valid executable found in PATH
*   added `_long_prefix` for programs whose long arguments start with something other than `--` [#278](https://github.com/amoffat/sh/pull/278)
*   added `_log_msg` for advanced configuration of log message [#311](https://github.com/amoffat/sh/pull/311)
*   added `sh.contrib.sudo`
*   added `_arg_preprocess` for advanced command wrapping
*   alter callable `_in` arguments to signify completion with falsy chunk
*   bugfix where pipes passed into `_out` or `_err` were not flushed on process end [#252](https://github.com/amoffat/sh/pull/252)
*   deprecated `with sh.args(**kwargs)` in favor of `sh2 = sh(**kwargs)`
*   made `sh.pushd` thread safe
*   added `.kill_group()` and `.signal_group()` methods for better process control [#237](https://github.com/amoffat/sh/pull/237)
*   added `new_session` special keyword argument for controlling spawned process session [#266](https://github.com/amoffat/sh/issues/266)
*   bugfix better handling for EINTR on system calls [#292](https://github.com/amoffat/sh/pull/292)
*   bugfix where with-contexts were not threadsafe [#247](https://github.com/amoffat/sh/issues/195)
*   `_uid` new special keyword param for specifying the user id of the process [#133](https://github.com/amoffat/sh/issues/133)
*   bugfix where exceptions were swallowed by processes that weren't waited on [#309](https://github.com/amoffat/sh/issues/309)
*   bugfix where processes that dupd their stdout/stderr to a long running child process would cause sh to hang [#310](https://github.com/amoffat/sh/issues/310)
*   improved logging output [#323](https://github.com/amoffat/sh/issues/323)
*   bugfix for python3+ where binary data was passed into a process's stdin [#325](https://github.com/amoffat/sh/issues/325)
*   Introduced execution contexts which allow baking of common special keyword arguments into all commands [#269](https://github.com/amoffat/sh/issues/269)
*   `Command` and `which` now can take an optional `paths` parameter which specifies the search paths [#226](https://github.com/amoffat/sh/issues/226)
*   `_preexec_fn` option for executing a function after the child process forks but before it execs [#260](https://github.com/amoffat/sh/issues/260)
*   `_fg` reintroduced, with limited functionality.  hurrah! [#92](https://github.com/amoffat/sh/issues/92)
*   bugfix where a command would block if passed a fd for stdin that wasn't yet ready to read [#253](https://github.com/amoffat/sh/issues/253)
*   `_long_sep` can now take `None` which splits the long form arguments into individual arguments [#258](https://github.com/amoffat/sh/issues/258)
*   making `_piped` perform "direct" piping by default (linking fds together).  this fixes memory problems [#270](https://github.com/amoffat/sh/issues/270)
*   bugfix where calling `next()` on an iterable process that has raised `StopIteration`, hangs [#273](https://github.com/amoffat/sh/issues/273)
*   `sh.cd` called with no arguments no changes into the user's home directory, like native `cd` [#275](https://github.com/amoffat/sh/issues/275)
*   `sh.glob` removed entirely.  the rationale is correctness over hand-holding. [#279](https://github.com/amoffat/sh/issues/279)
*   added `_truncate_exc`, defaulting to `True`, which tells our exceptions to truncate output.
*   bugfix for exceptions whose messages contained unicode
*   `_done` callback no longer assumes you want your command put in the background.
*   `_done` callback is now called asynchronously in a separate thread.
*   `_done` callback is called regardless of exception, which is necessary in order to release held resources, for example a process pool

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
