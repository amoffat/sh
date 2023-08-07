API
###


.. _command_class:

Command Class
==============

The ``Command`` class represents a program that exists on the system and can be
run at some point in time.  An instance of ``Command`` is never running; an
instance of :ref:`RunningCommand <running_command>` is spawned for that.

An instance of ``Command`` can take the form of a manually instantiated object,
or as an object instantiated by dynamic lookup:

.. code-block:: python

    import sh

    ls1 = sh.Command("ls")
    ls2 = sh.ls
    
    assert ls1 == ls2


.. py:class:: Command(name, search_paths=None)

    Instantiates a Command instance, where *name* is the name of a program that
    exists on the user's ``$PATH``, or is a full path itself.  If *search_paths*
    is specified, it must be a list of all the paths to look for the program
    name.

    .. code-block:: python

        from sh import Command

        ifconfig = Command("ifconfig")
        ifconfig = Command("/sbin/ifconfig")


.. py:method:: Command.bake(*args, **kwargs)

    Returns a new Command with ``*args`` and ``**kwargs`` baked in as
    positional and keyword arguments, respectively.  Any future calls to the
    returned Command will include ``*args`` and ``**kwargs`` automatically:

    .. code-block:: python

        from sh import ls

        long_ls = ls.bake("-l")
        print(ls("/var"))
        print(ls("/tmp"))
        
    
    .. seealso::

        :ref:`baking`


Similar to the above, arguments to the ``sh.Command`` must be separate.
e.g. the following does not work::

		lscmd = sh.Command("/bin/ls -l")
		tarcmd = sh.Command("/bin/tar cvf /tmp/test.tar /my/home/directory/")

You will run into ``CommandNotFound(path)`` exception even when correct full path is specified.
The correct way to do this is to :

#. build ``Command`` object using *only* the binary
#. pass the arguments to the object *when invoking*

as follows::

		lscmd = sh.Command("/bin/ls")
		lscmd("-l")
		tarcmd = sh.Command("/bin/tar")
		tarcmd("cvf", "/tmp/test.tar", "/my/home/directory/")

.. _running_command:

RunningCommand Class
====================

This represents a :ref:`Command <command_class>` instance that has been
or is being executed.  It exists as a wrapper around the low-level :ref:`OProc
<oproc_class>`.  Most of your interaction with sh objects are with instances of
this class. It is only returned if ``_return_cmd=True`` when you execute a command.

.. warning::

    Objects of this class behave very much like strings.  This was an
    intentional design decision to make the "output" of an executing Command
    behave more intuitively.

    Be aware that functions that accept real strings only, for example
    ``json.dumps``, will not work on instances of RunningCommand, even though it
    look like a string.

.. _wait_method:

.. py:method:: RunningCommand.wait(timeout=None)

    :param timeout: An optional non-negative number to wait for the command to complete. If it doesn't complete by the
        timeout, we raise :ref:`timeout_exc`.

    Block and wait for the command to finish execution and obtain an exit code.
    If the exit code represents a failure, we raise the appropriate exception.
    See :ref:`exceptions <exceptions>`.

    .. note::
        
        Calling this method multiple times only yields an exception on the first
        call.

    This is called automatically by sh unless your command is being executed
    :ref:`asynchronously <async>`, in which case, you may want to call this
    manually to ensure completion.

    If an instance of :ref:`Command <command_class>` is being used as the stdin
    argument (see :ref:`piping <piping>`), :meth:`wait` is also called on that
    instance, and any exceptions resulting from that process are propagated up.

.. py:attribute:: RunningCommand.process

    The underlying :ref:`OProc <oproc_class>` instance.

.. py:attribute:: RunningCommand.stdout

    A ``@property`` that calls :meth:`wait` and then returns the contents of
    what the process wrote to stdout.

.. py:attribute:: RunningCommand.stderr

    A ``@property`` that calls :meth:`wait` and then returns the contents of
    what the process wrote to stderr.

.. py:attribute:: RunningCommand.exit_code

    A ``@property`` that calls :meth:`wait` and then returns the process's exit
    code.

.. py:attribute:: RunningCommand.pid

    The process id of the process.

.. py:attribute:: RunningCommand.sid

    The session id of the process.  This will typically be a different session
    than the current python process, unless :ref:`_new_session=False
    <new_session>` was specified.

.. py:attribute:: RunningCommand.pgid

    The process group id of the process.

.. py:attribute:: RunningCommand.ctty

    The controlling terminal device, if there is one.

.. py:method:: RunningCommand.signal(sig_num)

    Sends *sig_num* to the process.  Typically used with a value from the
    :mod:`signal` module, like :py:data:`signal.SIGHUP` (see :manpage:`signal(7)`).

.. py:method:: RunningCommand.signal_group(sig_num)

    Sends *sig_num* to every process in the process group.  Typically used with
    a value from the :mod:`signal` module, like :py:data:`signal.SIGHUP` (see
    :manpage:`signal(7)`).

.. py:method:: RunningCommand.terminate()

    Shortcut for :meth:`RunningCommand.signal(signal.SIGTERM)
    <RunningCommand.signal>`.

.. py:method:: RunningCommand.kill()

    Shortcut for :meth:`RunningCommand.signal(signal.SIGKILL)
    <RunningCommand.signal>`.

.. py:method:: RunningCommand.kill_group()

    Shortcut for :meth:`RunningCommand.signal_group(signal.SIGKILL)
    <RunningCommand.signal_group>`.

.. py:method:: RunningCommand.is_alive()

    Returns whether or not the process is still alive.

    :rtype: bool

.. _oproc_class:

OProc Class
===========

.. warning::

    Don't use instances of this class directly.  It is being documented here for
    posterity, not for direct use.

.. py:method:: OProc.wait()

    Block until the process completes, aggregate the output, and populate
    :attr:`OProc.exit_code`.

.. py:attribute:: OProc.stdout

    A :class:`collections.deque`, sized to :ref:`_internal_bufsize
    <internal_bufsize>` items, that contains the process's STDOUT.

.. py:attribute:: OProc.stderr

    A :class:`collections.deque`, sized to :ref:`_internal_bufsize
    <internal_bufsize>` items, that contains the process's STDERR.

.. py:attribute:: OProc.exit_code

    Contains the process's exit code, or ``None`` if the process has not yet
    exited.

.. py:attribute:: OProc.pid

    The process id of the process.

.. py:attribute:: OProc.sid

    The session id of the process.  This will typically be a different session
    than the current python process, unless :ref:`_new_session=False
    <new_session>` was specified.

.. py:attribute:: OProc.pgid

    The process group id of the process.

.. py:attribute:: OProc.ctty

    The controlling terminal device, if there is one.

.. py:method:: OProc.signal(sig_num)

    Sends *sig_num* to the process.  Typically used with a value from the
    :mod:`signal` module, like :py:data:`signal.SIGHUP` (see :manpage:`signal(7)`).

.. py:method:: OProc.signal_group(sig_num)

    Sends *sig_num* to every process in the process group.  Typically used with
    a value from the :mod:`signal` module, like :py:data:`signal.SIGHUP` (see
    :manpage:`signal(7)`).

.. py:method:: OProc.terminate()

    Shortcut for :meth:`OProc.signal(signal.SIGTERM) <OProc.signal>`.

.. py:method:: OProc.kill()

    Shortcut for :meth:`OProc.signal(signal.SIGKILL) <OProc.signal>`.

.. py:method:: OProc.kill_group()

    Shortcut for :meth:`OProc.signal_group(signal.SIGKILL)
    <OProc.signal_group>`.

Exceptions
==========

.. _error_return_code:

ErrorReturnCode
---------------

.. py:class:: ErrorReturnCode

    This is the base class for, as the name suggests, error return codes.  It
    subclasses :py:class:`Exception`.

.. py:attribute:: ErrorReturnCode.full_cmd

    The full command that was executed, as a string, so that you can try it on
    the commandline if you wish.

.. py:attribute:: ErrorReturnCode.stdout

    The total aggregated STDOUT for the process.

.. py:attribute:: ErrorReturnCode.stderr

    The total aggregated STDERR for the process.

.. py:attribute:: ErrorReturnCode.exit_code

    The process's adjusted exit code.

    .. seealso:: :ref:`arch_exit_code`


.. _signal_exc:

SignalException
---------------

Subclasses :ref:`ErrorReturnCode <error_return_code>`.  Raised when a command
receives a signal that causes it to exit.

.. _timeout_exc:

TimeoutException
----------------

Raised when a command specifies a non-null :ref:`timeout` and the command times out:

.. code-block:: python

    import sh

    try:
        sh.sleep(10, _timeout=1)
    except sh.TimeoutException:
        print("we timed out, as expected")

Also raised when you specify a timeout to :ref:`RunningCommand.wait(timeout=None)<wait_method>`:

.. code-block:: python

    import sh

    p = sh.sleep(10, _bg=True)
    try:
        p.wait(timeout=1)
    except sh.TimeoutException:
        print("we timed out waiting")
        p.kill()

.. _not_found_exc:

CommandNotFound
---------------

This exception is raised in one of the following conditions:

* The program cannot be found on your path.
* You do not have permissions to execute the program.
* The program is not marked executable.

The last two bullets may seem strange, but they fall in line with how a shell like Bash behaves when looking up a
program to execute.

.. note::

    ``CommandNotFound`` subclasses ``AttributeError``. As such, the `repr` of it is simply the name of the missing
    attribute.


Helper Functions
================

.. py:function:: which(name, search_paths=None)

    Resolves *name* to program's absolute path, or ``None`` if it cannot be
    found.  If *search_paths* is list of paths, use that list to look for the
    program, otherwise use the environment variable ``$PATH``.

.. py:function:: pushd(directory)

    This function provides a ``with`` context that behaves similar to Bash's
    `pushd
    <https://www.gnu.org/software/bash/manual/html_node/Directory-Stack-Builtins.html>`_
    by pushing to the provided directory, and popping out of it at the end of
    the context.

    .. code-block:: python
        
        import sh

        with sh.pushd("/tmp"):
            sh.touch("a_file")

    .. note::

        It should be noted that we use a reentrant lock, so that different threads
        using this function will have the correct behavior inside of their ``with``
        contexts.
