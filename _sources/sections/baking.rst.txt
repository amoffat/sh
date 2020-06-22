.. _baking:

Baking
======

sh is capable of "baking" arguments into commands.  This is essentially
`partial application <https://en.wikipedia.org/wiki/Partial_application>`_,
like you might do with :func:`functools.partial`.

.. code-block:: python

	from sh import ls
	
	ls = ls.bake("-la")
	print(ls) # "/usr/bin/ls -la"
	
	# resolves to "ls -la /"
	print(ls("/"))

The idea here is that now every call to ``ls`` will have the "-la" arguments
already specified.  Baking can become very useful when you combine it with
:ref:`subcommands`:

.. code-block:: python

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
can call anything on the server easily:

.. code-block:: python
	
	# executes "/usr/bin/ssh myserver.com -p 1393 tail /var/log/dumb_daemon.log -n 100"
	print(myserver.tail("/var/log/dumb_daemon.log", n=100))
	
