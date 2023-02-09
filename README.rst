.. image:: https://raw.githubusercontent.com/amoffat/sh/master/images/logo-230.png
    :target: https://amoffat.github.com/sh
    :alt: Logo

**If you are migrating from 1.* to 2.*, please see MIGRATION.md**

|

.. image:: https://img.shields.io/pypi/v/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Version
.. image:: https://img.shields.io/pypi/dm/sh.svg?style=flat-square
    :target: https://pypi.python.org/pypi/sh
    :alt: Downloads Status
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

sh is a full-fledged subprocess replacement for Python 3.8 - 3.10, PyPy and PyPy3
that allows you to call *any* program as if it were a function:

.. code:: python

    from sh import ifconfig
    print(ifconfig("eth0"))

sh is *not* a collection of system commands implemented in Python.

sh relies on various Unix system calls and only works on Unix-like operating
systems - Linux, macOS, BSDs etc. Specifically, Windows is not supported.

`Complete documentation here <https://amoffat.github.io/sh>`_

Installation
============

::

    $> pip install sh

Support
=======
* `Andrew Moffat <https://github.com/amoffat>`_ - author/maintainer
* `Erik Cederstrand <https://github.com/ecederstrand>`_ - maintainer


Developers
==========

Updating the docs
-----------------

Check out the `gh-pages <https://github.com/amoffat/sh/tree/gh-pages>`_ branch and follow the ``README.rst`` there.

Testing
-------

Tests are run in a docker container against all supported Python versions. To run, make the following target::

    $> make test

To run a single test::

    $> make test='FunctionalTests.test_background' test_one

Coverage
--------

First run all of the tests::

    $> SH_TESTS_RUNNING=1 coverage run --source=sh -m unittest

This will aggregate a ``.coverage``.  You may then visualize the report with::

    $> coverage report

Or generate visual html files with::

    $> coverage html

Which will create ``./htmlcov/index.html`` that you may open in a web browser.
