#!/usr/bin/python
import sh
import time
import sys

class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        print "Time taken: %s" % (self.end - self.start)

def debug(line):
    sys.stdout.write(line)

print "Original piping method:"
with Timer() as t:
    sh.dd(sh.dd("if=/dev/zero", "bs=1M", 'count=512', _piped="out", _err=debug), "of=/dev/null")

print "Direct piping method:"
with Timer() as t:
    sh.dd(sh.dd("if=/dev/zero", "bs=1M", 'count=512', _piped="direct", _err=debug), "of=/dev/null")


print 'done'
sys.exit()
