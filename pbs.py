#===============================================================================
# Copyright (C) 2011 by Andrew Moffat
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


from collections import defaultdict as dd
import subprocess as subp
import inspect
import sys
import traceback
import os
import re
import logging






class ErrorReturnCode(Exception): pass
class CommandException(Exception): pass
class CommandNotFound(Exception): pass

rc_exc_regex = re.compile("ErrorReturnCode_(\d+)")
rc_exc_cache = {}

def get_rc_exc(rc):
    try: return rc_exc_cache[rc]
    except KeyError: pass
    
    name = "ErrorReturnCode_%d" % rc
    exc = type(name, (ErrorReturnCode,), {})
    rc_exc_cache[name] = exc
    return exc





class Command(object):
    def __init__(self, name):
        self.path = Environment.which(name)
        if not self.path:
            # our actual command might have a dash in it, but we can't call
            # that from python (we have to use underscores), so we'll check
            # if a dash version of our underscore command exists and use that
            # if it does
            if "_" in name:
                name = name.replace("_", "-") 
                self.path = Environment.which(name)
            if not self.path:
                raise CommandNotFound, name
            
        self.name = name
        self.log = logging.getLogger(str(self.path))
        
        self.process = None
        self._stdout = None
        self._stderr = None
        
        self.call_args = {
            "bg": False, # run command in background
        }
        
        
    def _reader_thread(self, fd, buffer):
        buffer.append(fd.read())
        
    @property
    def stdout(self):
        if self.call_args["bg"]:
            self.process.wait()
            return self.process.stdout.read()
        else: return self._stdout
    
    @property
    def stderr(self):
        if self.call_args["bg"]:
            self.process.wait()
            return self.process.stderr.read()
        else: return self._stderr
    
        
    def __str__(self):
        return unicode(self).encode('utf-8')
        
    def __unicode__(self):
        if self.process: return self.stdout
        else: return self.path


    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        args = list(args)
        stdin = None
        cmd = [self.name]
        
        # pull out the pbs-specific arguments (arguments that are not to be
        # passed to the commands
        for parg, default in self.call_args.iteritems():
            key = "pbs_" + parg
            self.call_args[parg] = default
            if key in kwargs:
                self.call_args[parg] = kwargs[key] 
                del kwargs[key]
                
        # check if we're piping via composition
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, Command): stdin = first_arg.stdout
            else: args.insert(0, first_arg)
        
        # aggregate the position arguments
        cmd.extend([str(a) for a in args])

        # aggregate the keyword arguments
        for k,v in kwargs.iteritems():
            k = k.replace("_", "-")
            # we have to do the "and not in" test because isinstance(True, int)
            # returns True!?
            if isinstance(v, (int, float, basestring)) and v not in (True, False): arg = "--%s=%s" % (k, v)
            else: arg = "--" + k
            cmd.append(arg)

        self.log.debug("running %r", " ".join(cmd))
        
        
        
        self.process = subp.Popen(cmd, shell=False, env=os.environ,
            stdin=subp.PIPE, stdout=subp.PIPE, stderr=subp.PIPE)
    
        if self.call_args["bg"]:
            return self.process
        else:
            self._stdout, self._stderr = self.process.communicate(stdin)
            rc = self.process.wait()

        if self.stderr: self.log.error(self.stderr)
        if rc != 0: raise get_rc_exc(rc)(self.stdout, self.stderr)
        return self



class Environment(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        
        self["ErrorReturnCode"] = ErrorReturnCode
        self["argv"] = sys.argv
        for i, arg in enumerate(sys.argv):
            self["ARG%d" % i] = arg
        
        # this needs to be last
        self["env"] = os.environ
        self.log = logging.getLogger("environment")
        
    def __setitem__(self, k, v):
        # are we altering an environment variable?
        if "env" in self and k in self["env"]: self["env"][k] = v
        # no?  just setting a regular name
        else: dict.__setitem__(self, k, v)
        
    def __missing__(self, k):
        # check if we're naming a dynamically generated ReturnCode exception
        try: return rc_exc_cache[k]
        except KeyError:
            m = rc_exc_regex.match(k)
            if m: return get_rc_exc(int(m.group(1)))
            
        # are we naming a commandline argument?
        if k.startswith("ARG"):
            self.log.error("%s not found", k)
            return None
            
        # is it a builtin?
        try: return getattr(self["__builtins__"], k)
        except AttributeError: pass
        
        # how about an environment variable?
        try: return os.environ[k]
        except KeyError: pass
        
        # it must be a command then
        builtin = getattr(self, "b_"+k, None)
        if builtin: return builtin
        return Command(k)
    
    def b_echo(self, *args, **kwargs):
        out = Command("echo")(*args, **kwargs)
        print out
        return out
    
    def b_cd(self, path):
        os.chdir(path)
        
    def b_which(self, program):
        return Command(Environment.which(program))
        
    @staticmethod
    def which(program):
        def is_exe(fpath):
            return os.path.exists(fpath) and os.access(fpath, os.X_OK)
    
        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
    
        return None




frame, script, line, module, code, index = inspect.stack()[1]
f_globals = frame.f_globals

logging.basicConfig(
    level=logging.DEBUG if f_globals.get("debug", True) else logging.INFO,
    format="(%(process)d) %(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# we avoid recursion by removing the line that imports us :)
with open(script, "r") as h: code = h.readlines()
code.pop(line-1)
code = "".join(code)


env = Environment(f_globals)
env.update(f_globals)

exit_code = 0
try: exec code in env, env
except SystemExit, e: exit_code = e.code
except: print traceback.format_exc()

# we exit so we don't actually run the script that we were imported from
# (which would be running it "again", since we just executed the script with
# exec
exit(exit_code)
