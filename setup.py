from __future__ import print_function
import os
from os.path import dirname, abspath, join
import sys
import sh
import codecs
from setuptools import setup


HERE = dirname(abspath(__file__))

author = "Andrew Moffat"
author_email = "andrew.robert.moffat@gmail.com"
keywords = ["subprocess", "process", "shell", "launch", "program"]


def read(*parts):
    with codecs.open(join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()

setup(
    name="sh",
    version=sh.__version__,
    description="Python subprocess replacement",
    long_description=read("README.rst"),
    author=author,
    author_email=author_email,
    maintainer=author,
    maintainer_email=author_email,
    keywords=keywords,
    url="https://github.com/amoffat/sh",
    license="MIT",
    py_modules=["sh"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
