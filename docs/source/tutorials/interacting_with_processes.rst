.. _tutorial2:

Entering an SSH password
========================

Here we will attempt to SSH into a server and enter a password programmatically.

.. note::

    It is recommended that you just ``ssh-copy-id`` to copy your public key to
    the server so you don't need to enter your password, but for the purposes of
    this demonstration, we try to enter a password.

To interact with a process, we need to assign a callback to STDOUT.  The
callback signature we'll use will take a :class:`queue.Queue` object for the
second argument, and we'll use that to send STDIN back to the process.

.. seealso:: :ref:`red_func`

Here's our first attempt:

.. code-block:: python

    from sh import ssh

    def ssh_interact(line, stdin):
        line = line.strip()
        print(line)
        if line.endswith("password:"):
            stdin.put("correcthorsebatterystaple")

    ssh("10.10.10.100", _out=ssh_interact)

If you run this (substituting an IP that you can SSH to), you'll notice that
nothing is printed from within the callback.  The problem has to do with STDOUT
buffering.  By default, sh line-buffers STDOUT, which means that
``ssh_interact`` will only receive output when sh encounters a newline in the
output.  This is a problem because the password prompt has no newline:

.. code-block:: none

    amoffat@10.10.10.100's password:

Because a newline is never encountered, nothing is sent to the ``ssh_interact``
callback.  So we need to change the STDOUT buffering.  We do this with the
:ref:`_out_bufsize <out_bufsize>` special kwarg.  We'll set
it to 0 for unbuffered output:

.. code-block:: python

    from sh import ssh
    
    def ssh_interact(line, stdin):
        line = line.strip()
        print(line)
        if line.endswith("password:"):
            stdin.put("correcthorsebatterystaple")

    ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0)

If you run this updated version, you'll notice a new problem.  The output looks
like this:

.. code-block:: none

    a
    m
    o
    f
    f
    a
    t
    @
    1
    0
    .
    1
    0
    .
    1
    0
    .
    1
    0
    0
    '
    s
    
    p
    a
    s
    s
    w
    o
    r
    d
    :

This is because the chunks of STDOUT our callback is receiving are unbuffered,
and are therefore individual characters, instead of entire lines.  What we need
to do now is aggregate this character-by-character data into something more
meaningful for us to test if the pattern ``password:`` has been sent, signifying
that SSH is ready for input.

It would make sense to encapsulate the variable we'll use for aggregating into
some kind of closure or class, but to keep it simple, we'll just use a global:

.. code-block:: python

    from sh import ssh
    import sys

    aggregated = ""
    def ssh_interact(char, stdin):
        global aggregated
        sys.stdout.write(char.encode())
        sys.stdout.flush()
        aggregated += char
        if aggregated.endswith("password: "):
            stdin.put("correcthorsebatterystaple")

    ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0)

You'll also notice that the example still doesn't work.  There are two problems:
The first is that your password must end with a newline, as if you had typed it
and hit the return key.  This is because SSH has no idea how long your password
is, and is line-buffering STDIN.

The second problem lies deeper in SSH.  SSH needs a TTY attached to its STDIN in
order to work properly.  This tricks SSH into believing that it is interacting
with a real user in a real terminal session.  To enable TTY, we can add the
:ref:`_tty_in <tty_in>` special kwarg.  We also need to use :ref:`_unify_ttys <unify_ttys>` special kwarg.
This tells sh to make STDOUT and STDIN come from a single pseudo-terminal, which is a requirement of SSH:

.. code-block:: python

    from sh import ssh
    import sys

    aggregated = ""
    def ssh_interact(char, stdin):
        global aggregated
        sys.stdout.write(char.encode())
        sys.stdout.flush()
        aggregated += char
        if aggregated.endswith("password: "):
            stdin.put("correcthorsebatterystaple\n")

    ssh("10.10.10.100", _out=ssh_interact, _out_bufsize=0, _tty_in=True, _unify_ttys=True)
    
And now our remote login script works!

.. code-block:: none

    amoffat@10.10.10.100's password: 
    Linux 10.10.10.100 testhost #1 SMP Tue Jun 21 10:29:24 EDT 2011 i686 GNU/Linux
    Ubuntu 10.04.2 LTS
    
    Welcome to Ubuntu!
     * Documentation:  https://help.ubuntu.com/
    
    66 packages can be updated.
    53 updates are security updates.
    
    Ubuntu 10.04.2 LTS
    
    Welcome to Ubuntu!
     * Documentation:  https://help.ubuntu.com/
    You have new mail.
    Last login: Thu Sep 13 03:53:00 2012 from some.ip.address
    amoffat@10.10.10.100:~$ 

SSH Contrib command
-------------------

The above process can be simplified by using a :ref:`contrib`. The :ref:`SSH contrib command <contrib_ssh>` does
all the ugly kwarg argument setup for you, and provides a simple but powerful interface for doing SSH password logins.
Please see the :ref:`SSH contrib command <contrib_ssh>` for more details about the exact api:

.. code-block:: python

    from sh.contrib import ssh

    def ssh_interact(content, stdin):
        sys.stdout.write(content.cur_char)
        sys.stdout.flush()

    # automatically logs in with password and then presents subsequent content to
    # the ssh_interact callback
    ssh("10.10.10.100", password="correcthorsebatterystaple", interact=ssh_interact)

How you should REALLY be using SSH
----------------------------------

Many people want to learn how to enter an SSH password by script because they
want to execute remote commands on a server.  Instead of trying to log in
through SSH and then sending terminal input of the command to run, let's see how
we can do it another way.

First, open a terminal and run ``ssh-copy-id yourservername``.  You'll be asked
to enter your password for the server.  After entering your password, you'll be
able to SSH into the server without needing a password again.  This simplifies
things greatly for sh.

The second thing we want to do is use SSH's ability to pass a command to run
to the server you're SSHing to.  Here's how you can run ``ifconfig`` on a server
without having to use that server's shell directly:

.. code-block:: none

    ssh amoffat@10.10.10.100 ifconfig 

Translating this to sh, it becomes:

.. code-block:: python

    import sh

    print(sh.ssh("amoffat@10.10.10.100", "ifconfig"))

We can make this even nicer by taking advantage of sh's :ref:`baking` to bind
our server username/ip to a command object:

.. code-block:: python

    import sh

    my_server = sh.ssh.bake("amoffat@10.10.10.100")
    print(my_server("ifconfig"))
    print(my_server("whoami"))

Now we have a reusable command object that we can use to call remote commands.
But there is room for one more improvement.  We can also use sh's
:ref:`subcommands` feature which expands attribute access into command
arguments:

.. code-block:: python

    import sh

    my_server = sh.ssh.bake("amoffat@10.10.10.100")
    print(my_server.ifconfig())
    print(my_server.whoami())
