.. _special_arguments:

Special keyword arguments
=========================

These arguments alter the way a command is launched or run.  They apply to
every command, but some may not be used together.

.. glossary::

	_bg
		Runs a command in the background.  The command will return immediately,
		and you will have to run ``.wait()`` on it to allow
		it to finish.  See :ref:`background`.

	_with
		Explicitly tells us that we're running a command in a ``with`` context.
		This is only necessary if you're using a command in a ``with`` context
		**and** passing parameters to it.  See :ref:`with_contexts`.
		
	_in
		Specifies an argument for the process to use as its standard input.  This
		may be a string, a `Queue <http://docs.python.org/library/queue.html#queue-objects>`_,
		a file object, or any iterable.  See :ref:`stdin`.
		
	_out
		What to redirect STDOUT to.  If this is a string, it will be treated as
		a file name.  You may also pass a file object (or file-like object), as
		well as a StringIO object.  See :ref:`redirection`.
		
	_err
		What to redirect STDERR to.  See ``_out`` above.
		
	_err_to_out
		If True, this redirects the STDERR stream to the STDOUT stream, so that
		any returned data from a command will be both from STDOUT and STDERR.
		
	_env
		A dictionary defining the only environment variables that will be made
		accessible to the process.  If not specified, the calling process's
		environment variables are used.  See :ref:`environments`.
		
	_piped
		May be ``True``, ``"out"``, or ``"err"``.
		Signals a command that it is being used as the input to another
		command, so it should return its output incrementally as it receives it,
		instead of aggregating it all at once.  See :ref:`advanced_piping`.
		
	_iter
		May be ``True``, ``"out"``, or ``"err"``.
		Puts a command in iterable mode.  In this mode, you can use a
		``for`` or ``while`` loop to iterate over a command's output in
		real-time.  See :ref:`iterable`.
		
	_iter_noblock
		Same as ``_iter``, except the loop will not block if there is no output
		to iterate over.  Instead, the output from the command will be 
		``errno.EWOULDBLOCK``.  See :ref:`iterable`.
		
	_ok_code
		Either an integer, a list, or a tuple containing the exit code(s)
		that are considered "ok", or in other words: do not raise an exception.
		See :ref:`exit_codes`.
		
	_cwd
		A string that sets the current working directory of the process.
		
	_tty_in
		If ``True``, sh creates a `TTY <http://en.wikipedia.org/wiki/Pseudo_terminal#Applications>`_
		for STDIN, otherwise use a `pipe <http://docs.python.org/library/os.html#os.pipe>`_.
		This is necessary for commands that require STDIN to be a TTY.
		By default, STDIN is a `pipe <http://docs.python.org/library/os.html#os.pipe>`_.
		
	_tty_out
		If ``True``, sh creates a `TTY <http://en.wikipedia.org/wiki/Pseudo_terminal#Applications>`_
		for STDOUT, otherwise use a `pipe <http://docs.python.org/library/os.html#os.pipe>`_.
		This is necessary for commands that require STDOUT to be a TTY.
		By default, STDOUT and STDERR are TTYs.
		
	_in_bufsize
		The STDIN buffer size.  0 for unbuffered (the default), 1 for line
		buffered, anything else for a buffer of that amount.  See :ref:`buffer_sizes`
		
	_out_bufsize
		The STDOUT/ERR buffer size.  0 for unbuffered, 1 for line
		buffered (the default), anything else for a buffer of that amount.
		See :ref:`buffer_sizes`
		
	_internal_bufsize
		How much of STDOUT/ERR your command will store internally.  This value
		represents the *number of bufsize chunks* not the total number of bytes.
		For example, if this value is 100, and STDOUT is line buffered, you will
		be able to retrieve 100 lines from STDOUT.  If STDOUT is unbuffered, you
		will be able to retrieve only 100 characters.
		
	_timeout
		How much time, in seconds, we should give the process to complete.  If the
		process does not finish within the timeout, it will be sent SIGKILL.
		
	_encoding
		The character encoding of the process's STDOUT.  By default, this is "utf8".
			
	_decode_errors
		.. versionadded:: 1.07
		This is how Python should handle decoding errors of the process's output.
		By default, this is "strict", but you can use any value that's valid
		to a string's ``.decode()`` method, such as "ignore".
		
	_no_out
		.. versionadded:: 1.07
		Disables STDOUT being internally stored.  This is useful for commands
		that produce huge amounts of output that you don't need, that would
		otherwise be hogging memory if stored internally by sh.
		
	_no_err
		.. versionadded:: 1.07
		Disables STDERR being internally stored.  This is useful for commands
		that produce huge amounts of output that you don't need, that would
		otherwise be hogging memory if stored internally by sh.
		
	_no_pipe
		.. versionadded:: 1.07
		Similar to ``_no_out``, this explicitly tells the sh command that it
		will never be used for piping its output into another command, so it
		should not fill its internal pipe buffer with the process's output.
		This is also useful for conserving memory.
		
	_tee
		.. versionadded:: 1.07
		As of 1.07, any time redirection is used, either for stdout or stderr,
		the respective internal buffers are not filled.  For example, if you're
		downloading a file and using a callback on stdout, the internal stdout
		buffer, nor the pipe buffer be filled with data from stdout.  This
		option forces those buffers to be filled anyways, in effect "tee-ing"
		the output into two places (the callback/redirect handler, and the
		internal buffers).
