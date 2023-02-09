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

## Removed execution contexts / default arguments

In `1.*` you could do could spawn a new module from the `sh` module, one which
had customized defaults for the special keyword arguments. This module could
then be accessed just like `sh`, and you could even import commands from it.

Unfortunately the magic required to make that work was brittle. Also it was not
aligned syntactically with the similar baking concept. We have therefore changed
the syntax to align with baking, and also removed the ability to import directly
from this new baked execution context.

### Workaround

```python
sh2 = sh(_tty_out=False)
sh2.ls()
```

Becomes:

```python
sh2 = sh.bake(_tty_out=False)
sh2.ls()
```

And

```python
sh2 = sh.bake(_tty_out=False)
from sh2 import ls
ls()
```

Becomes:

```python
sh2 = sh.bake(_tty_out=False)
ls = sh2.ls
ls()
```

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

sh = sh.bake(_return_cmd=True)
```

## Piping to STDIN

Previously, if the first argument of a sh command was an instance of `RunningCommand`,
it was automatically fed into the process's STDIN. This is no longer the case and you
must explicitly use `_in=`.

### Workaround

None

## New processes don't launch in new session

In `1.*`, `_new_session` defaulted to `True`. It now defaults to `False`. The reason
for this is that it makes more sense for launched processes to default to being in
the process group of the python script, so that they receive SIGINTs correctly.

### Workaround

To preserve the old behavior:

```python
import sh

sh = sh.bake(_new_session=True)
```
