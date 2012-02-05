#===============================================================================
# Copyright (C) 2011-2012 by Andrew Moffat
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#===============================================================================


"""PBS

PBS is a unique subprocess wrapper that maps your system programs to Python functions dynamically. 
PBS helps you write shell scripts in Python by giving you the good features of Bash (easy command 
calling, easy piping) with all the power and flexibility of Python.

Normally used as shown below

   from pbs import ifconfig
   ......
   print ifconfig("eth0")
   ......
"""

import inspect
import sys
import traceback
import os

from core import *

#--start constants--
__version__ = "0.90"
__project_url__ = "https://github.com/amoffat/pbs"
#--end constants--

frame, script, line, module, code, index = inspect.stack()[1]
env = Environment(frame.f_globals)

with open(script, "r") as h: source = h.readlines()
import_line = source[line-1]

# this it the most magical choice.  basically we're trying to import
# all of the system programs into our script.  the only way to do
# this is going to be to exec the source in modified global scope.
# there might be a less magical way to do this...
if "*" in import_line:
    # do not let us import * from anywhere but a stand-alone script
    if frame.f_globals["__name__"] != "__main__":
        raise RuntimeError("Do not do 'from pbs import *' \
from anywhere other than a stand-alone script.  Do a 'from pbs import program' instead.")
    
    # we avoid recursion by removing the line that imports us :)
    source.pop(line-1)
    source = "".join(source)
    
    exit_code = 0
    try: exec(source, env, env)
    except SystemExit as e: exit_code = e.code
    except: print(traceback.format_exc())

    # we exit so we don't actually run the script that we were imported from
    # (which would be running it "again", since we just executed the script
    # with exec
    exit(exit_code)

    # this is the least magical choice.  we're importing either a
    # selection of programs or we're just importing the pbs module.
    # in this case, let's just wrap ourselves with a module that has
    # __getattr__ so our program lookups can be done there
else:
    self = sys.modules[__name__]
    sys.modules[__name__] = SelfWrapper(self)

