import sh
from os.path import abspath, join, dirname 
import os
import logging
import sys
import glob


THIS_DIR = dirname(abspath(__file__))
DOCS_DIR = join(THIS_DIR, "_docs_sources")
BUILD_DIR = join(DOCS_DIR, "build")


if __name__ == "__main__":
    version_file = join(DOCS_DIR, "sh_version")

    try:
        sh_version = sys.argv[1]
    except IndexError:
        pass
    else:
        with open(version_file, "r+") as version_h:
            version_h.write(sh_version)

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("sh").setLevel(logging.ERROR)

    clean = ["_sources", "_static", "_images", "tutorials", "sections", "examples"]
    clean.extend(glob.glob("*.js"))
    clean.extend(glob.glob("*.html"))
    for o in clean:
        sh.rm(join(THIS_DIR, o), "-rf")
    
    logging.info("compiling docs with sphinx")

    os.chdir(DOCS_DIR)
    sh.make("html", _fg=True)
    
    logging.info("cleaning up cruft")
    sh.rm(join(BUILD_DIR, "objects.inv"))
    sh.rm(join(BUILD_DIR, "doctrees"), "-rf")

    sh.mv(glob.glob(join(BUILD_DIR, "*")), THIS_DIR)
