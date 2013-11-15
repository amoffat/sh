[![Build
Status](https://travis-ci.org/amoffat/sh.png)](https://travis-ci.org/amoffat/sh)

[![Coverage
Status](https://coveralls.io/repos/amoffat/sh/badge.png?branch=travis)](https://coveralls.io/r/amoffat/sh?branch=travis)

sh (previously [pbs](http://pypi.python.org/pypi/pbs)) is a full-fledged
subprocess replacement for Python 2.6 - 3.2
that allows you to call any program as if it were a function:

```python
from sh import ifconfig
print ifconfig("eth0")
```

sh is not a collection of system commands implemented in Python.

# Installation

    $> pip install sh

# Complete documentation @ http://amoffat.github.com/sh
