.. _special_arguments:

.. |def| replace:: Default value:

Special Kwargs
##############

These arguments alter a command's behavior.  They are not passed to the program.
You can use them on any command that you run, but some may not be used together.
sh will tell you if there are conflicts.

To set default special keyword arguments on *every* command run, you may use
:ref:`default_arguments`.

Controlling Output
==================

.. _out:

_out
----
|def| ``None``

What to redirect STDOUT to.  If this is a string, it will be treated as a file
name.  You may also pass a file object (or file-like object), an int
(representing a file descriptor, like the result of :func:`os.pipe`), a
:class:`io.StringIO` object, or a callable.

.. code-block:: python

    import sh
    sh.ls(_out="/tmp/output")

.. seealso::
    :ref:`redirection`
		
.. _err:

_err
----
|def| ``None``

What to redirect STDERR to.  See :ref:`_out<out>`.
    
_err_to_out
-----------
|def| ``False``

If ``True``, duplicate the file descriptor bound to the process's STDOUT also to
STDERR, effectively causing STDERR and STDOUT to go to the same place.

_encoding
---------
|def| ``sh.DEFAULT_ENCODING``

The character encoding of the process's STDOUT.  By default, this is the
locale's default encoding.
			
_decode_errors
--------------
.. versionadded:: 1.07.0

|def| ``"strict"``

This is how Python should handle decoding errors of the process's output.
By default, this is ``"strict"``, but you can use any value that's valid
to :meth:`bytes.decode`, such as ``"ignore"``.
		
_tee
----
.. versionadded:: 1.07.0

|def| ``None``

As of 1.07.0, any time redirection is used, either for STDOUT or STDERR, the
respective internal buffers are not filled.  For example, if you're downloading
a file and using a callback on STDOUT, the internal STDOUT buffer, nor the pipe
buffer be filled with data from STDOUT.  This option forces one of stderr
(``_tee='err'``) or stdout (``_tee='out'`` or ``_tee=True``) to be filled
anyways, in effect "tee-ing" the output into two places (the callback/redirect
handler, and the internal buffers).


_truncate_exc
-------------
.. versionadded:: 1.12.0

|def| ``True``

Whether or not exception ouput should be truncated.

Execution
=========

.. _fg:

_fg
---
.. versionadded:: 1.12.0

|def| ``False``

Runs a command in the foreground, meaning it is spawned using :func:`os.spawnle()`.  The current process's STDIN/OUT/ERR
is :func:`os.dup2`'d to the new process and so the new process becomes the *foreground* of the shell executing the
script.  This is only really useful when you want to launch a lean, interactive process that sh is having trouble
running, for example, ssh.

.. warning::

    ``_fg=True`` side-steps a lot of sh's functionality.  You will not be returned a process object and most (likely
    all) other special kwargs will not work.

If you are looking for similar functionality, but still retaining sh's features, use the following:

.. code-block:: python
        
    import sh
    import sys
    sh.your_command(_in=sys.stdin, _out=sys.stdout, _err=sys.stderr)


.. _bg:

_bg
---
|def| ``False``

Runs a command in the background.  The command will return immediately, and you
will have to run :meth:`RunningCommand.wait` on it to ensure it terminates.

.. seealso:: :ref:`background`.

.. _bg_exc:

_bg_exc
-------
.. versionadded:: 1.12.9

|def| ``True``

Automatically report exceptions for the background command. If you set this to
``False`` you should make sure to call :meth:`RunningCommand.wait` or you may
swallow exceptions that happen in the background command.

.. _async_kw:

_async
------
.. versionadded:: 2.0.0

|def| ``False``

Allows your command to become awaitable. Use in combination with :ref:`_iter <iter>`
and ``async for`` to incrementally await output as it is produced.

.. _env:

_env
----
|def| ``None``

A dictionary defining the only environment variables that will be made
accessible to the process.  If not specified, the calling process's environment
variables are used.

.. note::

    This dictionary is the authoritative environment for the process.  If you
    wish to change a single variable in your current environement, you must pass
    a copy of your current environment with the overriden variable to sh.

.. seealso:: :ref:`environments`

.. _timeout:

_timeout
--------
|def| ``None``

How much time, in seconds, we should give the process to complete.  If the
process does not finish within the timeout, it will be sent the signal defined
by :ref:`timeout_signal`.

.. _timeout_signal:

_timeout_signal
---------------
|def| ``signal.SIGKILL``

The signal to be sent to the process if :ref:`timeout` is not ``None``.

_cwd
----
|def| ``None``

A string that sets the current working directory of the process.

.. _ok_code:

_ok_code
--------
|def| ``0``

Either an integer, a list, or a tuple containing the exit code(s) that are
considered "ok", or in other words: do not raise an exception.  Some misbehaved
programs use exit codes other than 0 to indicate success.

.. code-block:: python

    import sh
    sh.weird_program(_ok_code=[0,3,5])

.. seealso:: :ref:`exit_codes`

.. _new_session:

_new_session
------------
|def| ``False``

Determines if our forked process will be executed in its own session via
:func:`os.setsid`.

.. versionchanged:: 2.0.0
    The default value of ``_new_session`` was changed from ``True`` to ``False``
    because it makes more sense for a launched process to default to being in
    the process group of python script, so that it receives SIGINTs correctly.

.. note::

    If ``_new_session`` is ``False``, the forked process will be put into its
    own group via ``os.setpgrp()``.  This way, the forked process, and all of
    it's children, are always alone in their own group that may be signalled
    directly, regardless of the value of ``_new_session``.

.. seealso:: :ref:`architecture`

.. _uid:

_uid
----
.. versionadded:: 1.12.0

|def| ``None``

The user id to assume before the child process calls :func:`os.execv`.

_preexec_fn
-----------
.. versionadded:: 1.12.0

|def| ``None``

A function to be run directly before the child process calls :func:`os.execv`.
Typically not used by normal users.

.. _pass_fds:

_pass_fds
---------
.. versionadded:: 1.13.0

|def| ``{}`` (empty set)

A whitelist iterable of integer file descriptors to be inherited by the child. Passing anything in this argument causes :ref:`_close_fds <close_fds>` to be ``True``.
		
.. _close_fds:

_close_fds
----------
.. versionadded:: 1.13.0

|def| ``True``

Causes all inherited file descriptors besides stdin, stdout, and stderr to be automatically closed. This option is
automatically enabled when :ref:`_pass_fds <pass_fds>` is given a value.

Communication
=============

.. _in:

_in
---

|def| ``None``

Specifies an argument for the process to use as its standard input.  This may be
a string, a :class:`queue.Queue`, a file-like object, or any iterable.

.. seealso:: :ref:`stdin`
		
.. _piped:

_piped
------

|def| ``None``

May be ``True``, ``"out"``, or ``"err"``.  Signals a command that it is being
used as the input to another command, so it should return its output
incrementally as it receives it, instead of aggregating it all at once.

.. seealso:: :ref:`Advanced Piping <advanced_piping>`

.. _iter:
		
_iter
-----

|def| ``None``

May be ``True``, ``"out"``, or ``"err"``.  Puts a command in iterable mode.  In
this mode, you can use a ``for`` or ``while`` loop to iterate over a command's
output in real-time.

.. code-block:: python

    import sh 
    for line in sh.cat("/tmp/file", _iter=True):
        print(line)

.. seealso:: :ref:`iterable`.

.. _iter_noblock:
		
_iter_noblock
-------------
|def| ``None``

Same as :ref:`_iter <iter>`, except the loop will not block if there is no
output to iterate over.  Instead, the output from the command will be
:py:data:`errno.EWOULDBLOCK`.

.. code-block:: python

    import sh
    import errno
    import time

    for line in sh.tail("-f", "stuff.log", _iter_noblock=True):
        if line == errno.EWOULDBLOCK:
            print("doing something else...")
            time.sleep(0.5)
        else:
            print("processing line!")


.. seealso:: :ref:`iterable`.

.. _with:

_with
-----
|def| ``False``

Explicitly tells us that we're running a command in a ``with`` context.  This is
only necessary if you're using a command in a ``with`` context **and** passing
parameters to it.

.. code-block:: python

    import sh
    with sh.contrib.sudo(password="abc123", _with=True):
        print(sh.ls("/root"))

.. seealso:: :ref:`with_contexts`

.. _done:

_done
-----
.. versionadded:: 1.11.0

|def| ``None``

A callback that is *always* called when the command completes, even if it
completes with an exit code that would raise an exception.  After the callback
is run, any exception that would be raised is raised.

The callback is passed the :ref:`RunningCommand <running_command>` instance, a
boolean indicating success, and the exit code.

.. include:: /examples/done.rst
		
TTYs
====

.. _tty_in:

_tty_in
-------

|def| ``False``, meaning a :func:`os.pipe` will be used.

If ``True``, sh creates a TTY for STDIN, essentially emulating a terminal, as if
your command was entered from the commandline.  This is necessary for commands
that require STDIN to be a TTY.

.. _tty_out:
    
_tty_out
--------

|def| ``True``

If ``True``, sh creates a TTY for STDOUT, otherwise use a :func:`os.pipe`. This
is necessary for commands that require STDOUT to be a TTY.

.. seealso:: :ref:`faq_tty_out`

.. _unify_ttys:

_unify_ttys
-----------
.. versionadded:: 1.13.0

|def| ``False``

If ``True``, sh will combine the STDOUT and STDIN TTY into a single
pseudo-terminal. This is sometimes required by picky programs which expect to be
dealing with a single pseudo-terminal, like SSH.

.. seealso:: :ref:`tutorial2`

_tty_size
---------

|def| ``(20, 80)``

The (rows, columns) of stdout's TTY.  Changing this may affect how much your
program prints per line, for example.

Performance & Optimization
==========================

_in_bufsize
-----------
|def| ``0``

The STDIN buffer size.  0 for unbuffered, 1 for line buffered, anything else for
a buffer of that amount.

.. _out_bufsize:
		
_out_bufsize
------------
|def| ``1``

The STDOUT buffer size.  0 for unbuffered, 1 for line buffered, anything
else for a buffer of that amount.

.. _err_bufsize:

_err_bufsize
------------
|def| ``1``

Same as :ref:`out_bufsize`, but with STDERR.

.. _internal_bufsize:
		
_internal_bufsize
-----------------
|def| ``3 * 1024**2`` chunks

How much of STDOUT/ERR your command will store internally.  This value
represents the *number of bufsize chunks* not the total number of bytes.  For
example, if this value is 100, and STDOUT is line buffered, you will be able to
retrieve 100 lines from STDOUT.  If STDOUT is unbuffered, you will be able to
retrieve only 100 characters.
		
_no_out
-------
.. versionadded:: 1.07.0

|def| ``False``

Disables STDOUT being internally stored.  This is useful for commands
that produce huge amounts of output that you don't need, that would
otherwise be hogging memory if stored internally by sh.
		
_no_err
-------
.. versionadded:: 1.07.0

|def| ``False``

Disables STDERR being internally stored.  This is useful for commands that
produce huge amounts of output that you don't need, that would otherwise be
hogging memory if stored internally by sh.
		
_no_pipe
--------
.. versionadded:: 1.07.0

|def| ``False``

Similar to ``_no_out``, this explicitly tells the sh command that it will never
be used for piping its output into another command, so it should not fill its
internal pipe buffer with the process's output.  This is also useful for
conserving memory.
		

Program Arguments
=================

These are options that affect how command options are fed into the program.

_long_sep
---------
.. versionadded:: 1.12.0

|def| ``"="``

This is the character(s) that separate a program's long argument's key from the
value, when using kwargs to specify your program's long arguments.  For example,
if your program expects a long argument in the form ``--name value``, the way to
achieve this would be to set ``_long_sep=" "``.

.. code-block:: python

    import sh
    sh.your_program(key=value, _long_sep=" ")

Would send the following list of arguments to your program:

.. code-block:: python

    ["--key value"]

If your program expects the long argument name to be separate from its value,
pass ``None`` into ``_long_sep`` instead:

.. code-block:: python

    import sh
    sh.your_program(key=value, _long_sep=None)

Would send the following list of arguments to your program:

.. code-block:: python

    ["--key", "value"]

_long_prefix
------------
.. versionadded:: 1.12.0

|def| ``"--"``

This is the character(s) that prefix a long argument for the program being run.
Some programs use single dashes, for example, and do not understand double
dashes.

.. _preprocess:

_arg_preprocess
---------------
.. versionadded:: 1.12.0

|def| ``None``

This is an advanced option that allows you to rewrite a command's arguments on
the fly, based on other command arguments, or some other variable.  It is really
only useful in conjunction with :ref:`baking <baking>`, and only currently used when
constructing :ref:`contrib <contrib>` wrappers.

Example:

.. code-block:: python

    import sh

    def processor(args, kwargs):
        return args, kwargs

    my_ls = sh.bake.ls(_arg_preprocess=processor)

.. warning::

    The interface to the ``_arg_preprocess`` function may change without
    warning.  It is generally only for internal sh use, so don't use it unless
    you absolutely have to.

Misc
====

_log_msg
--------

|def| ``None``

.. versionadded:: 1.12.0

This allows for a custom logging header for :ref:`command_class` instances.  For example, the default logging looks like this:

.. code-block:: python

    import logging
    import sh

    logging.basicConfig(level=logging.INFO)

    sh.ls("-l")

.. code-block:: none

    INFO:sh.command:<Command '/bin/ls -l'>: starting process
    INFO:sh.command:<Command '/bin/ls -l', pid 28952>: process started
    INFO:sh.command:<Command '/bin/ls -l', pid 28952>: process completed

People can find this ``<Command ..`` section long and not relevant. ``_log_msg`` allows you to customize this:

.. code-block:: python

    import logging
    import sh

    logging.basicConfig(level=logging.INFO)

    def custom_log(ran, call_args, pid=None):
        return ran

    sh.ls("-l", _log_msg=custom_log)

.. code-block:: none

    INFO:sh.command:/bin/ls -l: starting process
    INFO:sh.command:/bin/ls -l: process started
    INFO:sh.command:/bin/ls -l: process completed

The first argument, ``ran``, is the program's execution string and arguments, as close as we can get it to be how you'd
type in the shell.  ``call_args`` is a dictionary of all of the special kwargs that were passed to the command.  And ``pid``
is the process id of the forked process.  It defaults to ``None`` because the ``_log_msg`` callback is actually called
twice: first to construct the logger for the :ref:`running_command` instance, before the process itself is spawned, then
a second time after the process is spawned via :ref:`oproc_class`, when we have a pid.
