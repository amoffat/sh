.. _subcommands:

Sub-commands
============

Many programs have their own command subsets, like git (branch, checkout),
svn (update, status), and sudo (where any command following sudo is considered
a sub-command).  sh handles subcommands through attribute access:

.. code-block:: python

	from sh import git, sudo
	
	# resolves to "git branch -v"
	print(git.branch("-v"))
	print(git("branch", "-v")) # the same command
	
	# resolves to "sudo /bin/ls /root"
	print(sudo.ls("/root"))
	print(sudo("/bin/ls", "/root")) # the same command
	
Sub-commands are mainly syntax sugar that makes calling some programs look conceptually nicer.

.. seealso::
    If you're using ``sudo`` as a subcommand, please be sure to see :ref:`sudo`.
