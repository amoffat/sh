# Migrating from 1._ to 2._

This document provides an upgrade path from `1.*` to `2.*`.

## `sh.cd` builtin removed

There is no `sh.cd` command anymore. It was always command implemented in sh, as
some systems provide it as a shell builtin, while others have an actual binary.
But neither of them persisted the directory change between other `sh` calls,
which is why it was implemented in sh.

### Workaround

If you were using `sh.cd(dir)`, use the context manager `with sh.pushd(dir)`
instead. All of the commands in the managed context will have the correct
directory.

## Return value now a true string

In `2.*`, the return value of an executed `sh` command has changed (in most cases) from
a `RunningCommand` object to a unicode string. This makes using the output of a command
more natural.

### Workaround

To continue returning a `RunningCommand` object, you must use the `_return_cmd=True`
special keyword argument. You can achieve this on each file with the following code at
the top of files that use `sh`:

```python
import sh

sh = sh(_return_cmd=True)
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
_for the duration of the `sh.cd` process._ In other words, it will no longer behave
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

## New processes don't launch in new session

In `1.*`, `_new_session` defaulted to `True`. It now defaults to `False`. The reason
for this is that it makes more sense for launched processes to default to being in
the process group of the python script, so that they receive SIGINTs correctly.

### Workaround

```python
import sh

sh = sh(_new_session=True)
```
