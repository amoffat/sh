.. _faq:

FAQ
===

How do I execute a bash builtin?
--------------------------------

.. code-block:: python

    import sh

    sh.bash("-c", "your_builtin")

Or

.. code-block:: python

    import sh

    builtins = sh.bash.bake("-c")
    builtins("your_builtin")


Will Windows be supported?
--------------------------

There are no plans to support Windows.

.. _faq_append:

How do I append output to a file?
---------------------------------

Use a file object opened in the mode you desire:

.. code-block:: python

    import sh

    h = open("/tmp/output", "a")

    sh.ls("/dir1", _out=h)
    sh.ls("/dir2", _out=h)

.. _faq_color_output:

Why does my command's output have color?
----------------------------------------

Typically the reason for this is that your program detected that its STDOUT was
connected to a TTY, and therefore decided to print color escape sequences in its
output.  The typical solution is to use :ref:`_tty_out=False <tty_out>`, which
will force a pipe to be connected to STDOUT, and probably change the behavior of
the program.

.. seealso::

    Git is one of the programs that makes extensive use of terminal colors (as
    well as pagers) in its output, so we added :ref:`a contrib version
    <contrib_git>` for convenience.

.. _faq_tty_out:

Why is _tty_out=True the default?
---------------------------------

This was a design decision made for two reasons:

1. To make programs behave in the same way as seen on the commandline.
2. To provide better buffering control than pipes allow.

For #1, we want sh to produce output that is identical to what the user sees
from the commandline, because that's typically the only output they ever see
from their command.  This makes the output easy to understand.

For #2, using a TTY for STDOUT allows us to precisely control the buffering of a
command's output to sh's internal code.

.. seealso:: :ref:`arch_buffers`

Of course, there are some gotchas with TTY STDOUT.  One of them is commands that
use a pager, for example:

.. code-block:: python

    import sh
    print(sh.git.log())


This will sometimes raise a ``SignalException_SIGPIPE``. The reason is because
``git log`` detects a TTY STDOUT and forks the system’s pager (typically
``less``) to handle the output. The pager checks for a controlling terminal,
and, finding none, exits with exit code 1. The exit of the pager means no more
readers on ``git log``’s output, and thus a ``SIGPIPE`` is received.

One solution to the ``git log`` problem above is simply to use
``_tty_out=False``. Another option, specifically for git, is to use the
``git --no-pager`` option:

.. code-block:: python

    import sh
    print(sh.git('--no-pager', 'log'))


Why doesn't "*" work as a command argument?
-------------------------------------------

Glob expansion is a feature of a shell, like Bash, and is performed by the shell
before passing the results to the program to be exec'd.  Because sh is not a
shell, but rather tool to execute programs directly, we do not handle glob
expansion like a shell would.

So in order to use ``"*"`` like you would on the commandline, pass it into
:func:`glob.glob` first:

.. code-block:: python

    import sh
    import glob
    sh.ls(glob.glob("*.py"))


.. _faq_path:

How do I call a program that isn't in ``$PATH``?
------------------------------------------------

Use the :meth:`Command` constructor to instantiate an instance of Command
directly, then execute that:

.. code-block:: python

    import sh
    cmd = sh.Command("/path/to/command")
    cmd("-v", "arg1")

How do I execute a program with a dash in its name?
---------------------------------------------------

If it's in your ``$PATH``, substitute the dash for an underscore:

.. code-block:: python

    import sh
    sh.google_chrome("http://google.com")

The above will run ``google-chrome http://google.com``

.. note::

    If a program named ``google_chrome`` exists on your system, that will be
    called instead.  In that case, in order to execute the program with a dash
    in the name, you'll have to use the method described :ref:`here.
    <faq_special>`

.. _faq_special:

How do I execute a program with a special character in its name?
----------------------------------------------------------------

Programs with non-alphanumeric, non-dash characters in their names cannot be
executed directly as an attribute on the sh module.  For example, **this will not
work:**

.. code-block:: python

    import sh
    sh.mkfs.ext4()

The reason should be fairly obvious.  In Python, characters like ``.`` have
special meaning, in this case, attribute access.  What sh is trying to do in the
above example is find the program "mkfs" (which may or may not exist) and then
perform a :ref:`subcommand lookup <subcommands>` with the name "ext4".  In other
words, it will try to call ``mkfs`` with the argument ``ext4``, which is
probably not what you want.

The workaround is instantiating the :ref:`Command Class <command_class>` with
the string of the program you're looking for:

.. code-block:: python

    import sh
    mkfsext4 = sh.Command("mkfs.ext4")
    mkfsext4() # run it

.. _faq_pipe_syntax:


Why not use ``|`` to pipe commands?
-----------------------------------

I prefer the syntax of sh to resemble function composition instead of a
pipeline.  One of the goals of sh is to make executing processes more like
calling functions, not making function calls more like Bash.

Why isn't piping asynchronous by default?
-----------------------------------------

There is a non-obvious reason why async piping is not possible by default.
Consider the following example:

.. code-block:: python

    import sh

    sh.cat(sh.echo("test\n1\n2\n3\n"))

When this is run, ``sh.echo`` executes and finishes, then the entire output
string is fed into ``sh.cat``.  What we would really like is each
newline-delimited chunk to flow to ``sh.cat`` incrementally.

But for this example to flow data asynchronously from echo to cat, the echo
command would need to *not block.*  But how can the inner command know the
context of its execution, to know to block sometimes but not other times?  It
can't know that without something explicit.

This is why the :ref:`piped` special kwarg was introduced.  By default, commands
executed block until they are finished, so in order for an inner command to not
block, ``_piped=True`` signals to the inner command that it should not block.
This way, the inner command starts running, then very shortly after, the outer
command starts running, and both are running simultaneously.  Data can then flow
from the inner command to the outer command asynchronously:

.. code-block:: python

    import sh

    sh.cat(sh.echo("test\n1\n2\n3\n", _piped=True))

Again, this example is contrived -- a better example would be a long-running
command that produces a lot of output that you wish to pipe through another
program incrementally.

How do I run a command and connect it to sys.stdout and sys.stdin?
------------------------------------------------------------------

There are two ways to do this

.. seealso:: :ref:`fg`

You can use :data:`sys.stdin`, :data:`sys.stdout`, and :data:`sys.stderr` as
arguments to :ref:`in`, :ref:`out`, :ref:`err`, respectively, and it *should*
mostly work as expected:

.. code-block:: python

    import sh
    import sys
    sh.your_command(_in=sys.stdin, _out=sys.stdout)

There are a few reasons why this probably won't work.  The first reason is that
:data:`sys.stdin` is probably a controlling TTY (attached to the shell that
launched the python process), and probably not set in raw mode
:manpage:`termios(3)`, which means that, among other things, input is buffered
by newlines.

The real solution is to use :ref:`_fg=True <fg>`:

.. code-block:: python

    import sh
    sh.top(_fg=True)


.. _faq_separate_args:

Why do my arguments need to be separate strings?
------------------------------------------------

This confuses many new sh users.  They want to do something like this and expect
it to just work:

.. code-block:: python

    from sh import tar
    tar("cvf /tmp/test.tar /my/home/directory")

But instead they'll get a confusing error message:

.. code-block:: none

    RAN: '/bin/tar cvf /tmp/test.tar /my/home/directory'

    STDOUT:

    STDERR:
    /bin/tar: Old option 'f' requires an argument.
    Try '/bin/tar --help' or '/bin/tar --usage' for more information.

The reason why they expect it to work is because shells, like Bash, automatically
parse your commandline and break up arguments for you, before sending them to
the binary.  They have a complex set of rules (some of which are represented by
:mod:`shlex`) to take a single string of a command and arguments and separate
them.

Even if we wanted to implement this in sh (which we don't), it would hurt the
ability for users to parameterize parts of their arguments.  They would have to
use string interpolation, which would be ugly and error prone:

.. code-block:: python

    from sh import tar
    tar("cvf %s %s" % ("/tmp/tar1.tar", "/home/oh no a space")

In the above example, ``"/home/oh"``, ``"no"``, ``"a"``, and ``"space"`` would
all be separate arguments to tar, causing the program to behave unexpectedly.
Basically every command with parameterized arguments would need to expect
characters that could break the parser.

.. _faq_arg_ordering:

How do I order keyword arguments?
---------------------------------

Typically this question gets asked when a user is trying to execute something
like the following commandline:

.. code-block:: none

    my-command --arg1=val1 arg2 --arg3=val3

This is usually the first attempt that they make:

.. code-block:: python

    sh.my_command(arg1="val1", "arg2", arg3="val3")

This doesn't work because, in Python, position arguments, like ``arg2`` cannot
come after keyword arguments.

Furthermore, it is entirely possible that ``--arg3=val3`` comes before
``--arg1=val1``.  The reason for this is that a function's ``**kwargs`` is an
unordered mapping, and so key-value pairs are not guaranteed to resolve to a
specific order.

So the solution here is to forego the usage of the keyword argument
*convenience*, and just use raw ordered arguments:

.. code-block:: python

    sh.my_command("--arg1=val1", "arg2", "--arg3=val3")

.. _faq_pylint:

How to disable pylint E1101 no-member errors?
---------------------------------------------

Pylint complains with E1101 no-member to almost all ``sh.command`` invocations,
because it doesn't know, that these members are generated dynamically.
Starting with Pylint 1.6 these messages can be suppressed using `generated-members <https://docs.pylint.org/en/1.6.0/features.html#id28>`_ option.

Just add following lines to ``pylintrc``::

    [TYPECHECK]
    generated-members=sh


How do I patch sh in my tests?
------------------------------

sh can be patched in your tests the typical way, with
:func:`unittest.mock.patch`:

.. code-block:: python

    from unittest.mock import patch
    import sh

    def get_something():
        return sh.pwd()

    @patch("sh.pwd", create=True)
    def test_something(pwd):
        pwd.return_value = "/"
        assert get_something() == "/"

The important thing to note here is that ``create=True`` is set.  This is
required because sh is a bit magical and ``patch`` will fail to find the ``pwd``
command as an attribute on the sh module.

You may also patch the :class:`Command` class:

.. code-block:: python

    from unittest.mock import patch
    import sh

    def get_something():
        pwd = sh.Command("pwd")
        return pwd()

    @patch("sh.Command")
    def test_something(Command):
        Command().return_value = "/"
        assert get_something() == "/"

Notice here we do not need ``create=True``, because :class:`Command` is not an
automatically generated object on the sh module (it actually exists).


Why is sh just a single file?
-----------------------------

When sh was first written, the design decision was made to make it a single-file
module.  This has pros and cons:

Cons:

- Auditing the code is more challenging
- Without file-enforced structure, adding more features and abstractions makes
  the code harder to follow
- Cognitively, it feels cluttered

Pros:

- Can be used easily on systems without Python package managers
- Can be embedded/bundled together with other software more easily
- Cognitively, it feels more self-contained

In my mind, because the primary target audience of sh users is generally more
scrappy devops, systems people, or people just trying to stitch together some
clunky system programs, the listed pros weigh a little more heavily than the
cons.  Sacrificing some development advantages to give those users a more
flexible tool is a win to me.

Down the road, the development disadvantages of a single file can be solved with
additional development tools, for example, with a tool that compiles multiple
modules into the single sh.py file.  Realistically, though, sh is pretty mature,
so I don't see it growing much more in complexity or code size.

How do I see the commands sh is running?
----------------------------------------

Use logging:

.. code-block:: python

    import logging
    import sh

    logging.basicConfig(level=logging.INFO)
    sh.ls()

.. code-block:: none

    INFO:sh.command:<Command '/bin/ls'>: starting process
    INFO:sh.command:<Command '/bin/ls', pid 32394>: process started
    INFO:sh.command:<Command '/bin/ls', pid 32394>: process completed
    ...
