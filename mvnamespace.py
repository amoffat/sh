#!/usr/bin/env python
""" mvnamespace.py -- Rename the pbs module to 'sh'.

Use this script for releases.  So that http://pypi.python.org/pypi/sh can stay
in sync with http://pypi.python.org/pypi/pbs.

See the discussion in https://github.com/amoffat/pbs/issues/28 for more
information.
"""

import os

TARGET_DIR = os.path.abspath('sh')
file_mapping = {
    "pbs.py": "%s/sh.py" % TARGET_DIR,
    "test.py": "%s/test.py" % TARGET_DIR,
    "setup.py": "%s/setup.py" % TARGET_DIR,
    "README.md": "%s/README.md" % TARGET_DIR,
    "AUTHORS.md": "%s/AUTHORS.md" % TARGET_DIR,
    "LICENSE.txt": "%s/LICENSE.txt" % TARGET_DIR,
    "MANIFEST.in": "%s/MANIFEST.in" % TARGET_DIR,
}


def replace(content):
    return content\
            .replace('pbs', 'sh')\
            .replace('PBS ', '``sh`` ')


def main():
    if os.path.exists(TARGET_DIR):
        raise IOError("Target %r already exists.  Aborting." % TARGET_DIR)

    os.mkdir(TARGET_DIR)

    for frm, to in file_mapping.items():
        with open(frm, 'r') as from_file:
            with open(to, 'w') as to_file:
                print "Writing %r" % to
                to_file.write(replace(from_file.read()))


if __name__ == '__main__':
    main()
