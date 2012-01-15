Ever find yourself with a browser tab opened to [Advanced Bash Scripting](http://tldp.org/LDP/abs/html/),
writing obtuse Bash code to do something that would take you 4 seconds in Python?
Yeah, I have too.

Python in Bash Scripts (PBS) is an experimental replacement for your everyday
bash scripts
that gives you the good features of Bash (easy command calling, easy piping)
with the power and flexibility of Python.  The resulting code is a normal Python
script that does Bash-like things easily.

PBS is currently Python 2 only.



# Using

Importing works either from a script (recommended) or from the Python shell:

```python
import pbs
```

Or you run it as a stand-alone REPL:

    $> python pbs.py

Note, _do not_ import like this:

```python
from pbs import *
```

PBS does magic under the hood, so although the examples have top-level commands
like "ls()", these are automatically put in the global scope from "import pbs"


# Examples

## Executing Commands

Commands work like you'd expect:

```python
# print the contents of this directory 
print ls("-l")
```

Note that these aren't Python functions, these are running **the binary
commands** on your system dynamically by resolving your PATH, much like Bash does.

```python
longest_line = wc(__file__, "-L")
```

## Keyword Arguments

Keyword arguments also work like you'd expect: they get replaced with the
long-form commandline option:

```python
# resolves to "curl http://duckduckgo.com/ -o page.html --silent"
curl("http://duckduckgo.com/", "-o page.html", silent=True)

# resolves to "add_user amoffat --system --shell=/bin/bash --no-create-home"
add_user("amoffat", system=True, shell="/bin/bash", no_create_home=True)
```

## Piping

Piping has become function composition:

```python
# sort this directory by biggest file
print sort(du(glob("*"), "-sb"), "-rn")

# print the number of folders and files in /etc
print wc(ls("/etc", "-1"), "-l")
```

## Finding Commands

"Which" finds the full path of a program, or returns None if it doesn't exist.
This command is one of the few commands implemented as a Python function,
and therefore doesn't rely on the "which" program actually existing. 

```python
print which("python") # "/usr/bin/python"
print which("ls") # "/bin/ls"
print which("some_command") # None

if not which("supervisorctl"): apt_get("install", "supervisor", "-y")
```

You can also use the return argument of "which" as the program:

```python
etc_files = str(which("ls")("/etc", "-1")).split()
```

## Environment Variables

Environment variables are available globally much like they are in Bash:

```python
print HOME
print SHELL
print PS1
```

## Exceptions

Exceptions are dynamically generated based on the return code of the command.
This lets you catch a specific return code, or catch all error return codes
through the base class ErrorReturnCode:

```python
try: print ls("/some/non-existant/folder")
except ErrorReturnCode_2:
    print "folder doesn't exist!"
    create_the_folder()
except ErrorReturnCode:
    print "unknown error"
    exit(1)
```

## Commandline Arguments

You can access commandline arguments similar to Bash's $1, $2, etc by using
ARG1, ARG2, etc:

```python
print ARG1, ARG2

# if an argument isn't defined, it's set to None
if ARG10 is None: do_something()
```

You can access the entire argparse/optparse-friendly list of commandline
arguments through "argv".  This is recommended for flexibility:

```python
import argparse
parser = argparse.ArgumentParser(prog="PROG")
parser.add_argument("-x", default=3, type=int)
ns = parser.parse_args(argv)
print ns.x
```


## Background Processes

Commands can be run in the background with the special pbs_bg=True keyword
argument:

```python
# blocks
sleep(3)
print "...3 seconds later"

# doesn't block
p = sleep(3, pbs_bg=True)
print "prints immediately!"
p.wait()
print "...and 3 seconds later"
```

You can also pipe together background processes!

```python
p = wc(curl("http://github.com/", silent=True, pbs_bg=True), "--bytes")
print "prints immediately!"
print "byte count of github: %d" % int(str(p).strip()) # lazily completes
```
