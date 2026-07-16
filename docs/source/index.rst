
.. toctree::
    :hidden:

    usage
    reference

    sections/contrib
    sections/sudo
    sections/migration

    tutorials
    sections/faq

    ref_to_fulldoc

.. image:: images/logo-230.png
    :alt: Logo

sh
##

.. image:: https://img.shields.io/pypi/v/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Version
.. image:: https://img.shields.io/pypi/dm/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Downloads Status
.. image:: https://img.shields.io/pypi/pyversions/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Python Versions
.. image:: https://img.shields.io/coveralls/amoffat/sh.svg?style=flat-square
    :target: https://coveralls.io/r/amoffat/sh?branch=master
    :alt: Coverage Status
.. image:: https://img.shields.io/github/stars/amoffat/sh.svg?style=social&label=Star
    :target: https://github.com/amoffat/sh
    :alt: Github

sh is a full-fledged subprocess replacement for Python 3.10+ and PyPy that
allows you to call any program as if it were a function:


.. code-block:: python

    from sh import git
    print(git("status", "--short"))
	
Note that these aren't Python functions, these are running the binary commands
on your system by dynamically resolving your ``$PATH``, much like Bash does, and
then wrapping the binary in a function.  In this way, all the programs on your
system are easily available to you from within Python.

sh relies on various Unix system calls and only works on Unix-like operating
systems - Linux, macOS, BSDs etc. Specifically, Windows is not supported.


Installation
============

.. code-block:: none

    pip install sh


Quick Reference
===============

Passing Arguments
-----------------

.. code-block:: python
    
    sh.ls("-l", "/tmp", color="never")

:ref:`Read More <passing_arguments>`

Exit Codes
----------

.. code-block:: python

    try:
        sh.ls("/doesnt/exist")
    except sh.ErrorReturnCode_2:
        print("directory doesn't exist")

:ref:`Read More <exit_codes>`

Redirection
-----------

.. code-block:: python

    sh.ls(_out="/tmp/dir_contents")

    with open("/tmp/dir_contents", "w") as h:
        sh.ls(_out=h)

    from io import StringIO
    buf = StringIO()
    sh.ls(_out=buf)

:ref:`Read More <redirection>`

Baking
------

.. code-block:: python

    my_ls = sh.ls.bake("-l")

    # equivalent
    my_ls("/tmp")
    sh.ls("-l", "/tmp")

:ref:`Read More <baking>`

Piping
------

.. code-block:: python

    sh.wc("-l", _in=sh.ls("-1"))

:ref:`Read More <piping>`

Subcommands
-----------

.. code-block:: python

    # equivalent
    sh.git("show", "HEAD")
    sh.git.show("HEAD")

:ref:`Read More <subcommands>`


Background Processes
--------------------

.. code-block:: python

    p = sh.find("-name", "sh.py", _bg=True)
    # ... do other things ...
    p.wait()

:ref:`Read More <background>`

.. include:: ref_to_fulldoc.rst
