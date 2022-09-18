.. _sudo:

Using Sudo
==========

There are 3 ways of using ``sudo`` to execute commands in your script.  These
are listed in order of usefulness and security.  In most cases, you should just
use a variation of :ref:`contrib_sudo`.

.. _contrib_sudo:

sh.contrib.sudo
---------------

Because ``sudo`` is so frequently used, we have added a contrib version of the
command to make sudo usage more intuitive.  This contrib version is simply a
wrapper around the :ref:`sudo_raw` raw command, but we bake in some
:ref:`special keyword argument <special_arguments>` to make it well-behaved.  In
particular, the contrib version allows you to specify your password at execution
time via terminal input, or as a string in your script.

Terminal Input
^^^^^^^^^^^^^^

Via a :ref:`with context <with_contexts>`:

.. code-block:: python

    import sh

    with sh.contrib.sudo:
        print(ls("/root"))

Or alternatively via :ref:`subcommands <subcommands>`:

.. code-block:: python

    import sh
    print(sh.contrib.sudo.ls("/root"))

Output:

.. code-block:: none

    [sudo] password for youruser: *************
    your_root_files.txt

In the above example, ``sh.contrib.sudo`` automatically asks you for a password
using :func:`getpass.getpass` under the hood.

This method is the most secure, because it lowers the chances of doing something
insecure, like including your password in your python script, or by saying that
a particular user can execute anything inside of a particular script (the
NOPASSWD method).

.. note::

    ``sh.contrib.sudo`` does not do password caching like the sudo binary does.
    Thie means that each time a sudo command is run in your script, you will be
    asked to type in a password.

String Input
^^^^^^^^^^^^

You may also specify your password to ``sh.contrib.sudo`` as a string:

.. code-block:: python

    import sh

    password = get_your_password()

    with sh.contrib.sudo(password=password, _with=True):
        print(ls("/root"))

.. warning::

    This method is less secure because it becomes tempting to hard-code your
    password into the python script, and that's a bad idea.  However, it is more
    flexible, because it allows you to obtain your password from another source,
    so long as the end result is a string.

/etc/sudoers NOPASSWD
---------------------

With this method, you can use the raw ``sh.sudo`` command directly, because
you're being guaranteed that the system will not ask you for a password.  It
first requires you set up your user to have root execution privileges

Edit your sudoers file:

.. code-block:: none

    $> sudo visudo

Add or edit the line describing your user's permissions:

.. code-block:: none

    yourusername ALL = (root) NOPASSWD: /path/to/your/program

This says ``yourusername`` on ``ALL`` hosts will be able to run as root, but
only root ``(root)`` (no other users), and that no password ``NOPASSWD`` will be
asked of ``/path/to/your/program``.

.. warning::
    
    This method can be insecure if an unprivileged user can edit your script,
    because the entire script will be exited as a privileged user.  A malicious
    user could put something bad in this script.

.. _sudo_raw:

sh.sudo
-------

Using the raw command ``sh.sudo`` (which resolves directly to the system's
``sudo`` binary) without NOPASSWD is possible, provided you wire up the special
keyword arguments on your own to make it behave correctly.  This method is
discussed generally for educational purposes; if you take the time to wire up
``sh.sudo`` on your own, then you have in essence just recreated
:ref:`contrib_sudo`.

.. code-block:: python

    import sh

    # password must end in a newline
    my_password = "password\n"

    # -S says "get the password from stdin"
    my_sudo = sh.sudo.bake("-S", _in=my_password)

    print(my_sudo.ls("root"))

_fg=True
--------

Another less-obvious way of using sudo is by executing the raw ``sh.sudo``
command but also putting it in the foreground.  This way, sudo will work
correctly automatically, by hooking up stdin/out/err automatically, and by
asking you for a password if it requires one.  The downsides of using
:ref:`_fg=True <fg>`, however, are that you cannot capture its output -- everything is
just printed to your terminal as if you ran it from a shell.

.. code-block:: python

    import sh
    sh.sudo.ls("/root", _fg=True)
