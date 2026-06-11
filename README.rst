.. image:: https://raw.githubusercontent.com/amoffat/sh/master/images/logo-230.png
    :target: https://amoffat.github.com/sh
    :alt: Logo

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

|

sh is a full-fledged subprocess replacement for Python 3.8 - 3.14, and PyPy
that allows you to call *any* program as if it were a function:

.. code:: python

    from sh import git
    print(git("status", "--short"))

sh is *not* a collection of system commands implemented in Python.

sh relies on various Unix system calls and only works on Unix-like operating
systems - Linux, macOS, BSDs etc. Specifically, Windows is not supported.

`Complete documentation here <https://sh.readthedocs.io/>`_

`Full documentation on a single page for LLM-assisted coding here <https://sh.readthedocs.io/en/latest/fulldoc.html>`_

Installation
============

::

    $> pip install sh

Support
=======
* `Andrew Moffat <https://github.com/amoffat>`_ - author/maintainer

Developers
==========

Open the repo in a devcontainer in VScode, or in a codespace on Github.

.. image:: https://github.com/codespaces/badge.svg
   :target: https://codespaces.new/amoffat/sh
   :alt: Open in GitHub Codespaces

Testing
-------

Tests are run by tox against all supported Python versions. To run, make the following target::

    $> make test

To run a single test::

    $> make test='FunctionalTests.test_background' test_one

Docs
----

To build the docs, make sure you've run ``poetry install`` to install the dev dependencies, then::

    $> cd docs
    $> make html

This will generate the docs in ``docs/build/html``. You can open the ``index.html`` file in your browser to view the docs.

Coverage
--------

First run all of the tests::

    $> SH_TESTS_RUNNING=1 coverage run --source=sh -m pytest

This will aggregate a ``.coverage``.  You may then visualize the report with::

    $> coverage report

Or generate visual html files with::

    $> coverage html

Which will create ``./htmlcov/index.html`` that you may open in a web browser.
