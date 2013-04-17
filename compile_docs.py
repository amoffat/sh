#!/usr/bin/env python

import sh
from os.path import abspath, join, dirname 
import logging

THIS_DIR = dirname(abspath(__file__))
DOCS_DIR = join(THIS_DIR, "_docs_sources")



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    logging.info("compiling docs with sphinx")
    output = sh.make("html", _cwd=DOCS_DIR)
    logging.debug("sphinx output: \n%s", output)
    
    logging.info("cleaning up cruft")
    sh.rm(join(THIS_DIR, "objects.inv"))
    sh.rm(join(THIS_DIR, "doctrees"), "-rf")
