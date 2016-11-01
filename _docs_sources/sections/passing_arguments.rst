.. _passing_arguments:

Passing Arguments
=================

When passing multiple arguments to a command, each argument *must* be a separate
string:

.. code-block:: python

    from sh import tar
    tar("cvf", "/tmp/test.tar", "/my/home/directory/")

This *will not work*:

.. code-block:: python

    from sh import tar
    tar("cvf /tmp/test.tar /my/home/directory")
	
.. seealso:: :ref:`faq_separate_args`


Keyword Arguments
-----------------

sh supports short-form ``-a`` and long-form ``--arg`` arguments as
keyword arguments:

.. code-block:: python

	# resolves to "curl http://duckduckgo.com/ -o page.html --silent"
	curl("http://duckduckgo.com/", o="page.html", silent=True)
	
	# or if you prefer not to use keyword arguments, this does the same thing:
	curl("http://duckduckgo.com/", "-o", "page.html", "--silent")
	
	# resolves to "adduser amoffat --system --shell=/bin/bash --no-create-home"
	adduser("amoffat", system=True, shell="/bin/bash", no_create_home=True)
	
	# or
	adduser("amoffat", "--system", "--shell", "/bin/bash", "--no-create-home")

.. seealso:: :ref:`faq_arg_ordering`
