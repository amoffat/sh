from __future__ import print_function
import os
import sys
import sh

try: from distutils.core import setup
except ImportError: from setuptools import setup


setup(
    name="sh",
    version=sh.__version__,
    description="Python subprocess interface",
    author="Andrew Moffat",
    author_email="andrew.robert.moffat@gmail.com",
    url="https://github.com/amoffat/sh",
    license="MIT",
    py_modules=["sh"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
