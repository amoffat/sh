#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Yafei Zhang(zhangyafeikimi@gmail.com)
#
# Run it before: ulimit -n 5000
#

import os
import sh

pipes = []
for i in xrange(1000):
    pipes.append(os.pipe())

# Make sure sh works fine when too many files are opened.
print(sh.ls('.'))
