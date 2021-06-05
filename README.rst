.. image:: https://raw.githubusercontent.com/amoffat/sh/master/logo-230.png
    :target: https://amoffat.github.com/sh
    :alt: Logo

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

sh is a full-fledged subprocess replacement for Python 2, Python 3, PyPy and PyPy3
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

I've included a Docker test suite in the `docker_test_suit/` folder.  To build the image, `cd` into that directory and
run::

    $> ./build.sh

This will install ubuntu 18.04 LTS and all supported python versions.  Once it's done, stay in that directory and
run::

    $> ./run.sh

This will mount your local code directory into the container and start the test suite, which will take a long time to
run.  If you wish to run a single test, you may pass that test to `./run.sh`::

    $> ./run.sh FunctionalTests.test_unicode_arg

To run a single test for a single environment::

    $> ./run.sh -e 3.4 FunctionalTests.test_unicode_arg

Coverage
--------

First run all of the tests::

    $> python sh.py test

This will aggregate a ``.coverage``.  You may then visualize the report with::

    $> coverage report

Or generate visual html files with::

    $> coverage html

Which will create ``./htmlcov/index.html`` that you may open in a web browser.
