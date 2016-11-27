.. _default_arguments:

Default Arguments
=================

Many times, you want to override the default arguments of all commands launched
through sh.  For example, suppose you want the output of all commands to be
aggregated into a :class:`io.StringIO` buffer.  The naive way would be this:

.. code-block:: python

    import sh
    from io import StringIO

    buf = StringIO()

    sh.ls("/", _out=buf)
    sh.whoami(_out=buf)
    sh.ps("auxwf", _out=buf)

Clearly, this gets tedious quickly.  Fortunately, we can create execution
contexts that allow us to set default arguments on all commands spawned from
that context:

.. code-block:: python

    import sh
    from io import StringIO

    buf = StringIO()
    sh2 = sh(_out=buf)

    sh2.ls("/")
    sh2.whoami()
    sh2.ps("auxwf")

Now, anything launched from ``sh2`` will send its output to the ``StringIO``
instance ``buf``.

Execution contexts may also be imported from, like it is the top-level sh
module:

.. code-block:: python

    import sh
    from io import StringIO

    buf = StringIO()
    sh2 = sh(_out=buf)

    from sh2 import ls, whoami, ps

    ls("/")
    whoami()
    ps("auxwf")
