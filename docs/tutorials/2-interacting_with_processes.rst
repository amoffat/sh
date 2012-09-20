.. _tutorial2:

Tutorial 2: Entering an SSH password
====================================

Using `subprocesses <http://docs.python.org/library/subprocess.html>`_ to
interact with
SSH is notoriously difficult.  It is recommended that you just ``ssh-copy-id``
to copy your public key to the server so you don't need to enter your password,
but for the purposes of this demonstration, we try to enter a password.

To interact with a process, we need to assign a callback to STDOUT.  See
:ref:`tutorial1` for in-depth explanation of callbacks.  Unlike Tutorial 1,
this callback
will take 2 arguments: the STDOUT chunk and
and a STDIN `Queue <http://docs.python.org/library/queue.html#queue-objects>`_
object that we will ``.put()`` input on to send back to the process.

Here's our first attempt::

	from sh import ssh
	
	def ssh_interact(line, stdin):
	    line = line.strip()
	    print(line)
	    if line.endswith("password:"):
	        stdin.put("correcthorsebatterystaple")
		
	p = ssh("10.10.10.100", _out=ssh_interact)
	p.wait()
	
If you run this (substituting an IP that you can SSH to), you'll notice that
nothing is printed.  The problem has to do with STDOUT buffering.  By default,
sh line-buffers STDOUT, which means that ``ssh_interact`` will only receive output when
sh encounters a newline in the output.  This is a problem because the password
prompt has no newline::

	amoffat@10.10.10.100's password:
	
Because a newline is never encountered, nothing is sent to ``ssh_interact``.
So we need to change
the STDOUT buffering.  We do this with the ``_out_bufsize``
:ref:`special keyword argument <special_arguments>`.  We'll set it to 0 for
unbuffered output, so we'll receive each character as the process writes it
(also see :ref:`buffer_sizes`)::

	from sh import ssh
	
	def ssh_interact(line, stdin):
	    line = line.strip()
	    print(line)
	    if line.endswith("password:"):
	        stdin.put("correcthorsebatterystaple")
		
	p = ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0)
	p.wait()

If you run this updated version, you'll notice a new problem.  The output looks
like this::

	'a'
	'm'
	'o'
	'f'
	'f'
	'a'
	't'
	'@'
	'1'
	'0'
	'.'
	'1'
	'0'
	'.'
	'1'
	'0'
	'.'
	'1'
	'0'
	'0'
	"'"
	's'
	' '
	'p'
	'a'
	's'
	's'
	'w'
	'o'
	'r'
	'd'
	':'
	' '
	
This is because the chunks of STDOUT our callback is receiving are unbuffered,
and are therefore individual characters, instead of entire lines.  What we need
to do now is aggregate this character-by-character data into something more
meaningful for us to test if the pattern ``password:`` has been sent, signifying
that SSH is ready for input.
It would make sense to encapsulate the
variable we'll use for aggregating into some kind of closure or class, but to keep it simple,
we'll just use a global::

	from sh import ssh
	import os, sys
	
	# open stdout in unbuffered mode
	sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
	
	aggregated = ""
	def ssh_interact(char, stdin):
	    global aggregated
	    sys.stdout.write(char.encode())
	    aggregated += char
	    if aggregated.endswith("password: "):
	        stdin.put("correcthorsebatterystaple")
		
	p = ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0)
	p.wait()
	
Also notice that we open ``sys.stdout`` in unbuffered mode by re-opening it
with ``os.fdopen``.
This allows us to use ``sys.stdout.write`` to print each character as we
receive it, without adding a newline, and without us needing to ``.flush()`` it.

You'll also notice that the example still doesn't work.  There are two problems:
The first is that your password must end with a newline, as if you had typed
it and hit the return key.  This is because SSH has no idea how long your
password is, and is line-buffering STDIN.  The second problem lies
deeper in SSH.  Long story short, SSH needs a :ref:`TTY <ttys>` attached
to its STDIN in order to work properly.  This "tricks" SSH into believing that
it is interacting with a real user in a real terminal session.
To enable TTY, we can add the ``_tty_in`` :ref:`special keyword argument <special_arguments>`::

	from sh import ssh
	import os, sys
	
	# open stdout in unbuffered mode
	sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
	
	aggregated = ""
	def ssh_interact(char, stdin):
	    global aggregated
	    sys.stdout.write(char.encode())
	    aggregated += char
	    if aggregated.endswith("password: "):
	        stdin.put("correcthorsebatterystaple\n")
		
	p = ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0, _tty_in=True)
	p.wait()
	
Voilà our remote login script works!::

	amoffat@10.10.10.100's password: 
	Linux 10.10.10.100 testhost #1 SMP Tue Jun 21 10:29:24 EDT 2011 i686 GNU/Linux
	Ubuntu 10.04.2 LTS
	
	Welcome to Ubuntu!
	 * Documentation:  https://help.ubuntu.com/
	
	66 packages can be updated.
	53 updates are security updates.
	
	Ubuntu 10.04.2 LTS
	
	Welcome to Ubuntu!
	 * Documentation:  https://help.ubuntu.com/
	You have new mail.
	Last login: Thu Sep 13 03:53:00 2012 from some.ip.address
	amoffat@10.10.10.100:~$ 
	
	
How you should REALLY be using SSH
----------------------------------

Many people want to learn how to enter an SSH password by script because they
want to execute remote commands on a server.  Instead of trying to log in
through SSH and then sending terminal input of the command to run, let's see
how we can do it another way.

First, open a terminal and run ``ssh-copy-id yourservername``.  You'll be asked
to enter your password for the server.  After entering your password, you'll
be able to SSH into the server without needing a password again.  This
simplifies things greatly for sh.

The second thing we want to do is use SSH's ability to pass a command to run
to the server you're SSHing to.  Here's how you can run ``ifconfig`` on a server
without having to use that server's shell::

	ssh amoffat@10.10.10.100 ifconfig 
	
Translating this to sh, it becomes::

	import sh
	
	print(sh.ssh("amoffat@10.10.10.100", "ifconfig"))
	
However there is more room for improvement.  We can take advantage of sh's
:ref:`baking` to bind our server username/ip to a command object::

	import sh
	
	my_server = sh.ssh.bake("amoffat@10.10.10.100")
	print(my_server("ifconfig"))
	print(my_server("whoami"))
	
Now we have a reusable command object that we can use to call remote commands.
But there is room for one more improvement.  We can also use sh's
:ref:`subcommands` feature which expands attribute access into command
arguments::

	import sh
	
	my_server = sh.ssh.bake("amoffat@10.10.10.100")
	print(my_server.ifconfig())
	print(my_server.whoami())
	
The above example is the same as passing in the arguments explicitly, but it
looks syntactically cleaner.
	
	
.. include:: /learn_more.rst
	
