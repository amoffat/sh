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
