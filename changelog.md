# Changelog

## 1.04 - 10/07/12

*   Making `Command` class resolve the `path` parameter with `which` by default
    instead of expecting it to be resolved before it is passed in.  This change
    shouldn't affect backwards compatibility.
    
*   Fixing a bug when an exception is raised from a program, and the error
    output has non-ascii text.  This didn't work in Python < 3.0, because
    .decode()'s default encoding is typically ascii.