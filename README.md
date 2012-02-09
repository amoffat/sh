PBS is a unique subprocess wrapper that maps your system programs to
Python functions dynamically.  PBS helps you write shell scripts in
Python by giving you the good features of Bash (easy command calling, easy
piping) with all the power and flexibility of Python.

```python
from pbs import ifconfig
print ifconfig("eth0")
```

PBS is not a collection of system commands implemented in Python.

# Getting

    $> pip install pbs

# Usage

The easiest way to get up and running is to import pbs
directly or import your program from pbs:

```python
import pbs
print pbs.ifconfig("eth0")

from pbs import ifconfig
print ifconfig("eth0")
```

A less common usage pattern is through PBS Command wrapper, which takes a
full path to a command and returns a callable object.  This is useful for
programs that have weird characters in their names or programs that aren't in
your $PATH:

```python
import pbs
ffmpeg = pbs.Command("/usr/bin/ffmpeg")
ffmpeg(movie_file)
```

The last usage pattern is for trying PBS through an interactive REPL.  By
default, this acts like a star import (so all of your system programs will be
immediately available as functions):

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

You can also call attributes on commands.  This translates to the command
name followed by the attribute name:

```python
from pbs import git

# resolves to "git branch -v"
print git.branch("-v")
```

It turns out this is extremely useful for commands whose first argument is often
another sub-command (like git, svn, time, sudo, etc).
See "Baking" for an advanced usage of this.

## Keyword Arguments

Keyword arguments also work like you'd expect: they get replaced with the
long-form and short-form commandline option:

```python
# resolves to "curl http://duckduckgo.com/ -o page.html --silent"
curl("http://duckduckgo.com/", o="page.html", silent=True)

# or if you prefer not to use keyword arguments, these do the same thing:
curl("http://duckduckgo.com/", "-o page.html", "--silent")
curl("http://duckduckgo.com/", "-o", "page.html", "--silent")

# resolves to "adduser amoffat --system --shell=/bin/bash --no-create-home"
adduser("amoffat", system=True, shell="/bin/bash", no_create_home=True)

# or
adduser("amoffat", "--system", "--shell /bin/bash", "--no-create-home")
```

## Piping

Piping has become function composition:

```python
# sort this directory by biggest file
print sort(du(glob("*"), "-sb"), "-rn")

# print the number of folders and files in /etc
print wc(ls("/etc", "-1"), "-l")
```

## Redirection

PBS can redirect the standard and error output streams of a process to a file. 
This is done with the special _out and _err keyword arguments. You can pass a
filename or a file object as the argument value. When the name of an already 
existing file is passed, the contents of the file will be overwritten.

```python
ls(_out="files.list")
ls("nonexistent", _err="error.txt")
```

PBS can also redirect the error output stream to the standard output stream,
using the special _err_to_out=True keyword argument.


## Sudo and With Contexts

Commands can be run within a "with" context.  Popular commands using this
might be "sudo" or "fakeroot":

```python
with sudo:
    print ls("/root")
```

If you need
to run a command in a with context AND call it, for example, specifying
a -p prompt with sudo, you need to use the "_with" keyword argument.
This let's the command know that it's being run from a with context so
it can behave correctly.

```python
with sudo(p=">", _with=True):
    print ls("/root")
```

## Background Processes

Commands can be run in the background with the special _bg=True keyword
argument:

```python
# blocks
sleep(3)
print "...3 seconds later"

# doesn't block
p = sleep(3, _bg=True)
print "prints immediately!"
p.wait()
print "...and 3 seconds later"
```

You can also pipe together background processes!

```python
p = wc(curl("http://github.com/", silent=True, _bg=True), "--bytes")
print "prints immediately!"
print "byte count of github: %d" % int(p) # lazily completes
```

This lets you start long-running commands at the beginning of your script
(like a file download) and continue performing other commands in the
foreground.


## Foreground Processes

Foreground processes are processes that you want to interact directly with
the default stdout and stdin of your terminal.  In other words, these are
processes that you do not want to return their output as a return value
of their call.  An example would be opening a text editor:

```python
vim(file_to_edit)
```

This will block because pbs will be trying to aggregate the output
of the command to python, without displaying anything to the screen. The
solution is the "_fg" special keyword arg:

```python
vim(file_to_edit, _fg=True)
```

This will open vim as expected and let you use it as expected, with all
the input coming from the keyboard and the output going to the screen.
The return value of a foreground process is an empty string.


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

## Baking

PBS is capable of "baking" arguments into commands.  This is similar
to the stdlib functools.partial wrapper.  An example can speak volumes:

```python
from pbs import ls

ls = ls.bake("-la")
print ls # "/usr/bin/ls -la"

# resolves to "ls / -la"
print ls("/") 
```

The idea is that calling "bake" on a command creates a callable object 
that automatically passes along all of the arguments passed into "bake".
This gets **really interesting** when you combine this with the attribute
access on a command:

```python
from pbs import ssh

# calling whoami on the server.  this is tedious to do if you're running
# any more than a few commands.
iam1 = ssh("myserver.com", "-p 1393", "whoami")

# wouldn't it be nice to bake the common parameters into the ssh command?
myserver = ssh.bake("myserver.com", p=1393)

print myserver # "/usr/bin/ssh myserver.com -p 1393"

# resolves to "/usr/bin/ssh myserver.com -p 1393 whoami"
iam2 = myserver.whoami()

assert(iam1 == iam2) # True!
```

Now that the "myserver" callable represents a baked ssh command, you
can call anything on the server easily:

```python
# resolves to "/usr/bin/ssh myserver.com -p 1393 tail /var/log/dumb_daemon.log -n 100"
print myserver.tail("/var/log/dumb_daemon.log", n=100)
```

## Environment Variables

Environment variables are available much like they are in Bash:

```python
print HOME
print SHELL
print PS1
```

You can set enviroment variables the usual way, through the os.environ
mapping:

```python
import os
os.environ["TEST"] = "123"
```

Now any new subprocess commands called from the script will be able to
access that environment variable.

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

## Globbing

Glob-expansion is not done on your arguments.  For example, this will not work:

```python
from pbs import du
print du("*")
```

You'll get an error to the effect of "cannot access '\*': No such file or directory".
This is because the "\*" needs to be glob expanded:

```python
from pbs import du, glob
print du(glob("*")) 
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


## Weirdly-named Commands

PBS automatically handles underscore-dash conversions.  For example, if you want
to call apt-get:

```python
apt_get("install", "mplayer", y=True)
```

PBS looks for "apt_get", but if it doesn't find it, replaces all underscores
with dashes and searches again.  If the command still isn't found, a
CommandNotFound exception is raised.

Commands with other, less-commonly symbols in their names must be accessed
directly through the "Command" class wrapper.  The Command class takes the full
path to the program as a string:

```python
p27 = Command(which("python2.7"))
print p27("-h")
```

The Command wrapper is also useful for commands that are not in your standard PATH:

```python
script = Command("/tmp/temporary-script.sh")
print script()
```

## Windows Support
PBS now index the internal command from cmd.exe (i.e. at, dir, call, goto and etc.)
and automaticly search for *.exe command in the path

and now this is also possible:

```python
from pbs import ipconfig
print ipconfig("/all")
```

and internal commands:

```python
from pbs import dir
print dir("*.c")
```
