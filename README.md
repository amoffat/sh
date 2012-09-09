sh is a complete subprocess module rewrite that maps your system programs to
Python functions dynamically.  sh helps you write shell scripts in
Python by giving you the good features of Bash (easy command calling, easy
piping) with all the power and flexibility of Python.

```python
from pbs import ifconfig
print ifconfig("eth0")
```

PBS is not a collection of system commands implemented in Python.

# Getting

    $> pip install pbs

# Complete documentation @ http://amoffat.github.com/sh