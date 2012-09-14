.. _tutorial1:

Tutorial 1: Tailing a real-time log file
========================================

sh has the ability to respond to subprocesses in an event-driven fashion.
A typical example of where this would be useful is tailing a log file for
a specific pattern, then responding to that value immediately::

	from sh import tail
	
	for line in tail("-f", "info.log", _iter=True):
	    if "ERROR" in line:
	        send_an_email_to_support(line)
			
			
The ``_iter``  :ref:`special keyword argument <special_arguments>` takes a
command that would normally block until completion, and turns its output
into a real-time iterable.  See :ref:`iterable`.

Of course, you can do more than just tail log files.  Any program that
produces output can be iterated over.  Say you wanted to send an email to a
coworker if their C code emits a warning::

	from sh import gcc, git
	
	for line in gcc("-o", "awesome_binary", "awesome_source.c"):
	    if "warning" in line:
	        # parse out the relevant info
	        filename, line, char, message = line.split(":", 3)
	        
	        # find the commit using git
	        commit = git("blame", "-e", filename, L="%d,%d" % (line,line))
	        
	        # send them an email
	        email_address = parse_email_from_commit_line(commit)
	        send_email(email_address, message)

Using ``_iter`` is a great way to respond to events from another program, but 
your script can't do anything else while you're looping; the process must
end for the loop to finish, unless you explicitly ``break`` on some
condition.  You could try to put this loop in another thread, but sh provides
an easier method via callbacks::

	from sh import tail
	
	def process_log_line(line):
	    if "ERROR" in line:
	        send_an_email_to_support(line)
	
	process = tail("-f", "info.log", _out=process_log_line)
	
	# ... do other stuff here ...
	
	process.wait()
	
The ``_out`` :ref:`special keyword argument <special_arguments>` lets you
to assign a callback to STDOUT.  This callback will receive each line of
output from ``tail -f`` and allow you to do the same processing that we
did earlier.  See :ref:`callbacks`.

.. include:: /learn_more.rst