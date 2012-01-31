#!/usr/bin/python

from pbs import *

# sort this directory by biggest file
print sort(du("*", "-sb"), "-rn")

# print the number of folders and files in /etc
print wc(ls("/etc", "-1"), "-l")
