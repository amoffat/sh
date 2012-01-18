PBS is a unique subprocess wrapper that maps your system programs to
Python functions dynamically.  PBS helps you write shell scripts in
Python by giving you the good features of Bash (easy command calling, easy piping)
with all the power and flexibility of Python.



# Usage

Importing works either from a script (recommended) or from the Python shell:

```python
import pbs
```

Or you run it as a stand-alone REPL:

    $> python pbs.py


# Examples

## Executing Commands

Commands work like you'd expect.  **Just call your program's name like
a function:**

```python
# print the contents of this directory 
print ls("-l")

# get the longest line of this file
longest_line = wc(__file__, "-L")

# get interface information
print ifconfig("eth0")
```

Note that these aren't Python functions, these are running the binary
commands on your system dynamically by resolving your PATH, much like Bash does.
In this way, all the programs on your system are easily available
in Python.

## Keyword Arguments

Keyword arguments also work like you'd expect: they get replaced with the
long-form commandline option:

```python
# resolves to "curl http://duckduckgo.com/ -o page.html --silent"
curl("http://duckduckgo.com/", "-o page.html", silent=True)

# resolves to "adduser amoffat --system --shell=/bin/bash --no-create-home"
adduser("amoffat", system=True, shell="/bin/bash", no_create_home=True)
```

## Piping

Piping has become function composition:

```python
# sort this directory by biggest file
print sort(du(glob("*"), "-sb"), "-rn")

# print the number of folders and files in /etc
print wc(ls("/etc", "-1"), "-l")
```

## Sudo

Sudo can be called from a with context:

```python
with sudo:
    print ls("/root")
```

If you're required to enter a password, you will be prompted.  If you need
to run a command in a with context AND call it, for example, specifying
a -p prompt with sudo, you need to use the pbs_with keyword argument:

```python
with sudo(p=">", pbs_with=True):
    print ls("/root")
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
etc_files = which("ls")("/etc", "-1").split()
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
arguments through "ARGV".  This is recommended for flexibility:

```python
import argparse
parser = argparse.ArgumentParser(prog="PROG")
parser.add_argument("-x", default=3, type=int)
ns = parser.parse_args(ARGV)
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
print "byte count of github: %d" % int(p) # lazily completes
```
