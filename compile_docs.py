#!/usr/bin/env python

import sh
from os.path import abspath, join, dirname 
import logging
import sys


THIS_DIR = dirname(abspath(__file__))
DOCS_DIR = join(THIS_DIR, "_docs_sources")


if __name__ == "__main__":
    try: sh_version = sys.argv[1]
    except IndexError:
        print("ERROR: Please pass in the sh version to embed in the \
docs (ex: '1.12.0')")
        exit(1)
        
    with open(join(DOCS_DIR, "sh_version"), "w") as h:
        h.write(sh_version)
    
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("sh").setLevel(logging.ERROR)
    
    logging.info("compiling docs with sphinx")
    output = sh.make("html", _cwd=DOCS_DIR)
    logging.debug("sphinx output: \n%s", output)
    
    logging.info("cleaning up cruft")
    sh.rm(join(THIS_DIR, "objects.inv"))
    sh.rm(join(DOCS_DIR, "sh_version"))
    sh.rm(join(THIS_DIR, "doctrees"), "-rf")
