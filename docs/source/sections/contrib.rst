.. _contrib:

Contrib Commands
################

Contrib is an sh sub-module that provides friendly wrappers to useful commands.
Typically, the commands being wrapped are unintuitive, and the contrib version
makes them intuitive.

.. note::

    Contrib commands should be considered generally unstable. They will grow and change as the community figures out the
    best interface for them.

Commands
========

Sudo
----

Allows you to enter your password from the terminal at runtime, or as a string
in your script.

.. py:function:: sudo(password=None, *args, **kwargs)

    Call sudo with ``password``, if specified, else ask the executing user for a
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

.. _contrib_ssh:

SSH
---

.. versionadded:: 1.13.0

SSH password-based logins :ref:`can be a pain <tutorial2>`. This contrib command performs all of the ugly setup and
provides a clean interface to using SSH.

.. py:function:: ssh(interact=None, password=None, prompt_match=None, login_success=None, *args, **kwargs)

    :param interact: A callback to handle SSH session interaction *after* login is successful. Required.
    :param password: A password string or a function that returns a password string. Optional. If not provided, :func:`getpass.getpass` is used.
    :param prompt_match: The string to match in order to determine when to provide SSH with the password. Or a function
            that matches on the output. Optional.
    :param login_success: A function to determine if SSH login is successful. Optional.

The ``interact`` parameter takes a callback with a signature that is slightly different to the function callbacks for
:ref:`redirection <red_func>`:

.. py:function:: fn(content, stdin_queue)
    
    :param content: An instance of an ephemeral :ref:`SessionContent <session_content>` class whose job is to hold the
            characters that the SSH session has written to STDOUT.
    :param stdin_queue: A :class:`queue.Queue` object to communicate with STDIN programmatically.

``password`` can be simply a string that will be used to type the password. If it's not provided, it will be read from STDIN
at runtime via :func:`getpass.getpass`. It can also be a callable that returns the password string.

``prompt_match`` is a string to match before the contrib command will provide the SSH process with the password. It is
optional, and if left unspecified, will default to "password: ". It can also be a callable that is called on a
:ref:`SessionContent <session_content>` instance and returns ``True`` or ``False`` for a match.

``login_success`` is a function that takes a :ref:`SessionContent <session_content>` object and returns a boolean for
whether or not a successful login occurred. It is optional, and if unspecified, simply evaluates to ``True``, meaning
any password submission results in a successful login (obviously not always correct). It is recommended that you specify
this.

.. _session_content:

.. py:class:: SessionContent()

    This class contains a record lines and characters written to the SSH processes's STDOUT. It should be all you need
    from the callbacks to determine how to interact with the SSH process.

.. py:attribute:: SessionContent.chars
    
    :type: :class:`collections.deque`
    
    The previous 50,000 characters.

.. py:attribute:: SessionContent.lines
    
    :type: :class:`collections.deque`
    
    The previous 5,000 lines.

.. py:attribute:: SessionContent.line_chars
    
    :type: list

    The characters in the line currently being aggregated.

.. py:attribute:: SessionContent.cur_line
    
    :type: str

    A string of the line currently being aggregated.

.. py:attribute:: SessionContent.last_line
    
    :type: str

    The previous line.

.. py:attribute:: SessionContent.cur_char
    
    :type: str

    The currently written character.

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
