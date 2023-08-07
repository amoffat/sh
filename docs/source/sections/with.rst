.. _with_contexts:

'With' Contexts
===============

Commands can be run within a Python ``with`` context.  Popular commands using
this might be ``sudo`` or ``fakeroot``:

.. code-block:: python

	with sh.contrib.sudo:
	    print(ls("/root"))

.. seealso::

    :ref:`contrib_sudo`
		
If you need to run a command in a with context and pass in arguments, for
example, specifying a -p prompt with sudo, you need to use the :ref:`_with=True
<with>` This let's the command know that it's being run from a with context so
it can behave correctly:

.. code-block:: python

	with sh.contrib.sudo(k=True, _with=True):
	    print(ls("/root"))
	    

