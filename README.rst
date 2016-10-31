.. image:: https://travis-ci.org/amoffat/sh.svg?branch=master
    :target: https://travis-ci.org/amoffat/sh
    :alt: Build Status
.. image:: https://coveralls.io/repos/amoffat/sh/badge.png?branch=master
    :target: https://coveralls.io/r/amoffat/sh?branch=master
    :alt: Coverage Status
|
.. image:: https://pypip.in/v/sh/badge.png
    :target: https://pypi.python.org/pypi/sh
    :alt: Version
.. image:: https://pypip.in/d/sh/badge.png
    :target: https://pypi.python.org/pypi/sh
    :alt: Downloads
|
sh is a full-fledged subprocess replacement for Python 2.6 - 3.5, PyPy and PyPy3
that allows you to call any program as if it were a function:

.. code:: python

    from sh import ifconfig
    print ifconfig("eth0")

sh is *not* a collection of system commands implemented in Python.

============
Installation
============

::

    $> pip install sh

=====================================================
Complete documentation @ http://amoffat.github.com/sh
=====================================================

=======
Testing
=======

First install the development requirements:

::

    $> pip install -r requirements-dev.txt

The run the tests:

::

    $> python sh.py test

To run a single test for all environments:

::

    $> python sh.py test FunctionalTests.test_unicode_arg

To run a single test for a single environment:

::

    $> python sh.py test -e 3.4 FunctionalTests.test_unicode_arg
