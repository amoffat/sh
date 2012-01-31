#===============================================================================
# Copyright (C) 2011 by Andrew Moffat
# Copyright (C) 2012 by Harshavardhana
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


# project page:
# https://github.com/amoffat/pbs

# project page: 
# https://github.com/harshavardhana/pbs

import sys
import re
import os

import shlex
import subprocess as subp
from glob import glob

if sys.version_info[0] >= 3:
    raw_input = input

class ErrorReturnCode(Exception):
    truncate_cap = 200

    def __init__(self, full_cmd, stdout, stderr):
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr

        tstdout = self.stdout[:self.truncate_cap]
        out_delta = len(self.stdout) - len(tstdout)
        if out_delta: tstdout += "... (%d more, please see e.stdout)" % out_delta

        tstderr = self.stderr[:self.truncate_cap]
        err_delta = len(self.stderr) - len(tstderr)
        if err_delta: tstderr += "... (%d more, please see e.stderr)" % err_delta

        msg = "\n\nRan: %r\n\nSTDOUT:\n\n  %s\nSTDERR:\n\n  %s" %\
            (full_cmd, tstdout, tstderr)
        super(ErrorReturnCode, self).__init__(msg)

class CommandNotFound(Exception): pass

class UnicodeMixin(object):

    """Mixin class to handle defining the proper __str__/__unicode__
    methods in Python 2 or 3."""

    if sys.version_info[0] >= 3: # Python 3
        def __str__(self):
            return self.__unicode__()
    else:  # Python 2
        def __str__(self):
            return self.__unicode__().encode('utf8')

class Command(UnicodeMixin):
    prepend_stack = []

    @classmethod
    def create(cls, program, raise_exc=True):
        path = Command.resolve_program(program)
        if not path:
            if raise_exc: raise CommandNotFound(program)
            else: return None
        return cls(path)

    def __init__(self, path):
        self.path = path


        self.process = None
        self._stdout = None
        self._stderr = None

        self.call_args = {
            "bg": False, # run command in background
            "with": False, # prepend the command to every command after it
        }

    def __getattr__(self, p):
        return getattr(self.stdout, p)

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

        if rc != 0: raise __get_rc_exc__(rc)(self.stdout, self.stderr)
        return self

    @classmethod
    def resolve_program(self, program):
        path = Command.which(program)
        if not path:
            # our actual command might have a dash in it, but we can't call
            # that from python (we have to use underscores), so we'll check
            # if a dash version of our underscore command exists and use that
            # if it does
            if "_" in program: path = Command.which(program.replace("_", "-"))
            if not path: return None
        return path

    @classmethod
    def is_exe(self, fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    @classmethod
    def which(self, program):
        fpath, fname = os.path.split(program)
        if fpath:
            if Command.is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if Command.is_exe(exe_file):
                    return exe_file
        return None

    def __repr__(self):
        return str(self)

    def __long__(self):
        return long(str(self).strip())

    def __float__(self):
        return float(str(self).strip())

    def __int__(self):
        return int(str(self).strip())

    def __unicode__(self):
        if self.process: return self.stdout.decode('utf-8') # byte string
        else: return self.path

    def __enter__(self):
        if not self.call_args["with"]:
            Command.prepend_stack.append([self.path])

    def __exit__(self, typ, value, traceback):
        if Command.prepend_stack:
            Command.prepend_stack.pop()

    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        args = list(args)
        stdin = None
        processed_args = []
        cmd = []

        # aggregate any with contexts
        for prepend in self.prepend_stack:
            cmd.extend(prepend)

        cmd.append(self.path)

        # pull out the pbs-specific arguments (arguments that are not to be
        # passed to the commands
        for parg, default in self.call_args.items():
            key = "_" + parg
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

        # now glob-expand each arg and compose the final list
        final_args = []
        for arg in split_args:
            expanded = glob(arg)
            if expanded: final_args.extend(expanded)
            else: final_args.append(arg)

        cmd.extend(final_args)
        # for debugging
        self._command_ran = " ".join(cmd)


        # with contexts shouldn't run at all yet, they prepend
        # to every command in the context
        if self.call_args["with"]:
            Command.prepend_stack.append(cmd)
            return self

        self.process = subp.Popen(self._command_ran, shell=True, env=os.environ,
            stdin=stdin, stdout=subp.PIPE, stderr=subp.PIPE)

        if self.call_args["bg"]: return self

        self._stdout, self._stderr = self.process.communicate(actual_stdin)
        rc = self.process.wait()

        if rc != 0: raise __get_rc_exc__(rc)(self._command_ran, self.stdout, self.stderr)
        return self


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
        self["rc_exc_regex"] = re.compile("ErrorReturnCode_(\d+)")
        self["rc_exc_cache"] = {}


    def __setitem__(self, k, v):
        # are we altering an environment variable?
        if "env" in self and k in self["env"]: self["env"][k] = v
        # no?  just setting a regular name
        else: dict.__setitem__(self, k, v)


    def __get_rc_exc__(rc):
        try: return self["rc_exc_cache"][rc]
        except KeyError: pass

        name = "ErrorReturnCode_%d" % rc
        exc = type(name, (ErrorReturnCode,), {})
        self["rc_exc_cache"][name] = exc
        return exc



    def __missing__(self, k):
        # if we end with "_" just go ahead and skip searching
        # our namespace for python stuff.  this was mainly for the
        # command "id", which is a popular program for finding
        # if a user exists, but also a python function for getting
        # the address of an object.  so can call the python
        # version by "id" and the program version with "id_"
        if not k.endswith("_"):
            # check if we're naming a dynamically generated ReturnCode exception
            try: return self["rc_exc_cache"][k]
            except KeyError:
                m = self["rc_exc_regex"].match(k)
                if m: return __get_rc_exc__(int(m.group(1)))

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


    def b_echo(self, *args, **kwargs):
        out = Command("echo")(*args, **kwargs)
        print(out)
        return out

    def b_cd(self, path):
        os.chdir(path)

    def b_which(self, program):
        return Command.which(program)


# this is a thin wrapper around THIS module (we patch sys.modules[__name__]).
# this is in the case that the user does a "from pbs import whatever"
# in other words, they only want to import certain programs, not the whole
# system PATH worth of commands.  in this case, we just proxy the
# import lookup to our Environment class
class SelfWrapper(object):
    def __init__(self, self_module):
        self.self_module = self_module
        self.env = Environment(globals())

    def __getattr__(self, name):
        return self.env[name]
