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
        print "Time taken: %s\n" % (self.end - self.start)

def debug(line):
    sys.stdout.write(line)

print "These 2 times should be close to each other"

print "Nested sh calls with direct piping:"
with Timer() as t:
    sh.dd(sh.dd("if=/dev/zero", "bs=1M", 'count=5k', _piped=True), "of=/dev/null")

print "Execute straight in bash"    
with Timer() as t:
    sh.bash("-c", "dd if=/dev/zero bs=1M count=5k | dd of=/dev/null")

print 'done'
sys.exit()
