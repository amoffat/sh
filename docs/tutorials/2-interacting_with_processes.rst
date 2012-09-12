Tutorial 2: Interacting with processes
======================================

Many programs require some form of input.  This input can be in the form of
commandline arguments or STDIN.  Some programs require this input at their
launch, others require it during the lifetime of the process.  Let's start
with the former::

	from sh import sed
	
	data = "one two three"
	fixed = sed(e="s/you're code/your code/", _in=data)
	
``sed`` is a program that can take input in the form of a file or piped from
STDIN.  Here, we choose to use STDIN by using the ``_in``
:ref:`special keyword argument <special_arguments>`.