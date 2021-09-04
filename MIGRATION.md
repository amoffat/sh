# Migrating from 1.* to 2.*

This document provides an upgrade path from `1.*` to `2.*`.

## Return value now a true string
In `2.*`, the return value of an executed `sh` command has changed (in most cases) from
a `RunningCommand` object to a unicode string. This makes using the output of a command
more natural.

### Workaround
 To continue returning a `RunningCommand` object, you must use the `_return_cmd=True`
 special keyword argument. You can achieve this on each file with the following code at
 the top of files that use `sh`:

```python
import sh as sh2

sh = sh2(_return_cmd=True)
```

## Piping to STDIN
Previously, if the first argument of a sh command was an instance of `RunningCommand`,
it was automatically fed into the process's STDIN. This is no longer the case and you
must explicitly use `_in=`.

### Workaround
None

## Removal of the custom `sh.cd`
`sh.cd` was implemented as a custom function and shadowed the system `cd` binary in
order to be useful. `sh.cd` changed the current working directory globally for the
python script. With the removal of this custom override, calling `sh.cd` will fall back
to your actual system binary, which will only affect the current working directory
*for the duration of the `sh.cd` process.* In other words, it will no longer behave
as intended.

### Workaround
I have inserted a breaking `DeprecationWarning` on all uses of `sh.cd` to help you find
them quickly. Replace those instances with `sh.pushd`. It is like `sh.cd`, but operates
as a context manager with scoping to only affect `sh` commands within the scope:

```python
import sh

with sh.pushd("/tmp"):
    sh.ls()
```