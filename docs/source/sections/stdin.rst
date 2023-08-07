.. _stdin:

Input via STDIN
===============

STDIN is sent to a process directly by using a command's :ref:`in` special
kwarg:

.. code-block:: python

	print(cat(_in="test"))
	
Any command that takes input from STDIN can be used this way:

.. code-block:: python

	print(tr("[:lower:]", "[:upper:]", _in="sh is awesome"))
	
You're also not limited to using just strings.  You may use a file object, a
:class:`queue.Queue`, or any iterable (list, set, dictionary, etc):

.. code-block:: python

	stdin = ["sh", "is", "awesome"]
	out = tr("[:lower:]", "[:upper:]", _in=stdin)

.. note::

    If you use a queue, you can signal the end of the queue (EOF) with ``None``
