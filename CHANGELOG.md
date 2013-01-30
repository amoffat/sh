# Changelog


## 1.08 - 1/29/12

*	Added SignalException class and made all commands that end terminate by
	a signal defined in SIGNALS_THAT_SHOULD_THROW_EXCEPTION raise it. [#91](https://github.com/amoffat/sh/issues/91)

*   Bugfix where CommandNotFound was not being raised if Command was created
    by instantiation.  [#113](https://github.com/amoffat/sh/issues/113)

*   Bugfix for Commands that are wrapped with functools.wraps() [#121](https://github.com/amoffat/sh/issues/121]

*   Bugfix where input arguments were being assumed as ascii or unicode, but
    never as a string in a different encoding.

*   _long_sep keyword argument added joining together a dictionary of arguments
    passed in to a command

*   Commands can now be passed a dictionary of args, and the keys will be
    interpretted "raw", with no underscore-to-hyphen conversion
    
*   Reserved Python keywords can now be used as subcommands by appending an
	underscore `_` to them 


## 1.07 - 11/21/12

*   Bugfix for PyDev when `locale.getpreferredencoding()` is empty.

*   Fixes for IPython3 that involve `sh.<tab>` and `sh?`

*   Added `_tee` special keyword argument to force stdout/stderr to store
	internally and make available for piping data that is being redirected.

*   Added `_decode_errors` to be passed to all stdout/stderr decoding of a
    process.

*   Added `_no_out`, `_no_err`, and `_no_pipe` special keyword arguments.  These
	are used for long-running processes with lots of output.
	
*   Changed custom loggers that were created for each process to fixed loggers,
    so there are no longer logger references laying around in the logging
    module after the process ends and it garbage collected.
	

## 1.06 - 11/10/12

*   Removed old undocumented cruft of ARG1..ARGN and ARGV.

*   Bugfix where `logging_enabled` could not be set from the importing module.

*   Disabled garbage collection before fork to prevent garbage collection in
	child process.
	
*   Major bugfix where cyclical references were preventing process objects
	(and their associated stdout/stderr buffers) from being garbage collected.
	
*   Bugfix in RunningCommand and OProc loggers, which could get really huge if
    a command was called that had a large number of arguments.


## 1.05 - 10/20/12

*   Changing status from alpha to beta.

*   Python 3.3 officially supported.

*   Documentation fix.  The section on exceptions now references the fact
    that signals do not raise an exception, even for signals that might seem
    like they should, e.g. segfault.

*   Bugfix with Python 3.3 where importing commands from the sh namespace
    resulted in an error related to `__path__`

*   Long-form and short-form options to commands may now be given False to
    disable the option from being passed into the command.  This is useful to
    pass in a boolean flag that you flip to either True or False to enable or
    disable some functionality at runtime.

## 1.04 - 10/07/12

*   Making `Command` class resolve the `path` parameter with `which` by default
    instead of expecting it to be resolved before it is passed in.  This change
    shouldn't affect backwards compatibility.
    
*   Fixing a bug when an exception is raised from a program, and the error
    output has non-ascii text.  This didn't work in Python < 3.0, because
    .decode()'s default encoding is typically ascii.
