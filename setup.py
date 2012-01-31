try: from distutils.core import setup
except ImportError: from setuptools import setup

setup(
    name="pbs",
    version="0.6",
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
