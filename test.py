# -*- coding: utf8 -*-

import os
import unittest
import tempfile
import sys


IS_PY3 = sys.version_info[0] == 3
if IS_PY3:
    unicode = str


skipUnless = getattr(unittest, "skipUnless", None)
if not skipUnless:
    def skipUnless(*args, **kwargs):
        def wrapper(thing): return thing
        return wrapper

requires_posix = skipUnless(os.name == "posix", "Requires POSIX")



def create_tmp_test(code):
    py = tempfile.NamedTemporaryFile()
    if IS_PY3: code = bytes(code, "UTF-8")
    py.write(code)
    py.flush()
    return py



@requires_posix
class Basic(unittest.TestCase):

    def test_print_command(self):
        from pbs import ls, which
        actual_location = which("ls")
        out = str(ls)
        self.assertEqual(out, actual_location)

    def test_unicode_arg(self):
        from pbs import echo
        if IS_PY3: test = "漢字"
        else: test = "漢字".decode("utf8")
        p = echo(test).strip()

        self.assertEqual(test, p)

    def test_number_arg(self):
        from pbs import python

        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()
print args[0]
""")

        out = python(py.name, 3).strip()
        self.assertEqual(out, "3")

    def test_ok_code(self):
        from pbs import ls, ErrorReturnCode_2

        self.assertRaises(ErrorReturnCode_2, ls, "/aofwje/garogjao4a/eoan3on")
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=2)
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=[2])

    def test_glob_warning(self):
        from pbs import ls
        from glob import glob
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            ls(glob("ofjaoweijfaowe"))

            self.assertTrue(len(w) == 1)
            self.assertTrue(issubclass(w[-1].category, UserWarning))
            self.assertTrue("glob" in str(w[-1].message))

    def test_stdin_from_string(self):
        from pbs import sed
        self.assertEqual(sed(_in="test", e="s/test/lol/"), "lol")

    def test_quote_escaping(self):
        from pbs import python

        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()
print args
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


    def test_environment(self):
        from pbs import python
        import os

        env = {"HERP": "DERP"}

        py = create_tmp_test("""
import os
print os.environ["HERP"], len(os.environ)
""")
        out = python(py.name, _env=env).strip()
        self.assertEqual(out, "DERP 1")

        py = create_tmp_test("""
import pbs, os
print pbs.HERP, len(os.environ)
""")
        out = python(py.name, _env=env).strip()
        self.assertEqual(out, "DERP 1")


    def test_which(self):
        from pbs import which, ls
        self.assertEqual(which("fjoawjefojawe"), None)
        self.assertEqual(which("ls"), str(ls))


    def test_no_arg(self):
        import pwd
        from pbs import whoami
        u1 = whoami().strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)


    def test_exception(self):
        from pbs import ls, ErrorReturnCode_2
        self.assertRaises(ErrorReturnCode_2, ls, "/aofwje/garogjao4a/eoan3on")


    def test_command_not_found(self):
        from pbs import CommandNotFound

        def do_import(): from pbs import aowjgoawjoeijaowjellll
        self.assertRaises(CommandNotFound, do_import)


    def test_command_wrapper_equivalence(self):
        from pbs import Command, ls, which

        self.assertEqual(Command(which("ls")), ls)


    def test_multiple_args_short_option(self):
        from pbs import python

        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", dest="long_option")
options, args = parser.parse_args()
print len(options.long_option.split())
""")
        num_args = int(python(py.name, l="one two three"))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, l="\"one two three\""))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, l='\"one two three\"'))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, l='"one two three"'))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, "-l", "one's two's three's"))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, "-l", "\"one's two's three's\""))
        self.assertEqual(num_args, 3)


    def test_multiple_args_long_option(self):
        from pbs import python

        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", "--long-option", dest="long_option")
options, args = parser.parse_args()
print len(options.long_option.split())
""")
        num_args = int(python(py.name, long_option="one two three"))
        self.assertEqual(num_args, 3)

        num_args = int(python(py.name, "--long-option", "one's two's three's"))
        self.assertEqual(num_args, 3)


    def test_short_bool_option(self):
        from pbs import id
        i1 = int(id(u=True))
        i2 = os.geteuid()
        self.assertEqual(i1, i2)


    def test_long_bool_option(self):
        from pbs import id
        i1 = int(id(user=True, real=True))
        i2 = os.getuid()
        self.assertEqual(i1, i2)


    def test_composition(self):
        from pbs import ls, wc
        c1 = int(wc(ls("-A1"), l=True))
        c2 = len(os.listdir("."))
        if c1 != c2:
            with open("/tmp/fail", "a") as h: h.write("FUCK\n")
        self.assertEqual(c1, c2)


    def test_short_option(self):
        from pbs import sh
        s1 = sh(c="echo test").strip()
        s2 = "test"
        self.assertEqual(s1, s2)


    def test_long_option(self):
        from pbs import sed, echo
        out = sed(echo("test"), expression="s/test/lol/").strip()
        self.assertEqual(out, "lol")


    def test_command_wrapper(self):
        from pbs import Command, which

        ls = Command(which("ls"))
        wc = Command(which("wc"))

        c1 = int(wc(ls("-A1"), l=True))
        c2 = len(os.listdir("."))

        self.assertEqual(c1, c2)


    def test_background(self):
        from pbs import sleep
        import time

        start = time.time()
        sleep_time = .5
        p = sleep(sleep_time, _bg=True)

        now = time.time()
        self.assertTrue(now - start < sleep_time)

        p.wait()
        now = time.time()
        self.assertTrue(now - start > sleep_time)


    def test_bg_to_int(self):
        from pbs import echo
        # bugs with background might cause the following error:
        #   ValueError: invalid literal for int() with base 10: ''
        self.assertEqual(int(echo("123", _bg=True)), 123)


    def test_with_context(self):
        from pbs import time, ls
        with time:
            out = ls().stderr
        self.assertTrue("pagefaults" in out)



    def test_with_context_args(self):
        from pbs import time, ls
        with time(verbose=True, _with=True):
            out = ls().stderr
        self.assertTrue("Voluntary context switches" in out)



    def test_err_to_out(self):
        from pbs import time, ls
        with time(_with=True):
            out = ls(_err_to_out=True)

        self.assertTrue("pagefaults" in out)



    def test_out_redirection(self):
        import tempfile
        from pbs import ls

        file_obj = tempfile.TemporaryFile()
        out = ls(_out=file_obj)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertTrue(len(actual_out) != 0)



    def test_err_redirection(self):
        import tempfile
        from pbs import time, ls

        file_obj = tempfile.TemporaryFile()

        with time(_with=True):
            out = ls(_err=file_obj)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertTrue(len(actual_out) != 0)


    def test_subcommand(self):
        from pbs import time

        out = time.ls(_err_to_out=True)
        self.assertTrue("pagefaults" in out)


    def test_bake(self):
        from pbs import time, ls
        timed = time.bake("--verbose", _err_to_out=True)
        out = timed.ls()
        self.assertTrue("Voluntary context switches" in out)


    def test_multiple_bakes(self):
        from pbs import time
        timed = time.bake("--verbose", _err_to_out=True)
        out = timed.bake("ls")()
        self.assertTrue("Voluntary context switches" in out)


    def test_bake_args_come_first(self):
        from pbs import ls
        ls = ls.bake(full_time=True)

        ran = ls("-la").command_ran
        ft = ran.index("full-time")
        self.assertTrue("-la" in ran[ft:])


    def test_output_equivalence(self):
        from pbs import whoami

        iam1 = whoami()
        iam2 = whoami()

        self.assertEqual(iam1, iam2)

    def test_cwd(self):
        from pbs import pwd
        self.assertEqual(str(pwd(_cwd='/tmp')), '/tmp\n')
        self.assertEqual(str(pwd(_cwd='/etc')), '/etc\n')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(Basic)
        unittest.TextTestRunner(verbosity=2).run(suite)
