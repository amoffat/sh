# Changelog

## 1.04 - 10/07/12

*   Making `Command` class resolve the `path` parameter with `which` by default
    instead of expecting it to be resolved before it is passed in.  This change
    shouldn't affect backwards compatibility.