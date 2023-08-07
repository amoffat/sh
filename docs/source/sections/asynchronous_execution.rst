.. _async:

Asynchronous Execution
######################

sh provides a few methods for running commands and obtaining output in a
non-blocking fashion.

AsyncIO
=======

.. versionadded:: 2.0.0

Sh supports asyncio on commands with the :ref:`_async=True <async_kw>` special
kwarg. This let's you incrementally ``await`` output produced from your command.

.. code-block:: python

	import asyncio
	import sh

	async def main():
	    await sh.sleep(3, _async=True)

	asyncio.run(main())

.. _iterable:
	    
Incremental Iteration
=====================

You may also create asynchronous commands by iterating over them with the
:ref:`iter` special kwarg.  This creates an iterable (specifically, a generator)
that you can loop over:

.. code-block:: python

	from sh import tail

	# runs forever
	for line in tail("-f", "/var/log/some_log_file.log", _iter=True):
	    print(line)
	    
By default, :ref:`iter` iterates over STDOUT, but you can change set this
specifically by passing either ``"err"`` or ``"out"`` to :ref:`iter` (instead of
``True``).  Also by default, output is line-buffered, so the body of the loop
will only run when your process produces a newline.  You can change this by
changing the buffer size of the command's output with :ref:`out_bufsize`.

.. note::

    If you need a *fully* non-blocking iterator, use :ref:`iter_noblock`.  If
    the current iteration would block, :py:data:`errno.EWOULDBLOCK` will be
    returned, otherwise you'll receive a chunk of output, as normal.

.. _background:
	
Background Processes
====================

By default, each running command blocks until completion.  If you have a
long-running command, you can put it in the background with the :ref:`_bg=True
<bg>` special kwarg:

.. code-block:: python

	# blocks
	sleep(3)
	print("...3 seconds later")
	
	# doesn't block
	p = sleep(3, _bg=True)
	print("prints immediately!")
	p.wait()
	print("...and 3 seconds later")

You'll notice that you need to call :meth:`RunningCommand.wait` in order to exit
after your command exits.

Commands launched in the background ignore ``SIGHUP``, meaning that when their
controlling process (the session leader, if there is a controlling terminal)
exits, they will not be signalled by the kernel.  But because sh commands launch
their processes in their own sessions by default, meaning they are their own
session leaders, ignoring ``SIGHUP`` will normally have no impact.  So the only
time ignoring ``SIGHUP`` will do anything is if you use :ref:`_new_session=False
<new_session>`, in which case the controlling process will probably be the shell
from which you launched python, and exiting that shell would normally send a
``SIGHUP`` to all child processes.

.. seealso::

    For more information on the exact launch process, see :ref:`architecture`.

.. _callbacks:

Output Callbacks
----------------
	    
In combination with :ref:`_bg=True<bg>`, sh can use callbacks to process output
incrementally by passing a callable function to :ref:`out` and/or :ref:`err`.
This callable will be called for each line (or chunk) of data that your command
outputs:

.. code-block:: python

	from sh import tail
	
	def process_output(line):
	    print(line)
	
	p = tail("-f", "/var/log/some_log_file.log", _out=process_output, _bg=True)
    p.wait()

To control whether the callback receives a line or a chunk, use
:ref:`out_bufsize`.  To "quit" your callback, simply return ``True``.  This
tells the command not to call your callback anymore.

The line or chunk received by the callback can either be of type ``str`` or
``bytes``. If the output could be decoded using the provided encoding, a
``str`` will be passed to the callback, otherwise it would be raw ``bytes``.

.. note::

    Returning ``True`` does not kill the process, it only keeps the callback
    from being called again.  See :ref:`interactive_callbacks` for how to kill a
    process from a callback.
	
.. seealso:: :ref:`red_func`

.. _interactive_callbacks:
	    
Interactive callbacks
---------------------

Commands may communicate with the underlying process interactively through a
specific callback signature
Each command launched through sh has an internal STDIN :class:`queue.Queue`
that can be used from callbacks:

.. code-block:: python

	def interact(line, stdin):
	    if line == "What... is the air-speed velocity of an unladen swallow?":
	        stdin.put("What do you mean? An African or European swallow?")
			
	    elif line == "Huh? I... I don't know that....AAAAGHHHHHH":
	        cross_bridge()
	        return True
			
	    else:
	        stdin.put("I don't know....AAGGHHHHH")
	        return True
			
	p = sh.bridgekeeper(_out=interact, _bg=True)
    p.wait()

.. note::

    If you use a queue, you can signal the end of the input (EOF) with ``None``

You can also kill or terminate your process (or send any signal, really) from
your callback by adding a third argument to receive the process object:

.. code-block:: python

	def process_output(line, stdin, process):
	    print(line)
	    if "ERROR" in line:
	        process.kill()
	        return True
	
	p = tail("-f", "/var/log/some_log_file.log", _out=process_output, _bg=True)
	
The above code will run, printing lines from ``some_log_file.log`` until the
word ``"ERROR"`` appears in a line, at which point the tail process will be
killed and the script will end.

.. note::

    You may also use :meth:`RunningCommand.terminate` to send a SIGTERM, or
    :meth:`RunningCommand.signal` to send a general signal.


Done Callbacks
--------------

A done callback called when the process exits, either normally (through
a success or error exit code) or through a signal.  It is *always* called.

.. include:: /examples/done.rst
