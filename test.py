# -*- coding: utf8 -*-

import os
from os.path import exists, join, realpath
import unittest
import tempfile
import sys
import sh
import platform
from functools import wraps

# we have to use the real path because on osx, /tmp is a symlink to
# /private/tmp, and so assertions that gettempdir() == sh.pwd() will fail
tempdir = realpath(tempfile.gettempdir())
IS_OSX = platform.system() == "Darwin"
IS_PY3 = sys.version_info[0] == 3
if IS_PY3:
    unicode = str
    python = sh.Command(sh.which("python%d.%d" % sys.version_info[:2]))
else:
    from sh import python


THIS_DIR = os.path.dirname(os.path.abspath(__file__))

skipUnless = getattr(unittest, "skipUnless", None)
if not skipUnless:
    # our stupid skipUnless wrapper for python2.6
    def skipUnless(condition, reason):
        def wrapper(test):
            if condition:
                return test
            else:
                @wraps(test)
                def skip(*args, **kwargs):
                    return
                return skip
        return wrapper

requires_posix = skipUnless(os.name == "posix", "Requires POSIX")
requires_utf8 = skipUnless(sh.DEFAULT_ENCODING == "UTF-8", "System encoding must be UTF-8")


def create_tmp_test(code, prefix="tmp", delete=True):
    """ creates a temporary test file that lives on disk, on which we can run
    python with sh """

    py = tempfile.NamedTemporaryFile(prefix=prefix, delete=delete)
    if IS_PY3:
        code = bytes(code, "UTF-8")
    py.write(code)
    py.flush()
    # we don't explicitly close, because close will remove the file, and we
    # don't want that until the test case is done.  so we let the gc close it
    # when it goes out of scope
    return py



@requires_posix
class FunctionalTests(unittest.TestCase):

    def test_print_command(self):
        from sh import ls, which
        actual_location = which("ls")
        out = str(ls)
        self.assertEqual(out, actual_location)


    def test_unicode_arg(self):
        from sh import echo

        test = "漢字"
        if not IS_PY3:
            test = test.decode("utf8")

        p = echo(test, _encoding="utf8")
        output = p.strip()
        self.assertEqual(test, output)


    def test_number_arg(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()
print(args[0])
""")

        out = python(py.name, 3).strip()
        self.assertEqual(out, "3")


    def test_exit_code(self):
        from sh import ErrorReturnCode
        py = create_tmp_test("""
exit(3)
""")

        self.assertRaises(ErrorReturnCode, python, py.name)


    def test_exit_code_with_hasattr(self):
        from sh import ErrorReturnCode
        py = create_tmp_test("""
exit(3)
""")

        try:
            out = python(py.name, _iter=True)
            # hasattr can swallow exceptions
            hasattr(out, 'something_not_there')
            list(out)
            self.assertEqual(out.exit_code, 3)
            self.fail("Command exited with error, but no exception thrown")
        except ErrorReturnCode as e:
            pass


    def test_exit_code_from_exception(self):
        from sh import ErrorReturnCode
        py = create_tmp_test("""
exit(3)
""")

        self.assertRaises(ErrorReturnCode, python, py.name)

        try:
            python(py.name)
        except Exception as e:
            self.assertEqual(e.exit_code, 3)


    def test_glob_warning(self):
        from sh import ls
        from glob import glob
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            ls(glob("ofjaoweijfaowe"))

            self.assertTrue(len(w) == 1)
            self.assertTrue(issubclass(w[-1].category, UserWarning))
            self.assertTrue("glob" in str(w[-1].message))

    def test_stdin_from_string(self):
        from sh import sed
        self.assertEqual(sed(_in="one test three", e="s/test/two/").strip(),
                "one two three")

    def test_ok_code(self):
        from sh import ls, ErrorReturnCode_1, ErrorReturnCode_2

        exc_to_test = ErrorReturnCode_2
        code_to_pass = 2
        if IS_OSX:
            exc_to_test = ErrorReturnCode_1
            code_to_pass = 1
        self.assertRaises(exc_to_test, ls, "/aofwje/garogjao4a/eoan3on")

        ls("/aofwje/garogjao4a/eoan3on", _ok_code=code_to_pass)
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=[code_to_pass])
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=range(code_to_pass + 1))

    def test_quote_escaping(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()
print(args)
""")
        out = python(py.name, "one two three").strip()
        self.assertEqual(out, "['one two three']")

        out = python(py.name, "one \"two three").strip()
        self.assertEqual(out, "['one \"two three']")

        out = python(py.name, "one", "two three").strip()
        self.assertEqual(out, "['one', 'two three']")

        out = python(py.name, "one", "two \"haha\" three").strip()
        self.assertEqual(out, "['one', 'two \"haha\" three']")

        out = python(py.name, "one two's three").strip()
        self.assertEqual(out, "[\"one two's three\"]")

        out = python(py.name, 'one two\'s three').strip()
        self.assertEqual(out, "[\"one two's three\"]")

    def test_multiple_pipes(self):
        from sh import tr, python
        import time

        py = create_tmp_test("""
import sys
import os
import time

for l in "andrew":
    print(l)
    time.sleep(.2)
""")

        class Derp(object):
            def __init__(self):
                self.times = []
                self.stdout = []
                self.last_received = None

            def agg(self, line):
                self.stdout.append(line.strip())
                now = time.time()
                if self.last_received: self.times.append(now - self.last_received)
                self.last_received = now

        derp = Derp()

        p = tr(
               tr(
                  tr(
                     python(py.name, _piped=True),
                  "aw", "wa", _piped=True),
               "ne", "en", _piped=True),
            "dr", "rd", _out=derp.agg)

        p.wait()
        self.assertEqual("".join(derp.stdout), "werdna")
        self.assertTrue(all([t > .15 for t in derp.times]))


    def test_manual_stdin_string(self):
        from sh import tr

        out = tr("[:lower:]", "[:upper:]", _in="andrew").strip()
        self.assertEqual(out, "ANDREW")

    def test_manual_stdin_iterable(self):
        from sh import tr

        test = ["testing\n", "herp\n", "derp\n"]
        out = tr("[:lower:]", "[:upper:]", _in=test)

        match = "".join([t.upper() for t in test])
        self.assertEqual(out, match)


    def test_manual_stdin_file(self):
        from sh import tr
        import tempfile

        test_string = "testing\nherp\nderp\n"

        stdin = tempfile.NamedTemporaryFile()
        stdin.write(test_string.encode())
        stdin.flush()
        stdin.seek(0)

        out = tr("[:lower:]", "[:upper:]", _in=stdin)

        self.assertEqual(out, test_string.upper())


    def test_manual_stdin_queue(self):
        from sh import tr
        try: from Queue import Queue, Empty
        except ImportError: from queue import Queue, Empty

        test = ["testing\n", "herp\n", "derp\n"]

        q = Queue()
        for t in test: q.put(t)
        q.put(None) # EOF

        out = tr("[:lower:]", "[:upper:]", _in=q)

        match = "".join([t.upper() for t in test])
        self.assertEqual(out, match)


    def test_environment(self):
        """ tests that environments variables that we pass into sh commands
        exist in the environment, and on the sh module """
        import os

        # this is the environment we'll pass into our commands
        env = {"HERP": "DERP"}

        # python on osx will bizarrely add some extra environment variables that
        # i didn't ask for.  for this test, we prune those out if they exist
        osx_cruft = [
            "__CF_USER_TEXT_ENCODING",
            "__PYVENV_LAUNCHER__",
            "VERSIONER_PYTHON_PREFER_32_BIT",
            "VERSIONER_PYTHON_VERSION",
        ]

        # first we test that the environment exists in our child process as
        # we've set it
        py = create_tmp_test("""
import os

osx_cruft = %s
for key in osx_cruft:
    try: del os.environ[key]
    except: pass
print(os.environ["HERP"] + " " + str(len(os.environ)))
""" % osx_cruft)
        out = python(py.name, _env=env).strip()
        self.assertEqual(out, "DERP 1")

        py = create_tmp_test("""
import os, sys
sys.path.insert(0, os.getcwd())
import sh
osx_cruft = %s
for key in osx_cruft:
    try: del os.environ[key]
    except: pass
print(sh.HERP + " " + str(len(os.environ)))
""" % osx_cruft)
        out = python(py.name, _env=env, _cwd=THIS_DIR).strip()
        self.assertEqual(out, "DERP 1")


    def test_which(self):
        from sh import which, ls
        self.assertEqual(which("fjoawjefojawe"), None)
        self.assertEqual(which("ls"), str(ls))


    def test_foreground(self):
        return
        raise NotImplementedError

    def test_no_arg(self):
        import pwd
        from sh import whoami
        u1 = whoami().strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)

    def test_incompatible_special_args(self):
        from sh import ls
        self.assertRaises(TypeError, ls, _iter=True, _piped=True)


    def test_exception(self):
        from sh import ls, ErrorReturnCode_1, ErrorReturnCode_2

        exc_to_test = ErrorReturnCode_2
        if IS_OSX: exc_to_test = ErrorReturnCode_1
        self.assertRaises(exc_to_test, ls, "/aofwje/garogjao4a/eoan3on")


    def test_command_not_found(self):
        from sh import CommandNotFound

        def do_import(): from sh import aowjgoawjoeijaowjellll
        self.assertRaises(ImportError, do_import)

        def do_import():
            import sh
            sh.awoefaowejfw
        self.assertRaises(CommandNotFound, do_import)

        def do_import():
            import sh
            sh.Command("ofajweofjawoe")
        self.assertRaises(CommandNotFound, do_import)


    def test_command_wrapper_equivalence(self):
        from sh import Command, ls, which

        self.assertEqual(Command(which("ls")), ls)

    def test_doesnt_execute_directories(self):
        save_path = os.environ['PATH']
        bin_dir1 = tempfile.mkdtemp()
        bin_dir2 = tempfile.mkdtemp()
        gcc_dir1 = os.path.join(bin_dir1, 'gcc')
        gcc_file2 = os.path.join(bin_dir2, 'gcc')
        try:
            os.environ['PATH'] = os.pathsep.join((bin_dir1, bin_dir2))
            # a folder named 'gcc', its executable, but should not be
            # discovered by internal which(1)-clone
            os.makedirs(gcc_dir1)
            # an executable named gcc -- only this should be executed
            bunk_header = '#!/bin/sh\necho $*'
            with open(gcc_file2, "w") as h:
                h.write(bunk_header)
            os.chmod(gcc_file2, int(0o755))

            from sh import gcc
            if IS_PY3:
                self.assertEqual(gcc._path,
                        gcc_file2.encode(sh.DEFAULT_ENCODING))
            else:
                self.assertEqual(gcc._path, gcc_file2)
            self.assertEqual(gcc('no-error').stdout.strip(),
                'no-error'.encode("ascii"))

        finally:
            os.environ['PATH'] = save_path
            if exists(gcc_file2):
                os.unlink(gcc_file2)
            if exists(gcc_dir1):
                os.rmdir(gcc_dir1)
            if exists(bin_dir1):
                os.rmdir(bin_dir1)
            if exists(bin_dir1):
                os.rmdir(bin_dir2)

    def test_multiple_args_short_option(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", dest="long_option")
options, args = parser.parse_args()
print(len(options.long_option.split()))
""")
        num_args = int(python(py.name, l="one two three"))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, "-l", "one's two's three's"))
        self.assertEqual(num_args, 3)


    def test_multiple_args_long_option(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", "--long-option", dest="long_option")
options, args = parser.parse_args()
print(len(options.long_option.split()))
""")
        num_args = int(python(py.name, long_option="one two three"))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, "--long-option", "one's two's three's"))
        self.assertEqual(num_args, 3)


    def test_short_bool_option(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-s", action="store_true", default=False, dest="short_option")
options, args = parser.parse_args()
print(options.short_option)
""")
        self.assertTrue(python(py.name, s=True).strip() == "True")
        self.assertTrue(python(py.name, s=False).strip() == "False")
        self.assertTrue(python(py.name).strip() == "False")


    def test_long_bool_option(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", "--long-option", action="store_true", default=False, dest="long_option")
options, args = parser.parse_args()
print(options.long_option)
""")
        self.assertTrue(python(py.name, long_option=True).strip() == "True")
        self.assertTrue(python(py.name).strip() == "False")


    def test_composition(self):
        from sh import ls, wc
        c1 = int(wc(ls("-A1"), l=True))
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)

    def test_incremental_composition(self):
        from sh import ls, wc
        c1 = int(wc(ls("-A1", _piped=True), l=True).strip())
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)


    def test_short_option(self):
        from sh import sh
        s1 = sh(c="echo test").strip()
        s2 = "test"
        self.assertEqual(s1, s2)


    def test_long_option(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", "--long-option", action="store", default="", dest="long_option")
options, args = parser.parse_args()
print(options.long_option.upper())
""")
        self.assertTrue(python(py.name, long_option="testing").strip() == "TESTING")
        self.assertTrue(python(py.name).strip() == "")

    def test_raw_args(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("--long_option", action="store", default=None,
    dest="long_option1")
parser.add_option("--long-option", action="store", default=None,
    dest="long_option2")
options, args = parser.parse_args()

if options.long_option1:
    print(options.long_option1.upper())
else:
    print(options.long_option2.upper())
""")
        self.assertEqual(python(py.name,
            {"long_option": "underscore"}).strip(), "UNDERSCORE")

        self.assertEqual(python(py.name, long_option="hyphen").strip(), "HYPHEN")

    def test_custom_separator(self):
        py = create_tmp_test("""
import sys
print(sys.argv[1])
""")
        self.assertEqual(python(py.name,
            {"long-option": "underscore"}, _long_sep="=custom=").strip(), "--long-option=custom=underscore")
        # test baking too
        python_baked = python.bake(py.name, {"long-option": "underscore"}, _long_sep="=baked=")
        self.assertEqual(python_baked().strip(), "--long-option=baked=underscore")

    def test_command_wrapper(self):
        from sh import Command, which

        ls = Command(which("ls"))
        wc = Command(which("wc"))

        c1 = int(wc(ls("-A1"), l=True))
        c2 = len(os.listdir("."))

        self.assertEqual(c1, c2)


    def test_background(self):
        from sh import sleep
        import time

        start = time.time()
        sleep_time = .5
        p = sleep(sleep_time, _bg=True)

        now = time.time()
        self.assertTrue(now - start < sleep_time)

        p.wait()
        now = time.time()
        self.assertTrue(now - start > sleep_time)


    def test_background_exception(self):
        from sh import ls, ErrorReturnCode_1, ErrorReturnCode_2
        p = ls("/ofawjeofj", _bg=True) # should not raise

        exc_to_test = ErrorReturnCode_2
        if IS_OSX: exc_to_test = ErrorReturnCode_1
        self.assertRaises(exc_to_test, p.wait) # should raise


    def test_with_context(self):
        from sh import whoami
        import getpass

        py = create_tmp_test("""
import sys
import os
import subprocess

print("with_context")
subprocess.Popen(sys.argv[1:], shell=False).wait()
""")

        cmd1 = python.bake(py.name, _with=True)
        with cmd1:
            out = whoami()
        self.assertTrue("with_context" in out)
        self.assertTrue(getpass.getuser() in out)


    def test_with_context_args(self):
        from sh import whoami
        import getpass

        py = create_tmp_test("""
import sys
import os
import subprocess
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-o", "--opt", action="store_true", default=False, dest="opt")
options, args = parser.parse_args()

if options.opt:
    subprocess.Popen(args[0], shell=False).wait()
""")
        with python(py.name, opt=True, _with=True):
            out = whoami()
        self.assertTrue(getpass.getuser() == out.strip())


        with python(py.name, _with=True):
            out = whoami()
        self.assertTrue(out == "")



    def test_err_to_out(self):
        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stdout.flush()
sys.stderr.write("stderr")
sys.stderr.flush()
""")
        stdout = python(py.name, _err_to_out=True)
        self.assertTrue(stdout == "stdoutstderr")



    def test_out_redirection(self):
        import tempfile

        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")

        file_obj = tempfile.TemporaryFile()
        out = python(py.name, _out=file_obj)

        self.assertTrue(len(out) == 0)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertTrue(len(actual_out) != 0)


        # test with tee
        file_obj = tempfile.TemporaryFile()
        out = python(py.name, _out=file_obj, _tee=True)

        self.assertTrue(len(out) != 0)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertTrue(len(actual_out) != 0)



    def test_err_redirection(self):
        import tempfile

        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
        file_obj = tempfile.TemporaryFile()
        p = python(py.name, _err=file_obj)

        file_obj.seek(0)
        stderr = file_obj.read().decode()
        file_obj.close()

        self.assertTrue(p.stdout == b"stdout")
        self.assertTrue(stderr == "stderr")
        self.assertTrue(len(p.stderr) == 0)

        # now with tee
        file_obj = tempfile.TemporaryFile()
        p = python(py.name, _err=file_obj, _tee="err")

        file_obj.seek(0)
        stderr = file_obj.read().decode()
        file_obj.close()

        self.assertTrue(p.stdout == b"stdout")
        self.assertTrue(stderr == "stderr")
        self.assertTrue(len(p.stderr) != 0)



    def test_err_redirection_actual_file(self):
      import tempfile
      file_obj = tempfile.NamedTemporaryFile()
      py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
      stdout = python(py.name, _err=file_obj.name, u=True).wait()
      file_obj.seek(0)
      stderr = file_obj.read().decode()
      file_obj.close()
      self.assertTrue(stdout == "stdout")
      self.assertTrue(stderr == "stderr")

    def test_subcommand_and_bake(self):
        from sh import ls
        import getpass

        py = create_tmp_test("""
import sys
import os
import subprocess

print("subcommand")
subprocess.Popen(sys.argv[1:], shell=False).wait()
""")

        cmd1 = python.bake(py.name)
        out = cmd1.whoami()
        self.assertTrue("subcommand" in out)
        self.assertTrue(getpass.getuser() in out)


    def test_multiple_bakes(self):
        from sh import whoami
        import getpass

        py = create_tmp_test("""
import sys
import subprocess
subprocess.Popen(sys.argv[1:], shell=False).wait()
""")

        out = python.bake(py.name).bake("whoami")()
        self.assertTrue(getpass.getuser() == out.strip())



    def test_bake_args_come_first(self):
        from sh import ls
        ls = ls.bake(h=True)

        ran = ls("-la").ran
        ft = ran.index("-h")
        self.assertTrue("-la" in ran[ft:])

    def test_output_equivalence(self):
        from sh import whoami

        iam1 = whoami()
        iam2 = whoami()

        self.assertEqual(iam1, iam2)


    def test_stdout_callback(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print(i)
""")
        stdout = []
        def agg(line):
            stdout.append(line)

        p = python(py.name, _out=agg, u=True)
        p.wait()

        self.assertTrue(len(stdout) == 5)



    def test_stdout_callback_no_wait(self):
        import time

        py = create_tmp_test("""
import sys
import os
import time

for i in range(5):
    print(i)
    time.sleep(.5)
""")

        stdout = []
        def agg(line): stdout.append(line)

        p = python(py.name, _out=agg, u=True, _bg=True)

        # we give a little pause to make sure that the NamedTemporaryFile
        # exists when the python process actually starts
        time.sleep(.5)

        self.assertTrue(len(stdout) != 5)



    def test_stdout_callback_line_buffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print("herpderp")
""")

        stdout = []
        def agg(line): stdout.append(line)

        p = python(py.name, _out=agg, _out_bufsize=1, u=True)
        p.wait()

        self.assertTrue(len(stdout) == 5)



    def test_stdout_callback_line_unbuffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print("herpderp")
""")

        stdout = []
        def agg(char): stdout.append(char)

        p = python(py.name, _out=agg, _out_bufsize=0, u=True)
        p.wait()

        # + 5 newlines
        self.assertTrue(len(stdout) == (len("herpderp") * 5 + 5))


    def test_stdout_callback_buffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): sys.stdout.write("herpderp")
""")

        stdout = []
        def agg(chunk): stdout.append(chunk)

        p = python(py.name, _out=agg, _out_bufsize=4, u=True)
        p.wait()

        self.assertTrue(len(stdout) == (len("herp") / 2 * 5))



    def test_stdout_callback_with_input(self):
        py = create_tmp_test("""
import sys
import os
IS_PY3 = sys.version_info[0] == 3
if IS_PY3: raw_input = input

for i in range(5): print(str(i))
derp = raw_input("herp? ")
print(derp)
""")

        def agg(line, stdin):
            if line.strip() == "4": stdin.put("derp\n")

        p = python(py.name, _out=agg, u=True, _tee=True)
        p.wait()

        self.assertTrue("derp" in p)



    def test_stdout_callback_exit(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print(i)
""")

        stdout = []
        def agg(line):
            line = line.strip()
            stdout.append(line)
            if line == "2": return True

        p = python(py.name, _out=agg, u=True, _tee=True)
        p.wait()

        self.assertTrue("4" in p)
        self.assertTrue("4" not in stdout)



    def test_stdout_callback_terminate(self):
        import signal
        py = create_tmp_test("""
import sys
import os
import time

for i in range(5): 
    print(i)
    time.sleep(.5)
""")

        stdout = []
        def agg(line, stdin, process):
            line = line.strip()
            stdout.append(line)
            if line == "3":
                process.terminate()
                return True

        caught_signal = False
        try:
            p = python(py.name, _out=agg, u=True, _bg=True)
            p.wait()
        except sh.SignalException_SIGTERM:
            caught_signal = True

        self.assertTrue(caught_signal)
        self.assertEqual(p.process.exit_code, -signal.SIGTERM)
        self.assertTrue("4" not in p)
        self.assertTrue("4" not in stdout)



    def test_stdout_callback_kill(self):
        import signal
        import sh

        py = create_tmp_test("""
import sys
import os
import time

for i in range(5): 
    print(i)
    time.sleep(.5)
""")

        stdout = []
        def agg(line, stdin, process):
            line = line.strip()
            stdout.append(line)
            if line == "3":
                process.kill()
                return True

        caught_signal = False
        try:
            p = python(py.name, _out=agg, u=True, _bg=True)
            p.wait()
        except sh.SignalException_SIGKILL:
            caught_signal = True

        self.assertTrue(caught_signal)
        self.assertEqual(p.process.exit_code, -signal.SIGKILL)
        self.assertTrue("4" not in p)
        self.assertTrue("4" not in stdout)

    def test_general_signal(self):
        import signal
        from signal import SIGINT

        py = create_tmp_test("""
import sys
import os
import time
import signal

def sig_handler(sig, frame):
    print(10)
    exit(0)
    
signal.signal(signal.SIGINT, sig_handler)

for i in range(5):
    print(i)
    sys.stdout.flush()
    time.sleep(0.5)
""")

        stdout = []
        def agg(line, stdin, process):
            line = line.strip()
            stdout.append(line)
            if line == "3":
                process.signal(SIGINT)
                return True

        p = python(py.name, _out=agg, _tee=True)
        p.wait()

        self.assertEqual(p.process.exit_code, 0)
        self.assertEqual(p, "0\n1\n2\n3\n10\n")


    def test_iter_generator(self):
        py = create_tmp_test("""
import sys
import os
import time

for i in range(42): 
    print(i)
    sys.stdout.flush()
""")

        out = []
        for line in python(py.name, _iter=True):
            out.append(int(line.strip()))
        self.assertTrue(len(out) == 42 and sum(out) == 861)


    def test_nonblocking_iter(self):
        from errno import EWOULDBLOCK

        py = create_tmp_test("""
import time
time.sleep(3)
""")
        for line in python(py.name, _iter_noblock=True):
            break
        self.assertEqual(line, EWOULDBLOCK)


    def test_for_generator_to_err(self):
        py = create_tmp_test("""
import sys
import os

for i in range(42): 
    sys.stderr.write(str(i)+"\\n")
""")

        out = []
        for line in python(py.name, _iter="err", u=True): out.append(line)
        self.assertTrue(len(out) == 42)

        # verify that nothing is going to stdout
        out = []
        for line in python(py.name, _iter="out", u=True): out.append(line)
        self.assertTrue(len(out) == 0)



    def test_piped_generator(self):
        from sh import tr
        from string import ascii_uppercase
        import time

        py1 = create_tmp_test("""
import sys
import os
import time

for letter in "andrew":
    time.sleep(0.6)
    print(letter)
        """)

        py2 = create_tmp_test("""
import sys
import os
import time

while True:
    line = sys.stdin.readline()
    if not line: break
    print(line.strip().upper())
        """)


        times = []
        last_received = None

        letters = ""
        for line in python(python(py1.name, _piped="out", u=True), py2.name, _iter=True, u=True):
            if not letters: start = time.time()
            letters += line.strip()

            now = time.time()
            if last_received: times.append(now - last_received)
            last_received = now

        self.assertEqual("ANDREW", letters)
        self.assertTrue(all([t > .3 for t in times]))


    def test_generator_and_callback(self):
        py = create_tmp_test("""
import sys
import os

for i in range(42):
    sys.stderr.write(str(i * 2)+"\\n") 
    print(i)
""")

        stderr = []
        def agg(line): stderr.append(int(line.strip()))

        out = []
        for line in python(py.name, _iter=True, _err=agg, u=True): out.append(line)

        self.assertTrue(len(out) == 42)
        self.assertTrue(sum(stderr) == 1722)


    def test_bg_to_int(self):
        from sh import echo
        # bugs with background might cause the following error:
        #   ValueError: invalid literal for int() with base 10: ''
        self.assertEqual(int(echo("123", _bg=True)), 123)

    def test_cwd(self):
        from sh import pwd
        from os.path import realpath
        self.assertEqual(str(pwd(_cwd="/tmp")), realpath("/tmp") + "\n")
        self.assertEqual(str(pwd(_cwd="/etc")), realpath("/etc") + "\n")


    def test_huge_piped_data(self):
        from sh import tr

        stdin = tempfile.NamedTemporaryFile()

        data = "herpderp" * 4000 + "\n"
        stdin.write(data.encode())
        stdin.flush()
        stdin.seek(0)

        out = tr(tr("[:lower:]", "[:upper:]", _in=data), "[:upper:]", "[:lower:]")
        self.assertTrue(out == data)


    def test_tty_input(self):
        py = create_tmp_test("""
import sys
import os

if os.isatty(sys.stdin.fileno()):
    sys.stdout.write("password?\\n")
    sys.stdout.flush()
    pw = sys.stdin.readline().strip()
    sys.stdout.write("%s\\n" % ("*" * len(pw)))
    sys.stdout.flush()
else:
    sys.stdout.write("no tty attached!\\n")
    sys.stdout.flush()
""")

        test_pw = "test123"
        expected_stars = "*" * len(test_pw)
        d = {}

        def password_enterer(line, stdin):
            line = line.strip()
            if not line: return

            if line == "password?":
                stdin.put(test_pw + "\n")

            elif line.startswith("*"):
                d["stars"] = line
                return True

        pw_stars = python(py.name, _tty_in=True, _out=password_enterer)
        pw_stars.wait()
        self.assertEqual(d["stars"], expected_stars)

        response = python(py.name)
        self.assertEqual(response, "no tty attached!\n")


    def test_tty_output(self):
        py = create_tmp_test("""
import sys
import os

if os.isatty(sys.stdout.fileno()):
    sys.stdout.write("tty attached")
    sys.stdout.flush()
else:
    sys.stdout.write("no tty attached")
    sys.stdout.flush()
""")

        out = python(py.name, _tty_out=True)
        self.assertEqual(out, "tty attached")

        out = python(py.name, _tty_out=False)
        self.assertEqual(out, "no tty attached")


    def test_stringio_output(self):
        from sh import echo
        if IS_PY3:
            from io import StringIO
            from io import BytesIO as cStringIO
        else:
            from StringIO import StringIO
            from cStringIO import StringIO as cStringIO

        out = StringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue(), "testing 123")

        out = cStringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue().decode(), "testing 123")


    def test_stringio_input(self):
        from sh import cat

        if IS_PY3:
            from io import StringIO
            from io import BytesIO as cStringIO
        else:
            from StringIO import StringIO
            from cStringIO import StringIO as cStringIO

        input = StringIO()
        input.write("herpderp")
        input.seek(0)

        out = cat(_in=input)
        self.assertEqual(out, "herpderp")


    def test_internal_bufsize(self):
        from sh import cat

        output = cat(_in="a"*1000, _internal_bufsize=100, _out_bufsize=0)
        self.assertEqual(len(output), 100)

        output = cat(_in="a"*1000, _internal_bufsize=50, _out_bufsize=2)
        self.assertEqual(len(output), 100)


    def test_change_stdout_buffering(self):
        py = create_tmp_test("""
import sys
import os

# this proves that we won't get the output into our callback until we send
# a newline
sys.stdout.write("switch ")
sys.stdout.flush()
sys.stdout.write("buffering\\n")
sys.stdout.flush()

sys.stdin.read(1)
sys.stdout.write("unbuffered")
sys.stdout.flush()

# this is to keep the output from being flushed by the process ending, which
# would ruin our test.  we want to make sure we get the string "unbuffered"
# before the process ends, without writing a newline
sys.stdin.read(1)
""")

        d = {
            "newline_buffer_success": False,
            "unbuffered_success": False,
        }
        def interact(line, stdin, process):
            line = line.strip()
            if not line: return

            if line == "switch buffering":
                d["newline_buffer_success"] = True
                process.change_out_bufsize(0)
                stdin.put("a")

            elif line == "unbuffered":
                stdin.put("b")
                d["unbuffered_success"] = True
                return True

        # start with line buffered stdout
        pw_stars = python(py.name, _out=interact, _out_bufsize=1, u=True)
        pw_stars.wait()

        self.assertTrue(d["newline_buffer_success"])
        self.assertTrue(d["unbuffered_success"])



    def test_encoding(self):
        return
        raise NotImplementedError("what's the best way to test a different \
'_encoding' special keyword argument?")


    def test_timeout(self):
        from sh import sleep
        from time import time

        # check that a normal sleep is more or less how long the whole process
        # takes
        sleep_for = 3
        started = time()
        sh.sleep(sleep_for).wait()
        elapsed = time() - started

        self.assertTrue(abs(elapsed - sleep_for) < 0.5)

        # now make sure that killing early makes the process take less time
        sleep_for = 3
        timeout = 1
        started = time()
        try:
            sh.sleep(sleep_for, _timeout=timeout).wait()
        except sh.TimeoutException:
            pass
        elapsed = time() - started
        self.assertTrue(abs(elapsed - timeout) < 0.5)


    def test_binary_pipe(self):
        binary = b'\xec;\xedr\xdbF\x92\xf9\x8d\xa7\x98\x02/\x15\xd2K\xc3\x94d\xc9'

        py1 = create_tmp_test("""
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
sys.stdout.write(%r)
""" % binary)

        py2 = create_tmp_test("""
import sys
import os

sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
sys.stdout.write(sys.stdin.read())
""")
        out = python(python(py1.name), py2.name)
        self.assertEqual(out.stdout, binary)


    def test_auto_change_buffering(self):
        binary = b'\xec;\xedr\xdbF\x92\xf9\x8d\xa7\x98\x02/\x15\xd2K\xc3\x94d\xc9'
        py1 = create_tmp_test("""
import sys
import os
import time

sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
sys.stdout.write(b"testing")
sys.stdout.flush()
# to ensure that sh's select loop picks up the write before we write again
time.sleep(0.5)
sys.stdout.write(b"again\\n")
sys.stdout.flush()
time.sleep(0.5)
sys.stdout.write(%r)
sys.stdout.flush()
""" % binary)

        out = python(py1.name, _out_bufsize=1)
        self.assertTrue(out.stdout == b'testingagain\n\xec;\xedr\xdbF\x92\xf9\x8d\xa7\x98\x02/\x15\xd2K\xc3\x94d\xc9')


    # designed to trigger the "... (%d more, please see e.stdout)" output
    # of the ErrorReturnCode class
    def test_failure_with_large_output(self):
        from sh import ErrorReturnCode_1

        py = create_tmp_test("""
print("andrewmoffat" * 1000)
exit(1)
""")
        self.assertRaises(ErrorReturnCode_1, python, py.name)

    # designed to check if the ErrorReturnCode constructor does not raise
    # an UnicodeDecodeError
    def test_non_ascii_error(self):
        from sh import ls, ErrorReturnCode

        test = "/á"

        # coerce to unicode
        if IS_PY3:
            pass
        else:
            test = test.decode("utf8")

        self.assertRaises(ErrorReturnCode, ls, test)


    def test_no_out(self):
        py = create_tmp_test("""
import sys
sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
        p = python(py.name, _no_out=True)
        self.assertEqual(p.stdout, b"")
        self.assertEqual(p.stderr, b"stderr")
        self.assertTrue(p.process._pipe_queue.empty())

        def callback(line): pass
        p = python(py.name, _out=callback)
        self.assertEqual(p.stdout, b"")
        self.assertEqual(p.stderr, b"stderr")
        self.assertTrue(p.process._pipe_queue.empty())

        p = python(py.name)
        self.assertEqual(p.stdout, b"stdout")
        self.assertEqual(p.stderr, b"stderr")
        self.assertFalse(p.process._pipe_queue.empty())


    def test_no_err(self):
        py = create_tmp_test("""
import sys
sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
        p = python(py.name, _no_err=True)
        self.assertEqual(p.stderr, b"")
        self.assertEqual(p.stdout, b"stdout")
        self.assertFalse(p.process._pipe_queue.empty())

        def callback(line): pass
        p = python(py.name, _err=callback)
        self.assertEqual(p.stderr, b"")
        self.assertEqual(p.stdout, b"stdout")
        self.assertFalse(p.process._pipe_queue.empty())

        p = python(py.name)
        self.assertEqual(p.stderr, b"stderr")
        self.assertEqual(p.stdout, b"stdout")
        self.assertFalse(p.process._pipe_queue.empty())


    def test_no_pipe(self):
        from sh import ls

        # calling a command regular should fill up the pipe_queue
        p = ls()
        self.assertFalse(p.process._pipe_queue.empty())

        # calling a command with a callback should not
        def callback(line): pass
        p = ls(_out=callback)
        self.assertTrue(p.process._pipe_queue.empty())

        # calling a command regular with no_pipe also should not
        p = ls(_no_pipe=True)
        self.assertTrue(p.process._pipe_queue.empty())


    def test_decode_error_handling(self):
        from functools import partial

        py = create_tmp_test("""
# -*- coding: utf8 -*-
import sys
import os
sys.stdout = os.fdopen(sys.stdout.fileno(), 'wb')
IS_PY3 = sys.version_info[0] == 3
if IS_PY3:
    sys.stdout.write(bytes("te漢字st", "utf8"))
else:
    sys.stdout.write("te漢字st")
""")
        fn = partial(python, py.name, _encoding="ascii")
        def s(fn): str(fn())
        self.assertRaises(UnicodeDecodeError, s, fn)

        p = python(py.name, _encoding="ascii", _decode_errors="ignore")
        self.assertEqual(p, "test")


    def test_shared_secial_args(self):
        import sh

        if IS_PY3:
            from io import StringIO
            from io import BytesIO as cStringIO
        else:
            from StringIO import StringIO
            from cStringIO import StringIO as cStringIO

        out1 = sh.ls('.')
        out2 = StringIO()
        sh_new = sh(_out=out2)
        sh_new.ls('.')
        self.assertEqual(out1, out2.getvalue())
        out2.close()


    def test_signal_exception(self):
        from sh import SignalException_15

        def throw_terminate_signal():
            py = create_tmp_test("""
import time
while True: time.sleep(1)
""")
            to_kill = python(py.name, _bg=True)
            to_kill.terminate()
            to_kill.wait()

        self.assertRaises(SignalException_15, throw_terminate_signal)


    def test_file_output_isnt_buffered(self):
        # https://github.com/amoffat/sh/issues/147

        import time

        expected_time_increment = 0.2
        py = create_tmp_test("""
from time import sleep
import sys

for i in range(5):
    print(i)
    i += 1
    sleep(%.2f)
""" % expected_time_increment)

        file_obj = tempfile.TemporaryFile()
        p = python(py.name, _out=file_obj, _bg=True)

        # now we're going to test that the output file receives a chunk of
        # data roughly every expected_time_increment seconds, to prove that
        # output is being flushed

        last_pos = 0
        last_pos_time = 0
        times = []
        timeout = 5
        started = time.time()
        for i in range(5):
            while True:
                now = time.time()
                if now - started > timeout:
                    self.fail("test timed out")

                # check if the end of our file has grown
                file_obj.seek(0, 2)
                cur_pos = file_obj.tell()
                if cur_pos > last_pos:
                    last_pos = cur_pos
                    if last_pos_time == 0:
                        delta = 0
                    else:
                        delta = now - last_pos_time

                    if last_pos_time > 0:
                        self.assertTrue(abs(delta - expected_time_increment) <=
                                expected_time_increment * 0.5)

                    last_pos_time = now
                    break

        p.wait()
        file_obj.close()


    def test_pushd(self):
        """ test that pushd is just a specialized form of sh.args """
        import os
        old_wd = os.getcwd()
        with sh.pushd(tempdir):
            new_wd = sh.pwd().strip()

        self.assertNotEqual(old_wd, tempdir)
        self.assertEqual(old_wd, os.getcwd())
        self.assertEqual(new_wd, tempdir)


    def test_args_context(self):
        """ test that we can use the args with-context to temporarily override
        command settings """
        import os

        old_wd = os.getcwd()
        with sh.args(_cwd=tempdir):
            new_wd = sh.pwd().strip()

        # sanity
        self.assertNotEqual(old_wd, tempdir)
        self.assertEqual(old_wd, os.getcwd())
        self.assertEqual(new_wd, tempdir)


    def test_piped_direct(self):
        from sh import ls, wc

        # sanity check that our ls shows something
        p1 = ls("-A1")
        self.assertNotEqual(str(p1), "")

        # now let's run it again with direct piping.  this should yield no
        # visible output, because all the stdout is written to the process's
        # stdout fd
        p2 = ls("-A1", _piped="direct")
        p2.wait()
        self.assertEqual(str(p2), "")

        # now let us confirm that composing this function with another lets the
        # outer function read from that stdout fd directly
        c1 = int(wc(p2, l=True).strip())
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)

    def test_non_existant_cwd(self):
        from sh import ls

        # sanity check
        non_exist_dir = join(tempdir, "aowjgoahewro") 
        self.assertFalse(exists(non_exist_dir))

        self.assertRaises(OSError, ls, _cwd=non_exist_dir)


    # https://github.com/amoffat/sh/issues/176
    def test_baked_command_can_be_printed(self):
        from sh import ls

        ll = ls.bake("-l")
        self.assertTrue(str(ll).endswith("/ls -l"))


    # https://github.com/amoffat/sh/issues/185
    def test_done_callback(self):
        import time

        class Callback(object):
            def __init__(self):
                self.called = False
                self.exit_code = None
            def __call__(self, p):
                self.called = True
                self.exit_code = p.exit_code

        py = create_tmp_test("""
from time import time, sleep
sleep(1)
print(time())
""")

        callback = Callback()
        p = python(py.name, _done=callback)

        # do a little setup to prove that a command with a _done callback is run
        # in the background
        wait_start = time.time()
        p.wait()
        wait_elapsed = time.time() - wait_start

        self.assertTrue(callback.called)
        self.assertTrue(abs(wait_elapsed - 1.0) < 0.1)
        self.assertEqual(callback.exit_code, 0)


    def test_done_cb_exc(self):
        from sh import ErrorReturnCode

        class Callback(object):
            def __init__(self):
                self.called = False
            def __call__(self, p):
                self.called = True

        py = create_tmp_test("exit(1)")

        callback = Callback()
        try:
            p = python(py.name, _done=callback)
            p.wait()
        except ErrorReturnCode:
            self.assertFalse(callback.called)
        else:
            self.fail("command should've thrown an exception")


    def test_stdin_unbuffered_bufsize(self):
        import sh
        from time import sleep

        # this tries to receive some known data and measures the time it takes
        # to receive it.  since we're flushing by newline, we should only be
        # able to receive the data when a newline is fed in
        py = create_tmp_test("""
import sys
from time import time

started = time()
data = sys.stdin.read(len("testing"))
waited = time() - started
sys.stdout.write(data + "\\n")
sys.stdout.write(str(waited) + "\\n")

started = time()
data = sys.stdin.read(len("done"))
waited = time() - started
sys.stdout.write(data + "\\n")
sys.stdout.write(str(waited) + "\\n")

sys.stdout.flush()
""")

        def create_stdin():
            data = {"counter": 0}
            def stdin():
                if data["counter"] == 0:
                    data["counter"] += 1
                    return "test"
                elif data["counter"] == 1:
                    data["counter"] += 1
                    sleep(1)
                    return "ing"
                elif data["counter"] == 2:
                    data["counter"] += 1
                    sleep(1)
                    return "done"
                else:
                    raise sh.DoneReadingForever
            return stdin

        out = python(py.name, _in=create_stdin(), _in_bufsize=0)
        word1, time1, word2, time2, _ = out.split("\n")
        time1 = float(time1)
        time2 = float(time2)
        self.assertEqual(word1, "testing")
        self.assertTrue(abs(1-time1) < 0.1)
        self.assertEqual(word2, "done")
        self.assertTrue(abs(1-time2) < 0.1)


    def test_stdin_newline_bufsize(self):
        import sh
        from time import sleep

        # this tries to receive some known data and measures the time it takes
        # to receive it.  since we're flushing by newline, we should only be
        # able to receive the data when a newline is fed in
        py = create_tmp_test("""
import sys
from time import time

started = time()
data = sys.stdin.read(len("testing\\n"))
waited = time() - started
sys.stdout.write(data)
sys.stdout.write(str(waited) + "\\n")

started = time()
data = sys.stdin.read(len("done\\n"))
waited = time() - started
sys.stdout.write(data)
sys.stdout.write(str(waited) + "\\n")

sys.stdout.flush()
""")

        # we'll feed in text incrementally, sleeping strategically before
        # sending a newline.  we then measure the amount that we slept
        # indirectly in the child process
        def create_stdin():
            data = {"counter": 0}
            def stdin():
                if data["counter"] == 0:
                    data["counter"] += 1
                    return "test"
                elif data["counter"] == 1:
                    sleep(1)
                    data["counter"] += 1
                    return "ing\n"
                elif data["counter"] == 2:
                    sleep(1)
                    return "done\n"
                else:
                    raise sh.DoneReadingForever
            return stdin

        out = python(py.name, _in=create_stdin(), _in_bufsize=1)
        word1, time1, word2, time2, _ = out.split("\n")
        time1 = float(time1)
        time2 = float(time2)
        self.assertEqual(word1, "testing")
        self.assertTrue(abs(1-time1) < 0.1)
        self.assertEqual(word2, "done")
        self.assertTrue(abs(1-time2) < 0.1)


    def test_custom_timeout_signal(self):
        from sh import TimeoutException
        import signal

        py = create_tmp_test("""
import time
time.sleep(3)
""")
        try:
            python(py.name, _timeout=1, _timeout_signal=signal.SIGQUIT)
        except TimeoutException as e:
            self.assertEqual(e.exit_code, signal.SIGQUIT)
        else:
            self.fail("we should have handled a TimeoutException")


    def test_partially_applied_callback(self):
        from functools import partial

        py = create_tmp_test("""
for i in range(10):
    print(i)
""")

        output = []
        def fn(foo, line):
            output.append((foo, int(line.strip())))

        log_line = partial(fn, "hello")
        out = python(py.name, _out=log_line)
        self.assertEqual(output, [("hello", i) for i in range(10)])


        output = []
        def fn(foo, line, stdin, proc):
            output.append((foo, int(line.strip())))

        log_line = partial(fn, "hello")
        out = python(py.name, _out=log_line)
        self.assertEqual(output, [("hello", i) for i in range(10)])








class MiscTests(unittest.TestCase):
    def test_percent_doesnt_fail_logging(self):
        """ test that a command name doesn't interfere with string formatting in
        the internal loggers """
        py = create_tmp_test("""
print("cool")
""")
        out = python(py.name, "%")
        out = python(py.name, "%%")
        out = python(py.name, "%%%")

    @requires_utf8
    def test_unicode_path(self):
        from sh import Command

        py = create_tmp_test("""#!/usr/bin/env python
# -*- coding: utf8 -*-
print("字")
""", "字", delete=False)

        try:
            py.close()
            os.chmod(py.name, int(0o755))
            cmd = Command(py.name)

            # all of these should behave just fine
            str(cmd)
            repr(cmd)
            unicode(cmd)

            running = cmd()
            str(running)
            repr(running)
            unicode(running)

            str(running.process)
            repr(running.process)
            unicode(running.process)

        finally:
            os.unlink(py.name)


    # https://github.com/amoffat/sh/issues/121
    def test_wraps(self):
        from sh import ls
        wraps(ls)(lambda f: True)

    def test_signal_exception_aliases(self):
        """ proves that signal exceptions with numbers and names are equivalent
        """
        import signal
        import sh

        sig_name = "SignalException_%d" % signal.SIGQUIT
        sig = getattr(sh, sig_name)
        from sh import SignalException_SIGQUIT

        self.assertEqual(sig, SignalException_SIGQUIT)


class StreamBuffererTests(unittest.TestCase):
    def test_unbuffered(self):
        from sh import _disable_whitelist, StreamBufferer
        b = StreamBufferer(0)

        self.assertEqual(b.process(b"test"), [b"test"])
        self.assertEqual(b.process(b"one"), [b"one"])
        self.assertEqual(b.process(b""), [b""])
        self.assertEqual(b.flush(), b"")

    def test_newline_buffered(self):
        from sh import _disable_whitelist, StreamBufferer
        b = StreamBufferer(1)

        self.assertEqual(b.process(b"testing\none\ntwo"), [b"testing\n", b"one\n"])
        self.assertEqual(b.process(b"\nthree\nfour"), [b"two\n", b"three\n"])
        self.assertEqual(b.flush(), b"four")

    def test_chunk_buffered(self):
        from sh import _disable_whitelist, StreamBufferer
        b = StreamBufferer(10)

        self.assertEqual(b.process(b"testing\none\ntwo"), [b"testing\non"])
        self.assertEqual(b.process(b"\nthree\n"), [b"e\ntwo\nthre"])
        self.assertEqual(b.flush(), b"e\n")



if __name__ == "__main__":
    # if we're running a specific test, we can let unittest framework figure out
    # that test and run it itself.  it will also handle setting the return code
    # of the process if any tests error or fail
    if len(sys.argv) > 1:
        unittest.main()

    # otherwise, it looks like we want to run all the tests
    else:
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        result = unittest.TextTestRunner(verbosity=2).run(suite)

        if not result.wasSuccessful():
            exit(1)
