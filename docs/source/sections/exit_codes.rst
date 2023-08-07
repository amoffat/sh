.. _exit_codes:

Exit Codes & Exceptions
=======================

Normal processes exit with exit code 0.  This can be seen through a
:attr:`RunningCommand.exit_code`:

.. code-block:: python

	output = ls("/")
	print(output.exit_code) # should be 0
	
If a process terminates, and the exit code is not 0, an exception is generated
dynamically.  This lets you catch a specific return code, or catch all error
return codes through the base class :class:`ErrorReturnCode`:

.. code-block:: python

    try:
        print(ls("/some/non-existant/folder"))
    except ErrorReturnCode_2:
        print("folder doesn't exist!")
        create_the_folder()
    except ErrorReturnCode:
        print("unknown error")

You can also customize which exit codes indicate an error with :ref:`ok_code`. For example:

.. code-block:: python

   for i in range(10):
    	sh.grep("string to check", f"file_{i}.txt", _ok_code=(0, 1))

where the :ref:`ok_code` makes a failure to find a match a no-op.

Signals
-------

Signals are raised whenever your process terminates from a signal.  The
exception raised in this situation is :ref:`signal_exc`, which subclasses
:ref:`error_return_code`.

.. code-block:: python

    try:
        p = sh.sleep(3, _bg=True)
        p.kill()
    except sh.SignalException_SIGKILL:
        print("killed")

.. note::

    You can catch :ref:`signal_exc` by using either a number or a signal name.
    For example, the following two exception classes are equivalent:

    .. code-block:: python

        assert sh.SignalException_SIGKILL == sh.SignalException_9
