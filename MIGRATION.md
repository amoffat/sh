# Migrating from 1.* to 2.*

This document is intended to provide an upgrade path which preserves old 1.* behavior as much as possible.

## Return value

In 2.*, the return value of an executed `sh` command has changed from a `RunningCommand` object to a unicode string.
To continue returning a `RunningCommand` object, you must use the `_return_cmd=True` special keyword argument.