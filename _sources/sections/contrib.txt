.. _contrib:

Contrib Commands
################

Contrib is an sh sub-module that provides friendly wrappers to useful commands.
Typically, the commands being wrapped are unintuitive, and the contrib version
makes them intuitive.

Commands
========

Sudo
----

Allows you to enter your password from the terminal at runtime, or as a string
in your script.

.. py:function:: sudo(password=None, *args, **kwargs)

    Call sudo with *password*, if specified, else ask the executing user for a
    password at runtime via :func:`getpass.getpass`.

.. seealso:: :ref:`contrib_sudo`

.. _contrib_git:

Git
---

Many git commands use a pager for output, which can cause an unexpected behavior
when run through sh.  To account for this, the contrib version sets
``_tty_out=False`` for all git commands.

.. py:function:: git(*args, **kwargs)

    Call git with STDOUT connected to a pipe, instead of a TTY.

.. code-block:: python

    from sh.contrib import git
    repo_log = git.log()

.. seealso:: :ref:`faq_tty_out` and :ref:`faq_color_output`


Extending
=========

For developers.

To extend contrib, simply decorate a function in sh with the ``@contrib``
decorator, and pass in the name of the command you wish to shadow to the
decorator.  This method must return an instance of :ref:`Command
<command_class>`:

.. code-block:: python

    @contrib("ls")
    def my_ls(original):
        ls = original.bake("-l")
        return ls

Now you can run your custom contrib command from your scripts, and you'll be
using the command returned from your decorated function:


.. code-block:: python

    from sh.contrib import ls

    # executing: ls -l
    print(ls("/"))

For even more flexibility, you can design your contrib command to rewrite its
options based on *executed* arguments.  For example, say you only wish to set a
command's argument if another argument is set.  You can accomplish it like this:

.. code-block:: python

    @contrib("ls")
    def my_ls(original):
        def process(args, kwargs):
            if "-a" in args:
                args.append("-L")
            return args, kwargs

        ls = original.bake("-l")
        return ls, process

Returning a process function along with the command will tell sh to use that
function to preprocess the arguments at execution time using the
:ref:`_arg_preprocess <preprocess>` special kwarg.
