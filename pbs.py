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
import socket
from glob import glob
import shlex



VERSION = "0.1"


class ErrorReturnCode(Exception):
    truncate_cap = 200

    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

        tstdout = self.stdout[:self.truncate_cap] 
        out_delta = len(self.stdout) - len(tstdout)
        if out_delta: tstdout += "... (%d more, please see e.stdout)" % out_delta

        tstderr = self.stderr[:self.truncate_cap]
        err_delta = len(self.stderr) - len(tstderr)
        if err_delta: tstderr += "... (%d more, please see e.stderr)" % err_delta

        msg = "\n\nSTDOUT:\n\n  %s\nSTDERR:\n\n  %s" % (tstdout, tstderr)
        super(ErrorReturnCode, self).__init__(msg)

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




def which(program):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program): return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def resolve_program(program):
    path = which(program)
    if not path:
        # our actual command might have a dash in it, but we can't call
        # that from python (we have to use underscores), so we'll check
        # if a dash version of our underscore command exists and use that
        # if it does
        if "_" in program: path = which(program.replace("_", "-"))        
        if not path: return None
    return path


class Command(object):
    @classmethod
    def create(cls, program, raise_exc=True):
        path = resolve_program(program)
        if not path:
            if raise_exc: raise CommandNotFound(program)
            else: return None
        return cls(path)
    
    def __init__(self, path):            
        self.path = path
        self.log = logging.getLogger(str(path))
        
        
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
        if self.call_args["bg"]: self.wait()
        return self._stdout
    
    @property
    def stderr(self):
        if self.call_args["bg"]: self.wait()
        return self._stderr
        
        
    def wait(self):
        if self.process.returncode is not None: return
        self._stdout, self._stderr = self.process.communicate()
        rc = self.process.wait()

        if self.stderr: self.log.error(self.stderr)
        if rc != 0: raise get_rc_exc(rc)(self.stdout, self.stderr)
    
    def __repr__(self):
        return str(self)

    def __long__(self):
        return long(str(self))

    def __float__(self):
        return float(str(self))

    def __int__(self):
        return int(str(self))
        
    def __str__(self):
        return unicode(self).encode('utf-8')
        
    def __unicode__(self):
        if self.process: return self.stdout
        else: return self.path


    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        args = list(args)
        stdin = None
        cmd = [self.path]
        
        # pull out the pbs-specific arguments (arguments that are not to be
        # passed to the commands
        for parg, default in self.call_args.iteritems():
            key = "pbs_" + parg
            self.call_args[parg] = default
            if key in kwargs:
                self.call_args[parg] = kwargs[key] 
                del kwargs[key]
                
        # check if we're piping via composition
        stdin = subp.PIPE
        actual_stdin = None
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, Command):
                # it makes sense that if the input pipe of a command is running
                # in the background, then this command should run in the
                # background as well
                if first_arg.call_args["bg"]:
                    self.call_args["bg"] = True
                    stdin = first_arg.process.stdout
                else:
                    actual_stdin = first_arg.stdout
            else: args.insert(0, first_arg)
        
        # aggregate the position arguments
        for arg in args:
            # i should've commented why i did this, because now i don't
            # remember.  for some reason, some command was more natural
            # taking a list?
            if isinstance(arg, (list, tuple)):
                for sub_arg in arg: cmd.extend(shlex.split(str(a)))
            else: cmd.extend(shlex.split(str(arg)))


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
            stdin=stdin, stdout=subp.PIPE, stderr=subp.PIPE)

        if self.call_args["bg"]: return self
        
        self._stdout, self._stderr = self.process.communicate(actual_stdin)
        rc = self.process.wait()

        if self.stderr: self.log.error(self.stderr)
        if rc != 0: raise get_rc_exc(rc)(self.stdout, self.stderr)
        return self






class Environment(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        
        self["Command"] = Command
        self["CommandNotFound"] = CommandNotFound
        self["ErrorReturnCode"] = ErrorReturnCode
        self["glob"] = glob
        self["argv"] = sys.argv[1:]
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
        
        # is it a custom builtin?
        builtin = getattr(self, "b_"+k, None)
        if builtin: return builtin
        
        # it must be a command then
        return Command.create(k)
    
    
    def b_echo(self, *args, **kwargs):
        out = Command("echo")(*args, **kwargs)
        print out
        return out
    
    def b_cd(self, path):
        os.chdir(path)
        
    def b_which(self, program):
        return Command.create(program, raise_exc=False)





def run_repl(env):
    banner = "\n>> PBS v{version}\n>> https://github.com/amoffat/pbs\n"
    
    print banner.format(version=VERSION)
    while True:
        try: line = raw_input("pbs> ")
        except (ValueError, EOFError): break
            
        try: exec compile(line, "<dummy>", "single") in env, env
        except SystemExit: break
        except: print traceback.format_exc()

    # cleans up our last line
    print



# we're being run as a stand-alone script, fire up a REPL
if __name__ == "__main__":
    globs = globals()
    f_globals = {}
    for k in ["__builtins__", "__doc__", "__name__", "__package__"]:
        f_globals[k] = globs[k]
    env = Environment(f_globals)
    run_repl(env)
    
# we're bein imported from somewhere
else:
    frame, script, line, module, code, index = inspect.stack()[1]
    env = Environment(frame.f_globals)
    
    logging.basicConfig(
        level=logging.DEBUG if env.get("debug", False) else logging.INFO,
        format="(%(process)d) %(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # are we being imported from a REPL? start our REPL
    if script == "<stdin>":
        run_repl(env)
        
    # we're being imported from a script
    else:
        exit_code = 0
        
        # we avoid recursion by removing the line that imports us :)
        with open(script, "r") as h: source = h.readlines()
        source.pop(line-1)
        source = "".join(source)
    
        try: exec source in env, env
        except SystemExit, e: exit_code = e.code
        except: print traceback.format_exc()

        # we exit so we don't actually run the script that we were imported from
        # (which would be running it "again", since we just executed the script
        # with exec
        exit(exit_code)
