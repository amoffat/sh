.. _piping:

Piping
======

Basic
-----

Bash style piping is performed using function composition.  Just pass one
command as the input to another's ``_in`` argument, and sh will send the output of
the inner command to the input of the outer command:

.. code-block:: python

	# sort this directory by biggest file
	print(sort("-rn", _in=du(glob("*"), "-sb")))
	
	# print(the number of folders and files in /etc
	print(wc("-l", _in=ls("/etc", "-1")))

.. note::

    This basic piping does not flow data through asynchronously; the inner
    command blocks until it finishes, before sending its data to the outer
    command.
	
By default, any command that is piping another command in waits for it to
complete.  This behavior can be changed with the :ref:`_piped <piped>` special
kwarg on the command being piped, which tells it not to complete before sending
its data, but to send its data incrementally.  Read ahead for examples of this.

.. _advanced_piping:

Advanced
--------

By default, all piped commands execute sequentially.  What this means is that the
inner command executes first, then sends its data to the outer command:

.. code-block:: python

	print(wc("-l", _in=ls("/etc", "-1")))
	
In the above example, ``ls`` executes, gathers its output, then sends that output
to ``wc``.  This is fine for simple commands, but for commands where you need
parallelism, this isn't good enough.  Take the following example:

.. code-block:: python

	for line in tr(_in=tail("-f", "test.log"), "[:upper:]", "[:lower:]", _iter=True):
	    print(line)
	
**This won't work** because the ``tail -f`` command never finishes.  What you
need is for ``tail`` to send its output to ``tr`` as it receives it.  This is where
the :ref:`_piped <piped>` special kwarg comes in handy:

.. code-block:: python

	for line in tr(_in=tail("-f", "test.log", _piped=True), "[:upper:]", "[:lower:]", _iter=True):
	    print(line)
	    
This works by telling ``tail -f`` that it is being used in a pipeline, and that
it should send its output line-by-line to ``tr``.  By default, :ref:`piped` sends
STDOUT, but you can easily make it send STDERR instead by using ``_piped="err"``
