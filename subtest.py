import oproc
import time
import os
import threading
import pbs
from Queue import Queue

def test(line):
    print repr(line)
    pass


p = pbs.tr(pbs.ls("-l"), "[:lower:]", "[:upper:]", _bufsize=1, _out=test)
p.wait()