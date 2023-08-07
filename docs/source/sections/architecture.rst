.. _architecture:

Architecture Overview
#####################

Launch
======

When it comes time to launch a process

#. Open pipes and/or TTYs STDIN/OUT/ERR.
#. Open a pipe for communicating pre-exec exceptions from the child to the
   parent.
#. Open a pipe for child/parent launch synchronization.
#. :func:`os.fork` a child process.

From here, we have two concurrent processes running:

Child
-----

#. If :ref:`_bg=True <bg>` is set, we ignore :py:data:`signal.SIGHUP`.
#. If :ref:`_new_session=True <new_session>`, become a session leader with
   :func:`os.setsid`, else become a process group leader with
   :func:`os.setpgrp`.
#. Write our session id to the a pipe connected to the parent.  This is mainly
   to synchronize with our parent that our session/group logic has finished.
#. :func:`os.dup2` the file descriptors of our previously-setup TTYs/pipes to
   our STDIN/OUT/ERR file descriptors.
#. If we're a session leader and our STDIN is a TTY, via :ref:`_tty_in=True
   <tty_in>`, acquire a controlling
   terminal, thereby becoming the controlling process of the session.
#. Set our GID/UID if we've set a custom one via :ref:`_uid <uid>`.
#. Close all file descriptors greater than STDERR.
#. Call :func:`os.execv`.

Parent
------

#. Check for any exceptions via the exception pipe connected to the child.
#. Block and read our child's session id from a pipe connected to the child.
   This synchronizes to us that the child has finished moving between
   sessions/groups and we can now accurately determine its current session id
   and process group.
#. If we're using a TTY for STDIN, via :ref:`_tty_in=True <tty_in>`, disable
   echoing on the TTY, so that data sent to STDIN is not echoed to STDOUT.

Running
=======

An instance of :ref:`oproc_class` contains two internal threads, one for STDIN,
and one for STDOUT and STDERR.  The purpose of these threads is to handle
reading/writing to the read/write ends of the process's standard descriptors.

For example, the STDOUT/ERR thread continually runs :func:`select.select` on the
master ends of the TTYs/pipes connected to STDOUT/ERR, and if they're ready to
read, reads the available data and aggregates it into the appropriate place.

.. _arch_buffers:

Buffers
-------

A couple of different buffers must be considered when thinking about how data
flows through an sh process.

The first buffer is the buffer associated with the underlying pipe or TTY
attached to STDOUT/ERR.  In the case of a TTY (the default for output), the
buffer size is 0, so output is immediate -- a byte written by the process is a
byte received by sh.  For a pipe, however, the buffer size of the pipe is
typically 4-64kb.  :manpage:`pipe(2)`.

.. seealso:: FAQ: :ref:`faq_tty_out`

The second buffer is sh's internal buffers, one for STDOUT and one for STDERR.
These buffers aggregate data that has been read from the master end of the TTY
or pipe attached to the output fd, but before that data is sent along to the
appropriate output handler (queue, file object, function, etc).  Data sits in
these buffers until we reach the size specified with :ref:`internal_bufsize`, at
which point the buffer flushes to the output handler.


Exit
====

STDIN Thread Shutdown
---------------------

On process completion, our internal threads must complete, as the read end of
STDIN, for example, which is connected to the process, is no longer open, so
writing to the slave end will no longer work.

STDOUT/ERR Thread Shutdown
--------------------------

The STDOUT/ERR thread is a little more complicated, because although the process
is not alive, output data may still exist in the pipe/TTY buffer that must be
collected.  So we essentially just :func:`select.select` on the read ends until
they return nothing, indicating that they are complete, then we break out of our
read loop.

.. _arch_exit_code:

Exit Code Processing
--------------------

The exit code is obtained from the reaped process.  If the process ended from a
signal, the exit code is the negative value of that signal.  For example,
SIGKILL would result in an exit code -9.

Done Callback
-------------

If specified, the :ref:`done` callback is executed with the :ref:`RunningCommand
<running_command>` instance, a boolean indicating success, and the adjusted exit
code.  After the callback returns, error processing continues.  In other words,
the done callback is called regardless of success or failure, and there's
nothing it can do to prevent the :ref:`ErrorReturnCode <error_return_code>`
exceptions from being raised after it completes.

