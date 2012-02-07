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



import subprocess as subp
import sys
import traceback
import os
import re
from glob import glob
import shlex
from types import ModuleType
from functools import partial



__version__ = "0.91"
__project_url__ = "https://github.com/amoffat/pbs"

IS_PY3 = sys.version_info[0] == 3
if IS_PY3: raw_input = input




class ErrorReturnCode(Exception):
    truncate_cap = 200

    def __init__(self, full_cmd, stdout, stderr):
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr

        if self.stdout is None: tstdout = "<redirected>"
        else:
            tstdout = self.stdout[:self.truncate_cap] 
            out_delta = len(self.stdout) - len(tstdout)
            if out_delta: 
                tstdout += "... (%d more, please see e.stdout)" % out_delta
            
        if self.stderr is None: tstderr = "<redirected>"
        else:
            tstderr = self.stderr[:self.truncate_cap]
            err_delta = len(self.stderr) - len(tstderr)
            if err_delta: 
                tstderr += "... (%d more, please see e.stderr)" % err_delta

        msg = "\n\nRan: %r\n\nSTDOUT:\n\n  %s\n\nSTDERR:\n\n  %s" %\
            (full_cmd, tstdout, tstderr)
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



class RunningCommand(object):
    def __init__(self, command_ran, process, call_args, stdin=None):
        self.command_ran = command_ran
        self.process = process
        self._stdout = None
        self._stderr = None
        self.call_args = call_args

        # we're running in the background, return self and let us lazily
        # evaluate
        if self.call_args["bg"]: return

        # we're running this command as a with context, don't do anything
        # because nothing was started to run from Command.__call__
        if self.call_args["with"]: return

        # run and block
        self._stdout, self._stderr = self.process.communicate(stdin)
        rc = self.process.wait()

        if rc != 0: raise get_rc_exc(rc)(self.command_ran, self._stdout, self._stderr)

    def __enter__(self):
        # we don't actually do anything here because anything that should
        # have been done would have been done in the Command.__call__ call.
        # essentially all that has to happen is the comand be pushed on
        # the prepend stack.
        pass

    def __exit__(self, typ, value, traceback):
        if self.call_args["with"] and Command.prepend_stack:
            Command.prepend_stack.pop()
   
    def __str__(self):
        if IS_PY3: return self.__unicode__()
        else: return unicode(self).encode("utf-8")
        
    def __unicode__(self):
        if self.process: 
            if self.stdout: return self.stdout.decode("utf-8") # byte string
            else: return ""

    def __eq__(self, other):
        return str(self) == str(other)

    def __contains__(self, item):
        return item in str(self)

    def __getattr__(self, p):
        return getattr(str(self), p)
     
    def __repr__(self):
        return str(self)

    def __long__(self):
        return long(str(self).strip())

    def __float__(self):
        return float(str(self).strip())

    def __int__(self):
        return int(str(self).strip())
         
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

        if rc != 0: raise get_rc_exc(rc)(self.stdout, self.stderr)
        return self
    
    def __len__(self):
        return len(str(self))



class Command(object):
    prepend_stack = []

    def bake(self, *args, **kwargs):
        fn = Command(self.path)
        fn._partial = True
        fn._partial_args = list(args)
        fn._partial_kwargs = kwargs
        return fn

    @classmethod
    def create(cls, program):
        path = resolve_program(program)
        if not path:
            if raise_exc: raise CommandNotFound(program)
            else: return None
        return cls(path)

    def __getattr__(self, name):
        if self._partial: return partial(self, name)
        raise AttributeError
    
    def __init__(self, path):            
        self.path = path
        self._partial = False
        self._partial_args = []
        self._partial_kwargs = {}
       
    def __str__(self):
        if IS_PY3: return self.__unicode__()
        else: return unicode(self).encode("utf-8")

    def __repr__(self):
        return str(self)
        
    def __unicode__(self):
        return self.path

    def __enter__(self):
        Command.prepend_stack.append([self.path])

    def __exit__(self, typ, value, traceback):
        Command.prepend_stack.pop()

    
    def __call__(self, *args, **kwargs):
        call_args = {
            "fg": False, # run command in foreground
            "bg": False, # run command in background
            "with": False, # prepend the command to every command after it
            "out": None, # redirect STDOUT
            "err": None, # redirect STDERR
            "err_to_out": None, # redirect STDERR to STDOUT
        }
     
        kwargs = kwargs.copy()
        args = list(args)

        kwargs.update(self._partial_kwargs)
        args = self._partial_args + args

        processed_args = []
        cmd = []

        # aggregate any with contexts
        for prepend in self.prepend_stack: cmd.extend(prepend)

        cmd.append(self.path)
        
        # pull out the pbs-specific arguments (arguments that are not to be
        # passed to the commands
        for parg, default in call_args.items():
            key = "_" + parg
            call_args[parg] = default
            if key in kwargs:
                call_args[parg] = kwargs[key] 
                del kwargs[key]
                
        # set pipe to None if we're outputting straight to CLI
        pipe = None if call_args["fg"] else subp.PIPE
        
        # check if we're piping via composition
        stdin = pipe
        actual_stdin = None
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, RunningCommand):
                # it makes sense that if the input pipe of a command is running
                # in the background, then this command should run in the
                # background as well
                if first_arg.call_args["bg"]:
                    call_args["bg"] = True
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
                for sub_arg in arg: processed_args.append(str(sub_arg))
            else: processed_args.append(str(arg))


        # aggregate the keyword arguments
        for k,v in kwargs.items():
            # we're passing a short arg as a kwarg, example:
            # cut(d="\t")
            if len(k) == 1:
                if v is True: arg = "-"+k
                else: arg = "-%s %r" % (k, v)

            # we're doing a long arg
            else:
                k = k.replace("_", "-")

                if v is True: arg = "--"+k
                else: arg = "--%s=%s" % (k, v)
            processed_args.append(arg)

        # makes sure our arguments are broken up correctly
        split_args = shlex.split(" ".join(processed_args))

        # we used to glob, but now we don't.  the reason being, escaping globs
        # doesn't work.  also, adding a _noglob attribute doesn't allow the
        # flexibility to glob some args and not others.  so we have to leave
        # the globbing up to the user entirely
        #=======================================================================
        # # now glob-expand each arg and compose the final list
        # final_args = []
        # for arg in split_args:
        #    expanded = glob(arg)
        #    if expanded: final_args.extend(expanded)
        #    else: final_args.append(arg)
        #=======================================================================
        final_args = split_args

        cmd.extend(final_args)
        command_ran = " ".join(cmd)


        # with contexts shouldn't run at all yet, they prepend
        # to every command in the context
        if call_args["with"]:
            Command.prepend_stack.append(cmd)
            return RunningCommand(command_ran, None, call_args)
        
        
        # stdout redirection
        stdout = pipe
        out = call_args["out"]
        if out:
            if isinstance(out, file): stdout = out
            else: stdout = file(str(out), "w")
        
        # stderr redirection
        stderr = pipe
        err = call_args["err"]
        if err:
            if isinstance(err, file): stderr = err
            else: stderr = file(str(err), "w")
            
        if call_args["err_to_out"]: stderr = subp.STDOUT
            
        # leave shell=False
        process = subp.Popen(cmd, shell=False, env=os.environ,
            stdin=stdin, stdout=stdout, stderr=stderr)

        return RunningCommand(command_ran, process, call_args, actual_stdin)







# this class is used directly when we do a "from pbs import *".  it allows
# lookups to names that aren't found in the global scope to be searched
# for as a program.  for example, if "ls" isn't found in the program's
# scope, we consider it a system program and try to find it.
class Environment(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        
        self["Command"] = Command
        self["CommandNotFound"] = CommandNotFound
        self["ErrorReturnCode"] = ErrorReturnCode
        self["ARGV"] = sys.argv[1:]
        for i, arg in enumerate(sys.argv):
            self["ARG%d" % i] = arg
        
        # this needs to be last
        self["env"] = os.environ
        
    def __setitem__(self, k, v):
        # are we altering an environment variable?
        if "env" in self and k in self["env"]: self["env"][k] = v
        # no?  just setting a regular name
        else: dict.__setitem__(self, k, v)
        
    def __missing__(self, k):
        # the only way we'd get to here is if we've tried to
        # import * from a repl.  so, raise an exception, since
        # that's really the only sensible thing to do
        if k == "__all__":
            raise ImportError("Cannot import * from pbs. \
Please import pbs or import programs individually.")

        # if we end with "_" just go ahead and skip searching
        # our namespace for python stuff.  this was mainly for the
        # command "id", which is a popular program for finding
        # if a user exists, but also a python function for getting
        # the address of an object.  so can call the python
        # version by "id" and the program version with "id_"
        if not k.endswith("_"):
            # check if we're naming a dynamically generated ReturnCode exception
            try: return rc_exc_cache[k]
            except KeyError:
                m = rc_exc_regex.match(k)
                if m: return get_rc_exc(int(m.group(1)))
                
            # are we naming a commandline argument?
            if k.startswith("ARG"):
                return None
                
            # is it a builtin?
            try: return getattr(self["__builtins__"], k)
            except AttributeError: pass
        elif not k.startswith("_"): k = k.rstrip("_")
        
        # how about an environment variable?
        try: return os.environ[k]
        except KeyError: pass
        
        # is it a custom builtin?
        builtin = getattr(self, "b_"+k, None)
        if builtin: return builtin
        
        # it must be a command then
        return Command.create(k)
    
    def b_cd(self, path):
        os.chdir(path)
        
    def b_which(self, program):
        return which(program)





def run_repl(env):
    banner = "\n>> PBS v{version}\n>> https://github.com/amoffat/pbs\n"
    
    print(banner.format(version=__version__))
    while True:
        try: line = raw_input("pbs> ")
        except (ValueError, EOFError): break
            
        try: exec(compile(line, "<dummy>", "single"), env, env)
        except SystemExit: break
        except: print(traceback.format_exc())

    # cleans up our last line
    print("")




# this is a thin wrapper around THIS module (we patch sys.modules[__name__]).
# this is in the case that the user does a "from pbs import whatever"
# in other words, they only want to import certain programs, not the whole
# system PATH worth of commands.  in this case, we just proxy the
# import lookup to our Environment class
class SelfWrapper(ModuleType):
    def __init__(self, self_module):
        # this is super ugly to have to copy attributes like this,
        # but it seems to be the only way to make reload() behave
        # nicely.  if i make these attributes dynamic lookups in
        # __getattr__, reload sometimes chokes in weird ways...
        for attr in ["__builtins__", "__doc__", "__name__", "__package__"]:
            setattr(self, attr, getattr(self_module, attr))

        self.self_module = self_module
        self.env = Environment(globals())
    
    def __getattr__(self, name):
        return self.env[name]





# we're being run as a stand-alone script, fire up a REPL
if __name__ == "__main__":
    globs = globals()
    f_globals = {}
    for k in ["__builtins__", "__doc__", "__name__", "__package__"]:
        f_globals[k] = globs[k]
    env = Environment(f_globals)
    run_repl(env)
    
# we're being imported from somewhere
else:
    self = sys.modules[__name__]
    sys.modules[__name__] = SelfWrapper(self)
