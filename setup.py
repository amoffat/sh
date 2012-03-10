import os
import sys
import pbs
import subprocess

try: from distutils.core import setup
except ImportError: from setuptools import setup


if sys.argv[1] == "test":
    def run_test(version):
        py_version = "python%s" % version
        py_bin = pbs.which(py_version)
        
        if py_bin:
            print("Testing %s" % py_version.capitalize())
            
            p = subprocess.Popen([py_bin, "test.py"] + sys.argv[2:])
            p.wait()
        else:
            print("Couldn't find %s, skipping" % py_version.capitalize())
    
    versions = ("2.6", "2.7", "3", "3.1", "3.2")
    
    for version in versions:
        run_test(version)
        
    exit(0)
    

setup(
    name="pbs",
    version=pbs.__version__,
    description="Python subprocess wrapper",
    author="Andrew Moffat",
    author_email="andrew.robert.moffat@gmail.com",
    url="https://github.com/amoffat/pbs",
    license="MIT",
    py_modules=["pbs"],
    classifiers=[
        "Development Status :: 3 - Alpha",
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
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
