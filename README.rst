.. image:: https://raw.githubusercontent.com/amoffat/sh/master/logo-230.png
    :target: https://amoffat.github.com/sh
    :alt: Logo

|

.. image:: https://img.shields.io/pypi/v/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Version
.. image:: https://img.shields.io/pypi/pyversions/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Python Versions
.. image:: https://img.shields.io/travis/amoffat/sh/master.svg?style=flat-square
    :target: https://travis-ci.org/amoffat/sh
    :alt: Build Status
.. image:: https://img.shields.io/coveralls/amoffat/sh.svg?style=flat-square
    :target: https://coveralls.io/r/amoffat/sh?branch=master
    :alt: Coverage Status

|

sh is a full-fledged subprocess replacement for Python 2.6 - 3.6, PyPy and PyPy3
that allows you to call any program as if it were a function:

.. code:: python

    from sh import ifconfig
    print ifconfig("eth0")

sh is *not* a collection of system commands implemented in Python.

`Complete documentation here<https://amoffat.github.com/sh>`_

Installation
============

::

    $> pip install sh

Updating the docs
=================

Check out the `gh-pages <https://github.com/amoffat/sh/tree/gh-pages>`_ branch and follow the ``README.rst`` there.

Developers
==========

Testing
-------

First install the development requirements::

    $> pip install -r requirements-dev.txt

The run the tests for all Python versions on your system::

    $> python sh.py test

To run a single test for all environments::

    $> python sh.py test FunctionalTests.test_unicode_arg

To run a single test for a single environment::

    $> python sh.py test -e 3.4 FunctionalTests.test_unicode_arg

Coverage
--------

First run all of the tests::

    $> python sh.py test

This will aggregate a ``.coverage``.  You may then visualize the report with::

    $> coverage report

Or generate visual html files with::

    $> coverage html

Which will create ``./htmlcov/index.html`` that you may open in a web browser.
