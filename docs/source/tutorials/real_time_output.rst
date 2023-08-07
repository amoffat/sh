.. _tutorial1:

Tailing a real-time log file
============================

sh has the ability to respond to subprocesses in an event-driven fashion.
A typical example of where this would be useful is tailing a log file for
a specific pattern, then responding to that value immediately::

	from sh import tail
	
	for line in tail("-f", "info.log", _iter=True):
	    if "ERROR" in line:
	        send_an_email_to_support(line)
			
			
The :ref:`_iter <iter>` special kwarg takes a command that would normally block
until completion, and turns its output into a real-time iterable.

.. seealso:: :ref:`iterable`

Of course, you can do more than just tail log files.  Any program that
produces output can be iterated over.  Say you wanted to send an email to a
coworker if their C code emits a warning:

.. code-block:: python

	from sh import gcc, git
	
	for line in gcc("-o", "awesome_binary", "awesome_source.c", _iter=True):
	    if "warning" in line:
	        # parse out the relevant info
	        filename, line, char, message = line.split(":", 3)
	        
	        # find the commit using git
	        commit = git("blame", "-e", filename, L="%d,%d" % (line,line))
	        
	        # send them an email
	        email_address = parse_email_from_commit_line(commit)
	        send_email(email_address, message)

Using :ref:`_iter <iter>` is a great way to respond to events from another
program, but your blocks while you're looping, making you unable to do anything
else.  To be truly event-driven, sh provides callbacks:

.. code-block:: python

	from sh import tail
	
	def process_log_line(line):
	    if "ERROR" in line:
	        send_an_email_to_support(line)
	
	process = tail("-f", "info.log", _out=process_log_line, _bg=True)
	
	# ... do other stuff here ...
	
	process.wait()
	
The :ref:`_out <out>` special kwarg lets you to assign a callback to STDOUT.
This callback will receive each line of output from ``tail -f`` and allow you to
do the same processing that we did earlier.

.. seealso:: :ref:`callbacks`

.. seealso:: :ref:`redirection`
