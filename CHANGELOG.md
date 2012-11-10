# Changelog

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
