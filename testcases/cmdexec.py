#!/usr/bin/python

from pbs import *

# print the contents of this directory 
print ls("-l")

# get the longest line of this file
longest_line = wc(__file__, "-L")

# get interface information
print ifconfig("eth0")
