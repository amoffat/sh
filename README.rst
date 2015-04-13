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
sh (previously `pbs <http://pypi.python.org/pypi/pbs>`_) is a
full-fledged subprocess replacement for Python 2.6 - 3.4 that allows you
to call any program as if it were a function:

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

Then use `tox <http://tox.readthedocs.org/en/latest/index.html>`_ test
runner:

::

    $> tox

To run a single test for all environments:

::

    $> tox FunctionalTests.test_unicode_arg

To run a single test for a single environment:

::

    $> tox -e py34 FunctionalTests.test_unicode_arg
