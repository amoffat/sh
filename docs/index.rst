sh |version|
============

sh (previously `pbs <http://pypi.python.org/pypi/pbs>`_) is a full-fledged
subprocess interface for Python that
allows you to call any program as if it were a function::

	from sh import ifconfig
	print(ifconfig("wlan0"))
	
Output::

	wlan0	Link encap:Ethernet  HWaddr 00:00:00:00:00:00  
		inet addr:192.168.1.100  Bcast:192.168.1.255  Mask:255.255.255.0
		inet6 addr: ffff::ffff:ffff:ffff:fff/64 Scope:Link
		UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
		RX packets:0 errors:0 dropped:0 overruns:0 frame:0
		TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
		collisions:0 txqueuelen:1000 
		RX bytes:0 (0 GB)  TX bytes:0 (0 GB)
		
More examples::

	# checkout master branch
	git.checkout("master")
	
	# print(the contents of this directory 
	print(ls("-l"))
	
	# get the longest line of this file
	longest_line = wc(__file__, "-L")
	
Note that these aren't Python functions, these are running the binary
commands on your system dynamically by resolving your $PATH, much like Bash does.
In this way, all the programs on your system are easily available to you
from within Python.


To install::

    pip install sh
    
Follow it on Github: http://github.com/amoffat/sh

Tutorials
=========

	.. toctree::
		:glob:
		:maxdepth: 1
	   
		/tutorials/*
   

Basic Features
==============

Command execution
-----------------

Commands are called just like functions.  They may be executed on the sh
namespace, or imported directly from sh::

	import sh
	print(sh.ls("/"))
	
	# same thing as above
	from sh import ls
	print(ls("/"))
	
For commands that have dashes in their names, for example ``/usr/bin/google-chrome``,
substitute the dash for an underscore::

	import sh
	sh.google_chrome("http://google.com")
	
	
.. note::

    For commands with more exotic characters in their names, like ``.``, or
    if you just don't like the "magic"-ness of dynamic lookups, you
    may use sh's ``Command`` wrapper and pass in the absolute path of the
    executable::
	
		import sh
		run = sh.Command("/home/amoffat/run.sh")
		run()
		

Keyword arguments
-----------------

Commands support short-form ``-a`` and long-form ``--arg`` arguments as
keyword arguments::

	# resolves to "curl http://duckduckgo.com/ -o page.html --silent"
	curl("http://duckduckgo.com/", o="page.html", silent=True)
	
	# or if you prefer not to use keyword arguments, this does the same thing:
	curl("http://duckduckgo.com/", "-o", "page.html", "--silent")
	
	# resolves to "adduser amoffat --system --shell=/bin/bash --no-create-home"
	adduser("amoffat", system=True, shell="/bin/bash", no_create_home=True)
	
	# or
	adduser("amoffat", "--system", "--shell", "/bin/bash", "--no-create-home")
	
	
.. _background:
	
Background processes
--------------------

By default, each command runs and completes its process before returning.  If
you have a long-running command, you can put it in the background with the
``_bg=True`` :ref:`special keyword argument <special_arguments>`::

	# blocks
	sleep(3)
	print("...3 seconds later")
	
	# doesn't block
	p = sleep(3, _bg=True)
	print("prints immediately!")
	p.wait()
	print("...and 3 seconds later")


Piping
------

Bash style piping is performed using function composition.  Just pass
one command as the input to another, and sh will create a pipe between the two::

	# sort this directory by biggest file
	print(sort(du(glob("*"), "-sb"), "-rn"))
	
	# print(the number of folders and files in /etc
	print(wc(ls("/etc", "-1"), "-l"))
	
By default, any command that is piping another command in waits for it to
complete.  This behavior can be changed with the ``_piped``
:ref:`special keyword argument <special_arguments>` on the command being
piped, which tells it not to complete before sending its data, but to send
its data incrementally.  See :ref:`advanced_piping` for examples of this.
	

.. _redirection:

Redirection
-----------

sh can redirect the standard and error output streams of a process to a file
or file-like object.  This is done with the special ``_out`` and ``_err``
:ref:`special keyword argument <special_arguments>`. You can pass a filename
or a file object as the argument value.
When the name of an already existing file is passed, the contents of the file
will be overwritten::

	ls(_out="files.list")
	ls("nonexistent", _err="error.txt")
	
You can also redirect to a function.  See :ref:`callbacks`.
	

.. _stdin:

STDIN Processing
----------------

STDIN is sent to a process directly by using a command's ``_in`` 
:ref:`special keyword argument <special_arguments>`::

	print(cat(_in="test")) # prints "test"
	
Any command that takes input from STDIN can be used this way::

	print(tr("[:lower:]", "[:upper:]", _in="sh is awesome")) # SH IS AWESOME
	
You're also not limited to using just strings.  You may use a file object,
a `Queue <http://docs.python.org/library/queue.html#queue-objects>`_, or any iterable
(list, set, dictionary, etc)::

	stdin = ["sh", "is", "awesome"]
	out = tr("[:lower:]", "[:upper:]", _in=stdin)

.. _subcommands:
	
Sub-commands
------------

Many programs have their own command subsets, like git (branch, checkout),
svn (update, status), and sudo (where any command following sudo is considered
a sub-command).  sh handles subcommands through attribute access::

	from sh import git, sudo
	
	# resolves to "git branch -v"
	print(git.branch("-v"))
	print(git("branch", "-v")) # the same command
	
	# resolves to "sudo /bin/ls /root"
	print(sudo.ls("/root"))
	print(sudo("/bin/ls", "/root")) # the same command
	
Sub-commands are mainly syntax sugar that makes calling some programs look conceptually nicer.

.. note::

    If you use sudo, the user executing the script must have the NOPASSWD option
    set for whatever command that user is running, otherwise ``sudo`` will hang.

.. _exit_codes:

Exit codes
----------

Normal processes exit with exit code 0.  This can be seen through a
command's ``exit_code`` property::

	output = ls("/")
	print(output.exit_code) # should be 0
	
If a process ends with an error, and the exit code is not 0, an exception
is generated dynamically.
This lets you catch a specific return code, or catch all error return codes
through the base class ErrorReturnCode::

	try: print(ls("/some/non-existant/folder"))
	except ErrorReturnCode_2:
	    print("folder doesn't exist!")
	    create_the_folder()
	except ErrorReturnCode:
	    print("unknown error")
	    exit(1)
	    
.. note::
	
	Signals **will not** raise an ErrorReturnCode.  The command will return
	as if it succeeded, but its ``exit_code`` property will be set to
	-signal_num.  So, for example, if a command is killed with a SIGHUP, its
	return code will be -1.
	
	    
Some programs return strange error codes even though they succeed.  If you know
which code a program might returns and you don't want to deal with doing 
no-op exception handling, you can use the ``_ok_code``
:ref:`special keyword argument <special_arguments>`::

	import sh
	sh.weird_program(_ok_code=[0,3,5])
	
This means that the command will not generate an exception if the process
exits with 0, 3, or 5 exit code.

.. note::

	If you use ``_ok_code``, you must specify **all** the exit codes that are
	considered "ok", like (typically) 0.
	
	
Glob expansion
--------------

Glob expansion is not performed on your arguments, for example, this will
not work::

	import sh
	sh.ls("*.py")
	
You'll get an error to the effect of ``cannot access '\*.py': No such file or directory``.
This is because the ``*.py`` needs to be glob expanded, not passed in literally::

	import sh
	sh.ls(sh.glob("*.py"))
	
.. note::

	Don't use Python's ``glob.glob`` function, use ``sh.glob``.  Python's
	has edge cases that break with sh.
	

Advanced Features
=================

.. _baking:

Baking
------

sh is capable of "baking" arguments into commands.  This is similar to the
stdlib functools.partial wrapper.  Example::

	from sh import ls
	
	ls = ls.bake("-la")
	print(ls) # "/usr/bin/ls -la"
	
	# resolves to "ls -la /"
	print(ls("/"))

The idea here is that now every call to ``ls`` will have the "-la" arguments
already specified.  This gets *really interesting* when you combine this with
subcommand via attribute access::

	from sh import ssh
	
	# calling whoami on a server.  this is a lot to type out, especially if
	# you wanted to call many commands (not just whoami) back to back on
	# the same server
	iam1 = ssh("myserver.com", "-p 1393", "whoami")
	
	# wouldn't it be nice to bake the common parameters into the ssh command?
	myserver = ssh.bake("myserver.com", p=1393)
	
	print(myserver) # "/usr/bin/ssh myserver.com -p 1393"
	
	# resolves to "/usr/bin/ssh myserver.com -p 1393 whoami"
	iam2 = myserver.whoami()
	
	assert(iam1 == iam2) # True!
	
Now that the "myserver" callable represents a baked ssh command, you
can call anything on the server easily::
	
	# resolves to "/usr/bin/ssh myserver.com -p 1393 tail /var/log/dumb_daemon.log -n 100"
	print(myserver.tail("/var/log/dumb_daemon.log", n=100))
	
	
.. _with_contexts:

'With' contexts
---------------

Commands can be run within a ``with`` context.  Popular commands using this
might be ``sudo`` or ``fakeroot``::

	with sudo:
	    print(ls("/root"))
		
If you need
to run a command in a with context and pass in arguments, for example, specifying
a -p prompt with sudo, you need to use the ``_with`` :ref:`special keyword argument <special_arguments>`.
This let's the command know that it's being run from a with context so
it can behave correctly::

	with sudo(k=True, _with=True):
	    print(ls("/root"))
	    
.. note::

    If you use sudo, the user executing the script must have the NOPASSWD option
    set for whatever command that user is running, otherwise ``sudo`` will hang.

.. _iterable:
	    
Iterating over output
---------------------

You can iterate over long-running commands with the ``_iter``
:ref:`special keyword argument <special_arguments>`.  This creates an iterator
(technically, a generator) that you can
loop over::

	from sh import tail

	# runs forever
	for line in tail("-f", "/var/log/some_log_file.log", _iter=True):
	    print(line)
	    
By default, ``_iter`` iterates over stdout, but you can change set this specifically
by passing either "err" or "out" to _for (instead of True).  Also by default,
output is line-buffered, but you can change this by changing :ref:`buffer_sizes`

.. note::

	If you need a non-blocking iterator, use ``_iter_noblock``.  If the current
	iteration would block, ``errno.EWOULDBLOCK`` will be returned, otherwise
	you'll receive a chunk of output, as normal.
	
.. _callbacks:
	    
STDOUT/ERR callbacks
--------------------
	    
sh can use callbacks to process output incrementally.  This is done much like
redirection: by passing an argument to either the ``_out`` or ``_err`` (or both) 
:ref:`special keyword arguments <special_arguments>`, **except this time, you pass
a callable.**  This callable
will be called for each line (or chunk) of data that your command outputs::

	from sh import tail
	
	def process_output(line):
	    print(line)
	
	p = tail("-f", "/var/log/some_log_file.log", _out=process_output)
	p.wait()

To control whether the callback receives a line or a chunk, please see
:ref:`buffer_sizes`.  To "quit" your callback, simply return True.  This
tells the command not to call your callback anymore.

.. note::

	Returning True does not kill the process, it only keeps the callback from being
	called again.  See :ref:`interactive_callbacks` for how to kill a process
	from a callback.
	
.. note::
	
	``_out`` and ``_err`` don't have to specify callables.  It can be a file-like
	object, a Queue, a StringIO instance, or a filename.  See :ref:`redirection`
	for examples.


.. _interactive_callbacks:
	    
Interactive callbacks
---------------------

Each command launched through sh has an internal STDIN
`Queue <http://docs.python.org/library/queue.html#queue-objects>`_
that can be used from callbacks::

	def interact(line, stdin):
	    if line == "What... is the air-speed velocity of an unladen swallow?":
	        stdin.put("What do you mean? An African or European swallow?")
			
	    elif line == "Huh? I... I don't know that....AAAAGHHHHHH":
	        cross_bridge()
	        return True
			
	    else:
	        stdin.put("I don't know....AAGGHHHHH")
	        return True
			
	sh.bridgekeeper(_out=interact).wait()

You can also kill or terminate your process (or send any signal, really) from
your callback by adding a third argument to receive the process object::

	def process_output(line, stdin, process):
	    print(line)
	    if "ERROR" in line:
	        process.kill()
	        return True
	
	p = tail("-f", "/var/log/some_log_file.log", _out=process_output)
	p.wait()
	
The above code will run, printing lines from ``some_log_file.log`` until the
word "ERROR" appears in a line, at which point the tail process will be killed
and the script will end.

.. note::

	You may also use ``.terminate()`` to send a SIGTERM, or ``.signal(sig)`` to
	send a general `signal <http://docs.python.org/library/signal.html>`_.

.. _buffer_sizes:

Buffer sizes
------------

Buffer sizes are important to consider when you begin to use
:ref:`iterators <iterable>`,
:ref:`advanced piping <advanced_piping>`,
or :ref:`callbacks <callbacks>`.  :ref:`tutorial2` has a good example of why
different buffering modes are needed.
Buffer sizes control how STDIN is read and how STDOUT/ERR
are written to.  Consider the following::

	for chunk in tr("[:lower:]", "[:upper:]", _in="testing", _iter=True):
	    print(chunk)

STDIN is, by default, unbuffered, so the string "testing" is read character
by character.  But the result is still "TESTING", not "T", "E", "S", "T", "I",
"N", "G".  Why?  Because although STDIN is unbuffered, STDOUT is not.  STDIN
is being read character by character, but all of those single characters are
being aggregated to STDOUT, whose default buffering is line buffering.  Try
this instead::

	for chunk in tr("[:lower:]", "[:upper:]", _in="testing", _iter=True, _out_bufsize=0):
	    print(chunk)

Because now we set STDOUT to also be unbuffered with ``_out_bufsize=0`` the result is
"T", "E", "S", "T", "I", "N", "G", as expected.

There are 2 bufsize :ref:`special keyword arguments <special_arguments>`:
``_in_bufsize`` and ``_out_bufsize``.  They may be set to the following values:

.. glossary::

	0
		Unbuffered.  For STDIN, strings and file objects will be read character-by-character,
		while Queues, callables, and iterables will be read item by item.
		
	1
		Line buffered.  For STDIN, data will be passed into the process line-by-line.
		For STDOUT/ERR, data will be output line-by-line.  If any data is remaining
		in the STDOUT or STDIN buffers after all the lines have been consumed, it
		is also consumed/flushed.

	N
		Buffered by N characters.  For STDIN, data will be passed into the process
		<=N characters at a time.  For STDOUT/ERR, data will be output <=N characters
		at a time.  If any data is remaining
		in the STDOUT or STDIN buffers after all the lines have been consumed, it
		is also consumed/flushed.


.. _advanced_piping:

Advanced piping
---------------

By default, all piped commands execute sequentially.  What this means is that the
inner command executes first, then sends its data to the outer command::

	print(wc(ls("/etc", "-1"), "-l"))
	
In the above example, ``ls`` executes, gathers its output, then sends that output
to ``wc``.  This is fine for simple commands, but for commands where you need
parallelism, this isn't good enough.  Take the following example::

	for line in tr(tail("-f", "test.log"), "[:upper:]", "[:lower:]", _iter=True):
	    print(line)
	
**This won't work** because the ``tail -f`` command never finishes.  What you
need is for ``tail`` to send its output to ``tr`` as it receives it.  This is where
the ``_piped`` :ref:`special keyword argument <special_arguments>` comes in handy::

	for line in tr(tail("-f", "test.log", _piped=True), "[:upper:]", "[:lower:]", _iter=True):
	    print(line)
	    
This works by telling ``tail -f`` that it is being used in a pipeline, and that
it should send its output line-by-line to ``tr``.  By default, ``_piped`` sends
stdout, but you can easily make it send stderr instead by using ``_piped="err"``

.. _environments:

Environments
------------

The :ref:`special keyword argument <special_arguments>` ``_env`` allows you
to pass a dictionary of environement variables and their corresponding values::

	import sh
	sh.google_chrome(_env={"SOCKS_SERVER": "localhost:1234"})
	
.. note::

	``_env`` replaces your process's environment completely.  Only the key-value
	pairs in ``_env`` will be used for its environment.  If you want to add new
	environment variables for a process *in addition to* your existing environment,
	try something like this::
	
		import os
		import sh
		
		new_env = os.environ.copy()
		new_env["SOCKS_SERVER"] = "localhost:1234"
		
		sh.google_chrome(_env=new_env)


.. _ttys:

TTYs
----

By default, sh does not attach a `TTY <http://en.wikipedia.org/wiki/Pseudo_terminal#Applications>`_
to STDIN, instead it uses pipes.  However,
some programs behave differently depending on if a TTY is attached to STDIN.
If you need to attach a TTY,
use the :ref:`special keyword argument <special_arguments>`
``_tty_in``.
