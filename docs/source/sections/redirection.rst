.. _redirection:

Redirection
===========

sh can redirect the STDOUT and STDERR of a process to many different types of
targets, using the :ref:`_out <out>` and :ref:`_err <err>` special kwargs.

Filename
--------

If a string is used, it is assumed to be a filename.  The filename is opened as
"wb", meaning truncate-write and binary mode.

.. code-block:: python

    import sh
    sh.ifconfig(_out="/tmp/interfaces")

.. seealso:: :ref:`faq_append`

File-like Object
----------------

You may also use any object that supports ``.write(data)``, like
:class:`io.StringIO`:

.. code-block:: python

    import sh
    from io import StringIO

    buf = StringIO()
    sh.ifconfig(_out=buf)
    print(buf.getvalue())

.. _red_func:

Function Callback
-----------------

A callback function may also be used as a target.  The function must conform to
one of three signatures:

.. py:function:: fn(data)
    :noindex:

    The function takes just the chunk of data from the process.

.. py:function:: fn(data, stdin_queue)
    :noindex:

    In addition to the previous signature, the function also takes a
    :class:`queue.Queue`, which may be used to communicate programmatically with
    the process.

.. py:function:: fn(data, stdin_queue, process)
    :noindex:

    In addition to the previous signature, the function takes a
    :class:`weakref.ref` to the :ref:`OProc <oproc_class>` object.

.. seealso:: :ref:`callbacks`

.. seealso:: :ref:`tutorial2`
