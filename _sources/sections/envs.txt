.. _environments:

Environments
============

The :ref:`_env <env>` special kwarg allows you to pass a dictionary of
environment variables and their corresponding values:

.. code-block:: python

	import sh
	sh.google_chrome(_env={"SOCKS_SERVER": "localhost:1234"})
	

:ref:`_env <env>` replaces your process's environment completely.  Only the
key-value pairs in :ref:`_env <env>` will be used for its environment.  If you
want to add new environment variables for a process *in addition to* your
existing environment, try something like this:

.. code-block:: python

    import os
    import sh
    
    new_env = os.environ.copy()
    new_env["SOCKS_SERVER"] = "localhost:1234"
    
    sh.google_chrome(_env=new_env)

.. seealso::

    To make an environment apply to all sh commands look into
    :ref:`default_arguments`.
