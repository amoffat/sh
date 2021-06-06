# -*- coding: utf8 -*-
from contextlib import contextmanager
from functools import wraps
from os.path import exists, join, realpath, dirname, split
import errno
import fcntl
import inspect
import logging
import os
import platform
import pty
import resource
import sh
import signal
import stat
import sys
import tempfile
import time
import unittest
import warnings

IS_PY3 = sys.version_info[0] == 3
IS_PY2 = not IS_PY3
MINOR_VER = sys.version_info[1]

# coverage doesn't work in python 3.1, 3.2 due to it just being a shit
# python
HAS_UNICODE_LITERAL = not (IS_PY3 and MINOR_VER in (1, 2))

cov = None
if HAS_UNICODE_LITERAL:
    run_idx = int(os.environ.pop("SH_TEST_RUN_IDX", "0"))
    first_run = run_idx == 0

    try:
        import coverage
    except ImportError:
        pass
    else:
        # for some reason, we can't run auto_data on the first run, or the coverage
        # numbers get really screwed up
        auto_data = True
        if first_run:
            auto_data = False

        cov = coverage.Coverage(auto_data=auto_data)

        if first_run:
            cov.erase()

        cov.start()

try:
    import unittest.mock
except ImportError:
    HAS_MOCK = False
else:
    HAS_MOCK = True

# we have to use the real path because on osx, /tmp is a symlink to
# /private/tmp, and so assertions that gettempdir() == sh.pwd() will fail
tempdir = realpath(tempfile.gettempdir())
IS_MACOS = platform.system() in ("AIX", "Darwin")


# these 3 functions are helpers for modifying PYTHONPATH with a module's main
# directory

def append_pythonpath(env, path):
    key = "PYTHONPATH"
    pypath = [p for p in env.get(key, "").split(":") if p]
    pypath.insert(0, path)
    pypath = ":".join(pypath)
    env[key] = pypath


def get_module_import_dir(m):
    mod_file = inspect.getsourcefile(m)
    is_package = mod_file.endswith("__init__.py")

    mod_dir = dirname(mod_file)
    if is_package:
        mod_dir, _ = split(mod_dir)
    return mod_dir


def append_module_path(env, m):
    append_pythonpath(env, get_module_import_dir(m))


if IS_PY3:
    xrange = range
    unicode = str
    long = int
    from io import StringIO

    ioStringIO = StringIO
    from io import BytesIO as cStringIO

    iocStringIO = cStringIO
else:
    from StringIO import StringIO
    from cStringIO import StringIO as cStringIO
    from io import StringIO as ioStringIO
    from io import BytesIO as iocStringIO

THIS_DIR = dirname(os.path.abspath(__file__))

system_python = sh.Command(sys.executable)

# this is to ensure that our `python` helper here is able to import our local sh
# module, and not the system one
baked_env = os.environ.copy()
append_module_path(baked_env, sh)
python = system_python.bake(_env=baked_env)

if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None

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
skip_unless = skipUnless


def requires_progs(*progs):
    missing = []
    for prog in progs:
        try:
            sh.Command(prog)
        except sh.CommandNotFound:
            missing.append(prog)

    friendly_missing = ", ".join(missing)
    return skipUnless(len(missing) == 0, "Missing required system programs: %s"
                      % friendly_missing)


requires_posix = skipUnless(os.name == "posix", "Requires POSIX")
requires_utf8 = skipUnless(sh.DEFAULT_ENCODING == "UTF-8", "System encoding must be UTF-8")
not_macos = skipUnless(not IS_MACOS, "Doesn't work on MacOS")
requires_py3 = skipUnless(IS_PY3, "Test only works on Python 3")
requires_py35 = skipUnless(IS_PY3 and MINOR_VER >= 5, "Test only works on Python 3.5 or higher")


def requires_poller(poller):
    use_select = bool(int(os.environ.get("SH_TESTS_USE_SELECT", "0")))
    cur_poller = "select" if use_select else "poll"
    return skipUnless(cur_poller == poller, "Only enabled for select.%s" % cur_poller)


@contextmanager
def ulimit(key, new_soft):
    soft, hard = resource.getrlimit(key)
    resource.setrlimit(key, (new_soft, hard))
    try:
        yield
    finally:
        resource.setrlimit(key, (soft, hard))


def create_tmp_test(code, prefix="tmp", delete=True, **kwargs):
    """ creates a temporary test file that lives on disk, on which we can run
    python with sh """

    py = tempfile.NamedTemporaryFile(prefix=prefix, delete=delete)

    code = code.format(**kwargs)
    if IS_PY3:
        code = code.encode("UTF-8")

    py.write(code)
    py.flush()

    # make the file executable
    st = os.stat(py.name)
    os.chmod(py.name, st.st_mode | stat.S_IEXEC)

    # we don't explicitly close, because close will remove the file, and we
    # don't want that until the test case is done.  so we let the gc close it
    # when it goes out of scope
    return py


class BaseTests(unittest.TestCase):
    def assert_oserror(self, num, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except OSError as e:
            self.assertEqual(e.errno, num)

    def assert_deprecated(self, fn, *args, **kwargs):
        with warnings.catch_warnings(record=True) as w:
            fn(*args, **kwargs)

            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))

    # python2.6 lacks this
    def assertIn(self, needle, haystack):
        s = super(BaseTests, self)
        if hasattr(s, "assertIn"):
            s.assertIn(needle, haystack)
        else:
            self.assertTrue(needle in haystack)

    # python2.6 lacks this
    def assertNotIn(self, needle, haystack):
        s = super(BaseTests, self)
        if hasattr(s, "assertNotIn"):
            s.assertNotIn(needle, haystack)
        else:
            self.assertTrue(needle not in haystack)

    # python2.6 lacks this
    def assertLess(self, a, b):
        s = super(BaseTests, self)
        if hasattr(s, "assertLess"):
            s.assertLess(a, b)
        else:
            self.assertTrue(a < b)

    # python2.6 lacks this
    def assertGreater(self, a, b):
        s = super(BaseTests, self)
        if hasattr(s, "assertGreater"):
            s.assertGreater(a, b)
        else:
            self.assertTrue(a > b)

    # python2.6 lacks this
    def skipTest(self, msg):
        s = super(BaseTests, self)
        if hasattr(s, "skipTest"):
            s.skipTest(msg)
        else:
            return


@requires_posix
class FunctionalTests(BaseTests):

    def setUp(self):
        self._environ = os.environ.copy()

    def tearDown(self):
        os.environ = self._environ

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

    def test_unicode_exception(self):
        from sh import ErrorReturnCode
        py = create_tmp_test("exit(1)")

        arg = "漢字"
        native_arg = arg
        if not IS_PY3:
            arg = arg.decode("utf8")

        try:
            python(py.name, arg, _encoding="utf8")
        except ErrorReturnCode as e:
            self.assertIn(native_arg, str(e))
        else:
            self.fail("exception wasn't raised")

    def test_pipe_fd(self):
        py = create_tmp_test("""print("hi world")""")
        read_fd, write_fd = os.pipe()
        python(py.name, _out=write_fd)
        out = os.read(read_fd, 10)
        self.assertEqual(out, b"hi world\n")

    def test_trunc_exc(self):
        py = create_tmp_test("""
import sys
sys.stdout.write("a" * 1000)
sys.stderr.write("b" * 1000)
exit(1)
""")
        self.assertRaises(sh.ErrorReturnCode_1, python, py.name)

    def test_number_arg(self):
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()
print(args[0])
""")

        out = python(py.name, 3).strip()
        self.assertEqual(out, "3")

    def test_empty_stdin_no_hang(self):
        py = create_tmp_test("""
import sys
data = sys.stdin.read()
sys.stdout.write("no hang")
""")
        out = python(py.name, _in="", _timeout=2)
        self.assertEqual(out, "no hang")

        out = python(py.name, _in=None, _timeout=2)
        self.assertEqual(out, "no hang")

    def test_exit_code(self):
        from sh import ErrorReturnCode_3
        py = create_tmp_test("""
exit(3)
""")
        self.assertRaises(ErrorReturnCode_3, python, py.name)

    def test_patched_glob(self):
        from glob import glob

        py = create_tmp_test("""
import sys
print(sys.argv[1:])
""")
        files = glob("*.faowjefoajweofj")
        out = python(py.name, files).strip()
        self.assertEqual(out, "['*.faowjefoajweofj']")

    @requires_py35
    def test_patched_glob_with_recursive_argument(self):
        from glob import glob

        py = create_tmp_test("""
import sys
print(sys.argv[1:])
""")
        files = glob("*.faowjefoajweofj", recursive=True)
        out = python(py.name, files).strip()
        self.assertEqual(out, "['*.faowjefoajweofj']")

    def test_exit_code_with_hasattr(self):
        from sh import ErrorReturnCode_3
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
        except ErrorReturnCode_3:
            pass

    def test_exit_code_from_exception(self):
        from sh import ErrorReturnCode_3
        py = create_tmp_test("""
exit(3)
""")

        self.assertRaises(ErrorReturnCode_3, python, py.name)

        try:
            python(py.name)
        except Exception as e:
            self.assertEqual(e.exit_code, 3)

    def test_stdin_from_string(self):
        from sh import sed
        self.assertEqual(sed(_in="one test three", e="s/test/two/").strip(),
                         "one two three")

    def test_ok_code(self):
        from sh import ls, ErrorReturnCode_1, ErrorReturnCode_2

        exc_to_test = ErrorReturnCode_2
        code_to_pass = 2
        if IS_MACOS:
            exc_to_test = ErrorReturnCode_1
            code_to_pass = 1
        self.assertRaises(exc_to_test, ls, "/aofwje/garogjao4a/eoan3on")

        ls("/aofwje/garogjao4a/eoan3on", _ok_code=code_to_pass)
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=[code_to_pass])
        ls("/aofwje/garogjao4a/eoan3on", _ok_code=range(code_to_pass + 1))

    def test_ok_code_none(self):
        py = create_tmp_test("exit(0)")
        python(py.name, _ok_code=None)

    def test_ok_code_exception(self):
        from sh import ErrorReturnCode_0
        py = create_tmp_test("exit(0)")
        self.assertRaises(ErrorReturnCode_0, python, py.name, _ok_code=2)

    def test_none_arg(self):
        py = create_tmp_test("""
import sys
print(sys.argv[1:])
""")
        maybe_arg = "some"
        out = python(py.name, maybe_arg).strip()
        self.assertEqual(out, "['some']")

        maybe_arg = None
        out = python(py.name, maybe_arg).strip()
        self.assertEqual(out, "[]")

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
        import time

        py = create_tmp_test("""
import sys
import os
import time

for l in "andrew":
    sys.stdout.write(l)
    time.sleep(.2)
""")

        inc_py = create_tmp_test("""
import sys
while True:
    letter = sys.stdin.read(1)
    if not letter:
        break
    sys.stdout.write(chr(ord(letter)+1))
""")

        def inc(proc, *args, **kwargs):
            return python(proc, "-u", inc_py.name, *args, **kwargs)

        class Derp(object):
            def __init__(self):
                self.times = []
                self.stdout = []
                self.last_received = None

            def agg(self, line):
                self.stdout.append(line.strip())
                now = time.time()
                if self.last_received:
                    self.times.append(now - self.last_received)
                self.last_received = now

        derp = Derp()

        p = inc(
            inc(
                inc(
                    python("-u", py.name, _piped=True),
                    _piped=True),
                _piped=True),
            _out=derp.agg)

        p.wait()
        self.assertEqual("".join(derp.stdout), "dqguhz")
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
        try:
            from Queue import Queue
        except ImportError:
            from queue import Queue

        test = ["testing\n", "herp\n", "derp\n"]

        q = Queue()
        for t in test:
            q.put(t)
        q.put(None)  # EOF

        out = tr("[:lower:]", "[:upper:]", _in=q)

        match = "".join([t.upper() for t in test])
        self.assertEqual(out, match)

    def test_environment(self):
        """ tests that environments variables that we pass into sh commands
        exist in the environment, and on the sh module """
        import os

        # this is the environment we'll pass into our commands
        env = {"HERP": "DERP"}

        # first we test that the environment exists in our child process as
        # we've set it
        py = create_tmp_test("""
import os

for key in list(os.environ.keys()):
    if key != "HERP":
        del os.environ[key]
print(dict(os.environ))
""")
        out = python(py.name, _env=env).strip()
        self.assertEqual(out, "{'HERP': 'DERP'}")

        py = create_tmp_test("""
import os, sys
sys.path.insert(0, os.getcwd())
import sh
for key in list(os.environ.keys()):
    if key != "HERP":
        del os.environ[key]
print(dict(HERP=sh.HERP))
""")
        out = python(py.name, _env=env, _cwd=THIS_DIR).strip()
        self.assertEqual(out, "{'HERP': 'DERP'}")

        # Test that _env also accepts os.environ which is a mpping but not a dict.
        os.environ["HERP"] = "DERP"
        out = python(py.name, _env=os.environ, _cwd=THIS_DIR).strip()
        self.assertEqual(out, "{'HERP': 'DERP'}")

    def test_which(self):
        from sh import which, ls
        self.assertEqual(which("fjoawjefojawe"), None)
        self.assertEqual(which("ls"), str(ls))

    def test_which_paths(self):
        from sh import which
        py = create_tmp_test("""
print("hi")
""")
        test_path = dirname(py.name)
        _, test_name = os.path.split(py.name)

        found_path = which(test_name)
        self.assertEqual(found_path, None)

        found_path = which(test_name, [test_path])
        self.assertEqual(found_path, py.name)

    def test_no_close_fds(self):
        # guarantee some extra fds in our parent process that don't close on exec.  we have to explicitly do this
        # because at some point (I believe python 3.4), python started being more stringent with closing fds to prevent
        # security vulnerabilities.  python 2.7, for example, doesn't set CLOEXEC on tempfile.TemporaryFile()s
        #
        # https://www.python.org/dev/peps/pep-0446/
        tmp = [tempfile.TemporaryFile() for i in range(10)]
        for t in tmp:
            flags = fcntl.fcntl(t.fileno(), fcntl.F_GETFD)
            flags &= ~fcntl.FD_CLOEXEC
            fcntl.fcntl(t.fileno(), fcntl.F_SETFD, flags)

        py = create_tmp_test("""
import os
print(len(os.listdir("/dev/fd")))
""")
        out = python(py.name, _close_fds=False).strip()
        # pick some number greater than 4, since it's hard to know exactly how many fds will be open/inherted in the
        # child
        self.assertGreater(int(out), 7)

        for t in tmp:
            t.close()

    def test_close_fds(self):
        # guarantee some extra fds in our parent process that don't close on exec.  we have to explicitly do this
        # because at some point (I believe python 3.4), python started being more stringent with closing fds to prevent
        # security vulnerabilities.  python 2.7, for example, doesn't set CLOEXEC on tempfile.TemporaryFile()s
        #
        # https://www.python.org/dev/peps/pep-0446/
        tmp = [tempfile.TemporaryFile() for i in range(10)]
        for t in tmp:
            flags = fcntl.fcntl(t.fileno(), fcntl.F_GETFD)
            flags &= ~fcntl.FD_CLOEXEC
            fcntl.fcntl(t.fileno(), fcntl.F_SETFD, flags)

        py = create_tmp_test("""
import os
print(os.listdir("/dev/fd"))
""")
        out = python(py.name).strip()
        self.assertEqual(out, "['0', '1', '2', '3']")

        for t in tmp:
            t.close()

    def test_pass_fds(self):
        # guarantee some extra fds in our parent process that don't close on exec.  we have to explicitly do this
        # because at some point (I believe python 3.4), python started being more stringent with closing fds to prevent
        # security vulnerabilities.  python 2.7, for example, doesn't set CLOEXEC on tempfile.TemporaryFile()s
        #
        # https://www.python.org/dev/peps/pep-0446/
        tmp = [tempfile.TemporaryFile() for i in range(10)]
        for t in tmp:
            flags = fcntl.fcntl(t.fileno(), fcntl.F_GETFD)
            flags &= ~fcntl.FD_CLOEXEC
            fcntl.fcntl(t.fileno(), fcntl.F_SETFD, flags)
        last_fd = tmp[-1].fileno()

        py = create_tmp_test("""
import os
print(os.listdir("/dev/fd"))
""")
        out = python(py.name, _pass_fds=[last_fd]).strip()
        inherited = [0, 1, 2, 3, last_fd]
        inherited_str = [str(i) for i in inherited]
        self.assertEqual(out, str(inherited_str))

        for t in tmp:
            t.close()

    def test_no_arg(self):
        import pwd
        from sh import whoami
        u1 = whoami().strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)

    def test_incompatible_special_args(self):
        from sh import ls
        self.assertRaises(TypeError, ls, _iter=True, _piped=True)

    def test_invalid_env(self):
        from sh import ls

        exc = TypeError
        if IS_PY2 and MINOR_VER == 6:
            exc = ValueError

        self.assertRaises(exc, ls, _env="XXX")
        self.assertRaises(exc, ls, _env={"foo": 123})
        self.assertRaises(exc, ls, _env={123: "bar"})

    def test_exception(self):
        from sh import ErrorReturnCode_2

        py = create_tmp_test("""
exit(2)
""")
        self.assertRaises(ErrorReturnCode_2, python, py.name)

    def test_piped_exception1(self):
        from sh import ErrorReturnCode_2

        py = create_tmp_test("""
import sys
sys.stdout.write("line1\\n")
sys.stdout.write("line2\\n")
exit(2)
""")

        py2 = create_tmp_test("")

        def fn():
            list(python(python(py.name, _piped=True), "-u", py2.name, _iter=True))

        self.assertRaises(ErrorReturnCode_2, fn)

    def test_piped_exception2(self):
        from sh import ErrorReturnCode_2

        py = create_tmp_test("""
import sys
sys.stdout.write("line1\\n")
sys.stdout.write("line2\\n")
exit(2)
""")

        py2 = create_tmp_test("")

        def fn():
            python(python(py.name, _piped=True), "-u", py2.name)

        self.assertRaises(ErrorReturnCode_2, fn)

    def test_command_not_found(self):
        from sh import CommandNotFound

        def do_import():
            from sh import aowjgoawjoeijaowjellll  # noqa: F401

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

            import sh
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
        num_args = int(python(py.name, l="one two three"))  # noqa: E741
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
        num_args = int(python(py.name, long_option="one two three",
                              nothing=False))
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

    def test_false_bool_ignore(self):
        py = create_tmp_test("""
import sys
print(sys.argv[1:])
""")
        test = True
        self.assertEqual(python(py.name, test and "-n").strip(), "['-n']")
        test = False
        self.assertEqual(python(py.name, test and "-n").strip(), "[]")

    def test_composition(self):
        from sh import ls, wc
        c1 = int(wc(ls("-A1"), l=True))  # noqa: E741
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)

    def test_incremental_composition(self):
        from sh import ls, wc
        c1 = int(wc(ls("-A1", _piped=True), l=True).strip())  # noqa: E741
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

        opt = {"long-option": "underscore"}
        correct = "--long-option=custom=underscore"

        out = python(py.name, opt, _long_sep="=custom=").strip()
        self.assertEqual(out, correct)

        # test baking too
        correct = "--long-option=baked=underscore"
        python_baked = python.bake(py.name, opt, _long_sep="=baked=")
        out = python_baked().strip()
        self.assertEqual(out, correct)

    def test_custom_separator_space(self):
        py = create_tmp_test("""
import sys
print(str(sys.argv[1:]))
""")
        opt = {"long-option": "space"}
        correct = ["--long-option", "space"]
        out = python(py.name, opt, _long_sep=" ").strip()
        self.assertEqual(out, str(correct))

    def test_custom_long_prefix(self):
        py = create_tmp_test("""
import sys
print(sys.argv[1])
""")

        out = python(py.name, {"long-option": "underscore"},
                     _long_prefix="-custom-").strip()
        self.assertEqual(out, "-custom-long-option=underscore")

        out = python(py.name, {"long-option": True},
                     _long_prefix="-custom-").strip()
        self.assertEqual(out, "-custom-long-option")

        # test baking too
        out = python.bake(py.name, {"long-option": "underscore"},
                          _long_prefix="-baked-")().strip()
        self.assertEqual(out, "-baked-long-option=underscore")

        out = python.bake(py.name, {"long-option": True},
                          _long_prefix="-baked-")().strip()
        self.assertEqual(out, "-baked-long-option")

    def test_command_wrapper(self):
        from sh import Command, which

        ls = Command(which("ls"))
        wc = Command(which("wc"))

        c1 = int(wc(ls("-A1"), l=True))  # noqa: E741
        c2 = len(os.listdir("."))

        self.assertEqual(c1, c2)

    def test_background(self):
        from sh import sleep
        import time

        start = time.time()
        sleep_time = .5
        p = sleep(sleep_time, _bg=True)

        now = time.time()
        self.assertLess(now - start, sleep_time)

        p.wait()
        now = time.time()
        self.assertGreater(now - start, sleep_time)

    def test_background_exception(self):
        from sh import ls, ErrorReturnCode_1, ErrorReturnCode_2
        p = ls("/ofawjeofj", _bg=True, _bg_exc=False)  # should not raise

        exc_to_test = ErrorReturnCode_2
        if IS_MACOS:
            exc_to_test = ErrorReturnCode_1
        self.assertRaises(exc_to_test, p.wait)  # should raise

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
        self.assertIn("with_context", out)
        self.assertIn(getpass.getuser(), out)

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

    def test_binary_input(self):
        py = create_tmp_test("""
import sys
data = sys.stdin.read()
sys.stdout.write(data)
""")
        data = b'1234'
        out = python(py.name, _in=data)
        self.assertEqual(out, "1234")

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
        self.assertEqual(stdout, "stdoutstderr")

    def test_err_to_out_and_sys_stdout(self):
        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stdout.flush()
sys.stderr.write("stderr")
sys.stderr.flush()
""")
        master, slave = os.pipe()
        stdout = python(py.name, _err_to_out=True, _out=slave)
        self.assertEqual(stdout, "")
        self.assertEqual(os.read(master, 12), b"stdoutstderr")

    def test_err_piped(self):
        py = create_tmp_test("""
import sys
sys.stderr.write("stderr")
""")

        py2 = create_tmp_test("""
import sys
while True:
    line = sys.stdin.read()
    if not line:
        break
    sys.stdout.write(line)
""")

        out = python(python("-u", py.name, _piped="err"), "-u", py2.name)
        self.assertEqual(out, "stderr")

    def test_out_redirection(self):
        import tempfile

        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")

        file_obj = tempfile.NamedTemporaryFile()
        out = python(py.name, _out=file_obj)

        self.assertEqual(len(out), 0)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertNotEqual(len(actual_out), 0)

        # test with tee
        file_obj = tempfile.NamedTemporaryFile()
        out = python(py.name, _out=file_obj, _tee=True)

        self.assertGreater(len(out), 0)

        file_obj.seek(0)
        actual_out = file_obj.read()
        file_obj.close()

        self.assertGreater(len(actual_out), 0)

    def test_err_redirection(self):
        import tempfile

        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
        file_obj = tempfile.NamedTemporaryFile()
        p = python("-u", py.name, _err=file_obj)

        file_obj.seek(0)
        stderr = file_obj.read().decode()
        file_obj.close()

        self.assertEqual(p.stdout, b"stdout")
        self.assertEqual(stderr, "stderr")
        self.assertEqual(len(p.stderr), 0)

        # now with tee
        file_obj = tempfile.NamedTemporaryFile()
        p = python(py.name, _err=file_obj, _tee="err")

        file_obj.seek(0)
        stderr = file_obj.read().decode()
        file_obj.close()

        self.assertEqual(p.stdout, b"stdout")
        self.assertEqual(stderr, "stderr")
        self.assertGreater(len(p.stderr), 0)

    def test_tty_tee(self):
        py = create_tmp_test("""
import sys
sys.stdout.write("stdout")
""")
        read, write = pty.openpty()
        out = python("-u", py.name, _out=write).stdout
        tee = os.read(read, 6)

        self.assertEqual(out, b"")
        self.assertEqual(tee, b"stdout")
        os.close(write)
        os.close(read)

        read, write = pty.openpty()
        out = python("-u", py.name, _out=write, _tee=True).stdout
        tee = os.read(read, 6)

        self.assertEqual(out, b"stdout")
        self.assertEqual(tee, b"stdout")
        os.close(write)
        os.close(read)

    def test_err_redirection_actual_file(self):
        import tempfile
        file_obj = tempfile.NamedTemporaryFile()
        py = create_tmp_test("""
import sys
import os

sys.stdout.write("stdout")
sys.stderr.write("stderr")
""")
        stdout = python("-u", py.name, _err=file_obj.name).wait()
        file_obj.seek(0)
        stderr = file_obj.read().decode()
        file_obj.close()
        self.assertTrue(stdout == "stdout")
        self.assertTrue(stderr == "stderr")

    def test_subcommand_and_bake(self):
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
        self.assertIn("subcommand", out)
        self.assertIn(getpass.getuser(), out)

    def test_multiple_bakes(self):
        py = create_tmp_test("""
import sys
sys.stdout.write(str(sys.argv[1:]))
""")

        out = python.bake(py.name).bake("bake1").bake("bake2")()
        self.assertEqual("['bake1', 'bake2']", out)

    def test_arg_preprocessor(self):
        py = create_tmp_test("""
import sys
sys.stdout.write(str(sys.argv[1:]))
""")

        def arg_preprocess(args, kwargs):
            args.insert(0, "preprocessed")
            kwargs["a-kwarg"] = 123
            return args, kwargs

        cmd = python.bake(py.name, _arg_preprocess=arg_preprocess)
        out = cmd("arg")
        self.assertEqual("['preprocessed', 'arg', '--a-kwarg=123']", out)

    def test_bake_args_come_first(self):
        from sh import ls
        ls = ls.bake(h=True)

        ran = ls("-la").ran
        ft = ran.index("-h")
        self.assertIn("-la", ran[ft:])

    def test_output_equivalence(self):
        from sh import whoami

        iam1 = whoami()
        iam2 = whoami()

        self.assertEqual(iam1, iam2)

    # https://github.com/amoffat/sh/pull/252
    def test_stdout_pipe(self):
        py = create_tmp_test(r"""
import sys

sys.stdout.write("foobar\n")
""")

        read_fd, write_fd = os.pipe()
        python(py.name, _out=write_fd, u=True)

        def alarm(sig, action):
            self.fail("Timeout while reading from pipe")

        import signal
        signal.signal(signal.SIGALRM, alarm)
        signal.alarm(3)

        data = os.read(read_fd, 100)
        self.assertEqual(b"foobar\n", data)
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

    def test_stdout_callback(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print(i)
""")
        stdout = []

        def agg(line):
            stdout.append(line)

        p = python("-u", py.name, _out=agg)
        p.wait()

        self.assertEqual(len(stdout), 5)

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

        python("-u", py.name, _out=agg, _bg=True)

        # we give a little pause to make sure that the NamedTemporaryFile
        # exists when the python process actually starts
        time.sleep(.5)

        self.assertNotEqual(len(stdout), 5)

    def test_stdout_callback_line_buffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print("herpderp")
""")

        stdout = []

        def agg(line): stdout.append(line)

        p = python("-u", py.name, _out=agg, _out_bufsize=1)
        p.wait()

        self.assertEqual(len(stdout), 5)

    def test_stdout_callback_line_unbuffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): print("herpderp")
""")

        stdout = []

        def agg(char): stdout.append(char)

        p = python("-u", py.name, _out=agg, _out_bufsize=0)
        p.wait()

        # + 5 newlines
        self.assertEqual(len(stdout), len("herpderp") * 5 + 5)

    def test_stdout_callback_buffered(self):
        py = create_tmp_test("""
import sys
import os

for i in range(5): sys.stdout.write("herpderp")
""")

        stdout = []

        def agg(chunk): stdout.append(chunk)

        p = python("-u", py.name, _out=agg, _out_bufsize=4)
        p.wait()

        self.assertEqual(len(stdout), len("herp") / 2 * 5)

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
            if line.strip() == "4":
                stdin.put("derp\n")

        p = python("-u", py.name, _out=agg, _tee=True)
        p.wait()

        self.assertIn("derp", p)

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
            if line == "2":
                return True

        p = python("-u", py.name, _out=agg, _tee=True)
        p.wait()

        self.assertIn("4", p)
        self.assertNotIn("4", stdout)

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

        import sh
        caught_signal = False
        try:
            p = python("-u", py.name, _out=agg, _bg=True)
            p.wait()
        except sh.SignalException_SIGTERM:
            caught_signal = True

        self.assertTrue(caught_signal)
        self.assertEqual(p.process.exit_code, -signal.SIGTERM)
        self.assertNotIn("4", p)
        self.assertNotIn("4", stdout)

    def test_stdout_callback_kill(self):
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
                process.kill()
                return True

        import sh
        caught_signal = False
        try:
            p = python("-u", py.name, _out=agg, _bg=True)
            p.wait()
        except sh.SignalException_SIGKILL:
            caught_signal = True

        self.assertTrue(caught_signal)
        self.assertEqual(p.process.exit_code, -signal.SIGKILL)
        self.assertNotIn("4", p)
        self.assertNotIn("4", stdout)

    def test_general_signal(self):
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
        self.assertEqual(len(out), 42)
        self.assertEqual(sum(out), 861)

    def test_iter_unicode(self):
        # issue https://github.com/amoffat/sh/issues/224
        test_string = "\xe4\xbd\x95\xe4\xbd\x95\n" * 150  # len > buffer_s
        txt = create_tmp_test(test_string)
        for line in sh.cat(txt.name, _iter=True):
            break
        self.assertLess(len(line), 1024)

    def test_nonblocking_iter(self):
        from errno import EWOULDBLOCK

        py = create_tmp_test("""
import time
import sys
time.sleep(1)
sys.stdout.write("stdout")
""")
        count = 0
        value = None
        for line in python(py.name, _iter_noblock=True):
            if line == EWOULDBLOCK:
                count += 1
            else:
                value = line
        self.assertGreater(count, 0)
        self.assertEqual(value, "stdout")

        py = create_tmp_test("""
import time
import sys
time.sleep(1)
sys.stderr.write("stderr")
""")

        count = 0
        value = None
        for line in python(py.name, _iter_noblock="err"):
            if line == EWOULDBLOCK:
                count += 1
            else:
                value = line
        self.assertGreater(count, 0)
        self.assertEqual(value, "stderr")

    def test_for_generator_to_err(self):
        py = create_tmp_test("""
import sys
import os

for i in range(42):
    sys.stderr.write(str(i)+"\\n")
""")

        out = []
        for line in python("-u", py.name, _iter="err"):
            out.append(line)
        self.assertEqual(len(out), 42)

        # verify that nothing is going to stdout
        out = []
        for line in python("-u", py.name, _iter="out"):
            out.append(line)
        self.assertEqual(len(out), 0)

    def test_sigpipe(self):
        py1 = create_tmp_test("""
import sys
import os
import time
import signal

# by default, python disables SIGPIPE, in favor of using IOError exceptions, so
# let's put that back to the system default where we terminate with a signal
# exit code
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

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
    if not line:
        break
    print(line.strip().upper())
    exit(0)
        """)

        p1 = python("-u", py1.name, _piped="out")
        p2 = python(p1, "-u", py2.name)

        # SIGPIPE should happen, but it shouldn't be an error, since _piped is
        # truthful
        self.assertEqual(-p1.exit_code, signal.SIGPIPE)
        self.assertEqual(p2.exit_code, 0)

    def test_piped_generator(self):
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
    if not line:
        break
    print(line.strip().upper())
        """)

        times = []
        last_received = None

        letters = ""
        for line in python(python("-u", py1.name, _piped="out"), "-u",
                           py2.name, _iter=True):
            letters += line.strip()

            now = time.time()
            if last_received:
                times.append(now - last_received)
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

        def agg(line):
            stderr.append(int(line.strip()))

        out = []
        for line in python("-u", py.name, _iter=True, _err=agg):
            out.append(line)

        self.assertEqual(len(out), 42)
        self.assertEqual(sum(stderr), 1722)

    def test_cast_bg(self):
        py = create_tmp_test("""
import sys
import time
time.sleep(0.5)
sys.stdout.write(sys.argv[1])
""")
        self.assertEqual(int(python(py.name, "123", _bg=True)), 123)
        self.assertEqual(long(python(py.name, "456", _bg=True)), 456)
        self.assertEqual(float(python(py.name, "789", _bg=True)), 789.0)

    def test_cmd_eq(self):
        py = create_tmp_test("")

        cmd1 = python.bake(py.name, "-u")
        cmd2 = python.bake(py.name, "-u")
        cmd3 = python.bake(py.name)

        self.assertEqual(cmd1, cmd2)
        self.assertNotEqual(cmd1, cmd3)

    def test_fg(self):
        py = create_tmp_test("exit(0)")
        # notice we're using `system_python`, and not `python`.  this is because
        # `python` has an env baked into it, and we want `_env` to be None for
        # coverage
        system_python(py.name, _fg=True)

    def test_fg_false(self):
        """ https://github.com/amoffat/sh/issues/520 """
        py = create_tmp_test("print('hello')")
        buf = StringIO()
        python(py.name, _fg=False, _out=buf)
        self.assertEqual(buf.getvalue(), "hello\n")

    def test_fg_true(self):
        """ https://github.com/amoffat/sh/issues/520 """
        py = create_tmp_test("print('hello')")
        buf = StringIO()
        self.assertRaises(TypeError, python, py.name, _fg=True, _out=buf)

    def test_fg_env(self):
        py = create_tmp_test("""
import os
code = int(os.environ.get("EXIT", "0"))
exit(code)
""")

        env = os.environ.copy()
        env["EXIT"] = "3"
        self.assertRaises(sh.ErrorReturnCode_3, python, py.name, _fg=True,
                          _env=env)

    def test_fg_alternative(self):
        py = create_tmp_test("exit(0)")
        python(py.name, _in=sys.stdin, _out=sys.stdout, _err=sys.stderr)

    def test_fg_exc(self):
        py = create_tmp_test("exit(1)")
        self.assertRaises(sh.ErrorReturnCode_1, python, py.name, _fg=True)

    def test_out_filename(self):
        outfile = tempfile.NamedTemporaryFile()
        py = create_tmp_test("print('output')")
        python(py.name, _out=outfile.name)
        outfile.seek(0)
        self.assertEqual(b"output\n", outfile.read())

    def test_bg_exit_code(self):
        py = create_tmp_test("""
import time
time.sleep(1)
exit(49)
""")
        p = python(py.name, _ok_code=49, _bg=True)
        self.assertEqual(49, p.exit_code)

    def test_cwd(self):
        from sh import pwd
        from os.path import realpath
        self.assertEqual(str(pwd(_cwd="/tmp")), realpath("/tmp") + "\n")
        self.assertEqual(str(pwd(_cwd="/etc")), realpath("/etc") + "\n")

    def test_cwd_fg(self):
        td = realpath(tempfile.mkdtemp())
        py = create_tmp_test("""
import sh
import os
from os.path import realpath
orig = realpath(os.getcwd())
print(orig)
sh.pwd(_cwd="{newdir}", _fg=True)
print(realpath(os.getcwd()))
""".format(newdir=td))

        orig, newdir, restored = python(py.name).strip().split("\n")
        newdir = realpath(newdir)
        self.assertEqual(newdir, td)
        self.assertEqual(orig, restored)
        self.assertNotEqual(orig, newdir)
        os.rmdir(td)

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
            if not line:
                return

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

        out = StringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue(), "testing 123")

        out = cStringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue().decode(), "testing 123")

        out = ioStringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue(), "testing 123")

        out = iocStringIO()
        echo("-n", "testing 123", _out=out)
        self.assertEqual(out.getvalue().decode(), "testing 123")

    def test_stringio_input(self):
        from sh import cat

        input = StringIO()
        input.write("herpderp")
        input.seek(0)

        out = cat(_in=input)
        self.assertEqual(out, "herpderp")

    def test_internal_bufsize(self):
        from sh import cat

        output = cat(_in="a" * 1000, _internal_bufsize=100, _out_bufsize=0)
        self.assertEqual(len(output), 100)

        output = cat(_in="a" * 1000, _internal_bufsize=50, _out_bufsize=2)
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
            if not line:
                return

            if line == "switch buffering":
                d["newline_buffer_success"] = True
                process.change_out_bufsize(0)
                stdin.put("a")

            elif line == "unbuffered":
                stdin.put("b")
                d["unbuffered_success"] = True
                return True

        # start with line buffered stdout
        pw_stars = python("-u", py.name, _out=interact, _out_bufsize=1)
        pw_stars.wait()

        self.assertTrue(d["newline_buffer_success"])
        self.assertTrue(d["unbuffered_success"])

    def test_callable_interact(self):
        py = create_tmp_test("""
import sys
sys.stdout.write("line1")
""")

        class Callable(object):
            def __init__(self):
                self.line = None

            def __call__(self, line):
                self.line = line

        cb = Callable()
        python(py.name, _out=cb)
        self.assertEqual(cb.line, "line1")

    def test_encoding(self):
        return self.skipTest("what's the best way to test a different '_encoding' special keyword argument?")

    def test_timeout(self):
        import sh
        from time import time

        sleep_for = 3
        timeout = 1
        started = time()
        try:
            sh.sleep(sleep_for, _timeout=timeout).wait()
        except sh.TimeoutException as e:
            assert 'sleep 3' in e.full_cmd
        else:
            self.fail("no timeout exception")
        elapsed = time() - started
        self.assertLess(abs(elapsed - timeout), 0.5)

    def test_timeout_overstep(self):
        started = time.time()
        sh.sleep(1, _timeout=5)
        elapsed = time.time() - started
        self.assertLess(abs(elapsed - 1), 0.5)

    def test_timeout_wait(self):
        p = sh.sleep(3, _bg=True)
        self.assertRaises(sh.TimeoutException, p.wait, timeout=1)

    def test_timeout_wait_overstep(self):
        p = sh.sleep(1, _bg=True)
        p.wait(timeout=5)

    def test_timeout_wait_negative(self):
        p = sh.sleep(3, _bg=True)
        self.assertRaises(RuntimeError, p.wait, timeout=-3)

    def test_binary_pipe(self):
        binary = b'\xec;\xedr\xdbF'

        py1 = create_tmp_test("""
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
sys.stdout.write(b'\\xec;\\xedr\\xdbF')
""")

        py2 = create_tmp_test("""
import sys
import os

sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
sys.stdout.write(sys.stdin.read())
""")
        out = python(python(py1.name), py2.name)
        self.assertEqual(out.stdout, binary)

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

    def test_tty_stdin(self):
        py = create_tmp_test("""
import sys
sys.stdout.write(sys.stdin.read())
sys.stdout.flush()
""")
        out = python(py.name, _in="test\n", _tty_in=True)
        self.assertEqual("test\n", out)

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

    def test_signal_group(self):
        child = create_tmp_test("""
import time
time.sleep(3)
""")

        parent = create_tmp_test("""
import sys
import sh
python = sh.Command(sys.executable)
p = python("{child_file}", _bg=True, _new_session=False)
print(p.pid)
print(p.process.pgid)
p.wait()
""", child_file=child.name)

        def launch():
            p = python(parent.name, _bg=True, _iter=True)
            child_pid = int(next(p).strip())
            child_pgid = int(next(p).strip())
            parent_pid = p.pid
            parent_pgid = p.process.pgid

            return p, child_pid, child_pgid, parent_pid, parent_pgid

        def assert_alive(pid):
            os.kill(pid, 0)

        def assert_dead(pid):
            self.assert_oserror(errno.ESRCH, os.kill, pid, 0)

        # first let's prove that calling regular SIGKILL on the parent does
        # nothing to the child, since the child was launched in the same process
        # group (_new_session=False) and the parent is not a controlling process
        p, child_pid, child_pgid, parent_pid, parent_pgid = launch()

        assert_alive(parent_pid)
        assert_alive(child_pid)

        p.kill()
        time.sleep(0.1)
        assert_dead(parent_pid)
        assert_alive(child_pid)

        self.assertRaises(sh.SignalException_SIGKILL, p.wait)
        assert_dead(child_pid)

        # now let's prove that killing the process group kills both the parent
        # and the child
        p, child_pid, child_pgid, parent_pid, parent_pgid = launch()

        assert_alive(parent_pid)
        assert_alive(child_pid)

        p.kill_group()
        time.sleep(0.1)
        assert_dead(parent_pid)
        assert_dead(child_pid)

    def test_pushd(self):
        """ test basic pushd functionality """
        old_wd1 = sh.pwd().strip()
        old_wd2 = os.getcwd()

        self.assertEqual(old_wd1, old_wd2)
        self.assertNotEqual(old_wd1, tempdir)

        with sh.pushd(tempdir):
            new_wd1 = sh.pwd().strip()
            new_wd2 = os.getcwd()

        old_wd3 = sh.pwd().strip()
        old_wd4 = os.getcwd()
        self.assertEqual(old_wd3, old_wd4)
        self.assertEqual(old_wd1, old_wd3)

        self.assertEqual(new_wd1, tempdir)
        self.assertEqual(new_wd2, tempdir)

    def test_pushd_cd(self):
        """ test that pushd works like pushd/popd with built-in cd correctly """
        import sh

        child = realpath(tempfile.mkdtemp())
        try:
            old_wd = os.getcwd()
            with sh.pushd(tempdir):
                self.assertEqual(tempdir, os.getcwd())
                sh.cd(child)
                self.assertEqual(child, os.getcwd())

            self.assertEqual(old_wd, os.getcwd())
        finally:
            os.rmdir(child)

    def test_cd_homedir(self):
        orig = os.getcwd()
        my_dir = os.path.realpath(os.path.expanduser("~"))  # Use realpath because homedir may be a symlink
        sh.cd()

        self.assertNotEqual(orig, os.getcwd())
        self.assertEqual(my_dir, os.getcwd())

    def test_non_existant_cwd(self):
        from sh import ls

        # sanity check
        non_exist_dir = join(tempdir, "aowjgoahewro")
        self.assertFalse(exists(non_exist_dir))
        self.assertRaises(sh.ForkException, ls, _cwd=non_exist_dir)

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
                self.success = None

            def __call__(self, p, success, exit_code):
                self.called = True
                self.exit_code = exit_code
                self.success = success

        py = create_tmp_test("""
from time import time, sleep
sleep(1)
print(time())
""")

        callback = Callback()
        p = python(py.name, _done=callback, _bg=True)

        # do a little setup to prove that a command with a _done callback is run
        # in the background
        wait_start = time.time()
        p.wait()
        wait_elapsed = time.time() - wait_start

        self.assertTrue(callback.called)
        self.assertLess(abs(wait_elapsed - 1.0), 1.0)
        self.assertEqual(callback.exit_code, 0)
        self.assertTrue(callback.success)

    def test_fork_exc(self):
        from sh import ForkException

        py = create_tmp_test("")

        def fail():
            raise RuntimeError("nooo")

        self.assertRaises(ForkException, python, py.name, _preexec_fn=fail)

    def test_new_session(self):
        from threading import Event

        py = create_tmp_test("""
import os
import time
pid = os.getpid()
pgid = os.getpgid(pid)
sid = os.getsid(pid)
stuff = [pid, pgid, sid]

print(",".join([str(el) for el in stuff]))
time.sleep(0.5)
""")

        event = Event()

        def handle(line, stdin, p):
            pid, pgid, sid = line.strip().split(",")
            pid = int(pid)
            pgid = int(pgid)
            sid = int(sid)

            self.assertEqual(p.pid, pid)
            self.assertEqual(pid, pgid)
            self.assertEqual(p.pgid, pgid)
            self.assertEqual(pgid, p.get_pgid())
            self.assertEqual(pid, sid)
            self.assertEqual(sid, pgid)
            self.assertEqual(p.sid, sid)
            self.assertEqual(sid, p.get_sid())

            event.set()

        # new session
        p = python(py.name, _out=handle)
        p.wait()
        self.assertTrue(event.is_set())

        event.clear()

        def handle(line, stdin, p):
            pid, pgid, sid = line.strip().split(",")
            pid = int(pid)
            pgid = int(pgid)
            sid = int(sid)

            test_pid = os.getpgid(os.getpid())

            self.assertEqual(p.pid, pid)
            self.assertNotEqual(test_pid, pgid)
            self.assertEqual(p.pgid, pgid)
            self.assertEqual(pgid, p.get_pgid())
            self.assertNotEqual(pid, sid)
            self.assertNotEqual(sid, pgid)
            self.assertEqual(p.sid, sid)
            self.assertEqual(sid, p.get_sid())

            event.set()

        # no new session
        p = python(py.name, _out=handle, _new_session=False)
        p.wait()
        self.assertTrue(event.is_set())

    def test_done_cb_exc(self):
        from sh import ErrorReturnCode

        class Callback(object):
            def __init__(self):
                self.called = False
                self.success = None

            def __call__(self, p, success, exit_code):
                self.success = success
                self.called = True

        py = create_tmp_test("exit(1)")

        callback = Callback()
        try:
            p = python(py.name, _done=callback, _bg=True)
            p.wait()
        except ErrorReturnCode:
            self.assertTrue(callback.called)
            self.assertFalse(callback.success)
        else:
            self.fail("command should've thrown an exception")

    def test_callable_stdin(self):
        py = create_tmp_test("""
import sys
sys.stdout.write(sys.stdin.read())
""")

        def create_stdin():
            state = {"count": 0}

            def stdin():
                count = state["count"]
                if count == 4:
                    return None
                state["count"] += 1
                return str(count)

            return stdin

        out = python(py.name, _in=create_stdin())
        self.assertEqual("0123", out)

    def test_stdin_unbuffered_bufsize(self):
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
            yield "test"
            sleep(1)
            yield "ing"
            sleep(1)
            yield "done"

        out = python(py.name, _in=create_stdin(), _in_bufsize=0)
        word1, time1, word2, time2, _ = out.split("\n")
        time1 = float(time1)
        time2 = float(time2)
        self.assertEqual(word1, "testing")
        self.assertLess(abs(1 - time1), 0.5)
        self.assertEqual(word2, "done")
        self.assertLess(abs(1 - time2), 0.5)

    def test_stdin_newline_bufsize(self):
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
            yield "test"
            sleep(1)
            yield "ing\n"
            sleep(1)
            yield "done\n"

        out = python(py.name, _in=create_stdin(), _in_bufsize=1)
        word1, time1, word2, time2, _ = out.split("\n")
        time1 = float(time1)
        time2 = float(time2)
        self.assertEqual(word1, "testing")
        self.assertLess(abs(1 - time1), 0.5)
        self.assertEqual(word2, "done")
        self.assertLess(abs(1 - time2), 0.5)

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

    def test_append_stdout(self):
        py = create_tmp_test("""
import sys
num = sys.stdin.read()
sys.stdout.write(num)
""")
        append_file = tempfile.NamedTemporaryFile(mode="a+b")
        python(py.name, _in="1", _out=append_file)
        python(py.name, _in="2", _out=append_file)
        append_file.seek(0)
        output = append_file.read()
        self.assertEqual(b"12", output)

    def test_shadowed_subcommand(self):
        py = create_tmp_test("""
import sys
sys.stdout.write(sys.argv[1])
""")
        out = python.bake(py.name).bake_()
        self.assertEqual("bake", out)

    def test_no_proc_no_attr(self):
        py = create_tmp_test("")
        with python(py.name) as p:
            self.assertRaises(AttributeError, getattr, p, "exit_code")

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
        python(py.name, _out=log_line)
        self.assertEqual(output, [("hello", i) for i in range(10)])

        output = []

        def fn(foo, line, stdin, proc):
            output.append((foo, int(line.strip())))

        log_line = partial(fn, "hello")
        python(py.name, _out=log_line)
        self.assertEqual(output, [("hello", i) for i in range(10)])

    # https://github.com/amoffat/sh/issues/266
    def test_grandchild_no_sighup(self):
        import time

        # child process that will write to a file if it receives a SIGHUP
        child = create_tmp_test("""
import signal
import sys
import time

output_file = sys.argv[1]
with open(output_file, "w") as f:
    def handle_sighup(signum, frame):
        f.write("got signal %d" % signum)
        sys.exit(signum)
    signal.signal(signal.SIGHUP, handle_sighup)
    time.sleep(2)
    f.write("made it!\\n")
""")

        # the parent that will terminate before the child writes to the output
        # file, potentially causing a SIGHUP
        parent = create_tmp_test("""
import os
import time
import sys

child_file = sys.argv[1]
output_file = sys.argv[2]

python_name = os.path.basename(sys.executable)
os.spawnlp(os.P_NOWAIT, python_name, python_name, child_file, output_file)
time.sleep(1) # give child a chance to set up
""")

        output_file = tempfile.NamedTemporaryFile(delete=True)
        python(parent.name, child.name, output_file.name)
        time.sleep(3)

        out = output_file.readlines()[0]
        self.assertEqual(out, b"made it!\n")

    def test_unchecked_producer_failure(self):
        from sh import ErrorReturnCode_2

        producer = create_tmp_test("""
import sys
for i in range(10):
    print(i)
sys.exit(2)
""")

        consumer = create_tmp_test("""
import sys
for line in sys.stdin:
    pass
""")

        direct_pipe = python(producer.name, _piped=True)
        self.assertRaises(ErrorReturnCode_2, python, direct_pipe, consumer.name)

    def test_unchecked_pipeline_failure(self):
        # similar to test_unchecked_producer_failure, but this
        # tests a multi-stage pipeline

        from sh import ErrorReturnCode_2

        producer = create_tmp_test("""
import sys
for i in range(10):
    print(i)
sys.exit(2)
""")

        middleman = create_tmp_test("""
import sys
for line in sys.stdin:
    print("> " + line)
""")

        consumer = create_tmp_test("""
import sys
for line in sys.stdin:
    pass
""")

        producer_normal_pipe = python(producer.name, _piped=True)
        middleman_normal_pipe = python(producer_normal_pipe, middleman.name, _piped=True)
        self.assertRaises(ErrorReturnCode_2, python, middleman_normal_pipe, consumer.name)


@skip_unless(HAS_MOCK, "requires unittest.mock")
class MockTests(BaseTests):

    def test_patch_command_cls(self):
        def fn():
            cmd = sh.Command("afowejfow")
            return cmd()

        @unittest.mock.patch("sh.Command")
        def test(Command):
            Command().return_value = "some output"
            return fn()

        self.assertEqual(test(), "some output")
        self.assertRaises(sh.CommandNotFound, fn)

    def test_patch_command(self):
        def fn():
            return sh.afowejfow()

        @unittest.mock.patch("sh.afowejfow", create=True)
        def test(cmd):
            cmd.return_value = "some output"
            return fn()

        self.assertEqual(test(), "some output")
        self.assertRaises(sh.CommandNotFound, fn)


class MiscTests(BaseTests):
    def test_pickling(self):
        import pickle

        py = create_tmp_test("""
import sys
sys.stdout.write("some output")
sys.stderr.write("some error")
exit(1)
""")

        try:
            python(py.name)
        except sh.ErrorReturnCode as e:
            restored = pickle.loads(pickle.dumps(e))
            self.assertEqual(restored.stdout, b"some output")
            self.assertEqual(restored.stderr, b"some error")
            self.assertEqual(restored.exit_code, 1)
        else:
            self.fail("Didn't get an exception")

    @requires_poller("poll")
    def test_fd_over_1024(self):
        py = create_tmp_test("""print("hi world")""")

        with ulimit(resource.RLIMIT_NOFILE, 2048):
            cutoff_fd = 1024
            pipes = []
            for i in xrange(cutoff_fd):
                master, slave = os.pipe()
                pipes.append((master, slave))
                if slave >= cutoff_fd:
                    break

            python(py.name)
            for master, slave in pipes:
                os.close(master)
                os.close(slave)

    def test_args_deprecated(self):
        self.assertRaises(DeprecationWarning, sh.args, _env={})

    def test_percent_doesnt_fail_logging(self):
        """ test that a command name doesn't interfere with string formatting in
        the internal loggers """
        py = create_tmp_test("""
print("cool")
""")
        python(py.name, "%")
        python(py.name, "%%")
        python(py.name, "%%%")

    # TODO
    # for some reason, i can't get a good stable baseline measured in this test
    # on osx.  so skip it for now if osx
    @not_macos
    @requires_progs("lsof")
    def test_no_fd_leak(self):
        import sh
        import os
        from itertools import product

        # options whose combinations can possibly cause fd leaks
        kwargs = {
            "_tty_out": (True, False),
            "_tty_in": (True, False),
            "_err_to_out": (True, False),
        }

        def get_opts(possible_values):
            all_opts = []
            for opt, values in possible_values.items():
                opt_collection = []
                all_opts.append(opt_collection)

                for val in values:
                    pair = (opt, val)
                    opt_collection.append(pair)

            for combo in product(*all_opts):
                opt_dict = {}
                for key, val in combo:
                    opt_dict[key] = val
                yield opt_dict

        test_pid = os.getpid()

        def get_num_fds():
            lines = sh.lsof(p=test_pid).strip().split("\n")

            def test(line):
                line = line.upper()
                return "CHR" in line or "PIPE" in line

            lines = [line for line in lines if test(line)]
            return len(lines) - 1

        py = create_tmp_test("")

        def test_command(**opts):
            python(py.name, **opts)

        # make sure our baseline is stable.. we can remove this
        test_command()
        baseline = get_num_fds()
        for i in xrange(10):
            test_command()
            num_fds = get_num_fds()
            self.assertEqual(baseline, num_fds)

        for opts in get_opts(kwargs):
            for i in xrange(2):
                test_command(**opts)
                num_fds = get_num_fds()
                self.assertEqual(baseline, num_fds, (baseline, num_fds, opts))

    def test_pushd_thread_safety(self):
        import threading
        import time

        temp1 = realpath(tempfile.mkdtemp())
        temp2 = realpath(tempfile.mkdtemp())
        try:
            results = [None, None]

            def fn1():
                with sh.pushd(temp1):
                    time.sleep(0.2)
                    results[0] = realpath(os.getcwd())

            def fn2():
                time.sleep(0.1)
                with sh.pushd(temp2):
                    results[1] = realpath(os.getcwd())
                    time.sleep(0.3)

            t1 = threading.Thread(name="t1", target=fn1)
            t2 = threading.Thread(name="t2", target=fn2)

            t1.start()
            t2.start()

            t1.join()
            t2.join()

            self.assertEqual(results, [temp1, temp2])
        finally:
            os.rmdir(temp1)
            os.rmdir(temp2)

    def test_stdin_nohang(self):
        py = create_tmp_test("""
print("hi")
""")
        read, write = os.pipe()
        stdin = os.fdopen(read, "r")
        python(py.name, _in=stdin)

    @requires_utf8
    def test_unicode_path(self):
        from sh import Command

        python_name = os.path.basename(sys.executable)
        py = create_tmp_test("""#!/usr/bin/env {0}
# -*- coding: utf8 -*-
print("字")
""".format(python_name), prefix="字", delete=False)

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

    def test_change_log_message(self):
        py = create_tmp_test("""
print("cool")
""")

        def log_msg(cmd, call_args, pid=None):
            return "Hi! I ran something"

        buf = StringIO()
        handler = logging.StreamHandler(buf)
        logger = logging.getLogger("sh")
        logger.setLevel(logging.INFO)

        try:
            logger.addHandler(handler)
            python(py.name, "meow", "bark", _log_msg=log_msg)
        finally:
            logger.removeHandler(handler)

        loglines = buf.getvalue().split("\n")
        self.assertTrue(loglines, "Log handler captured no messages?")
        self.assertTrue(loglines[0].startswith("Hi! I ran something"))

    # https://github.com/amoffat/sh/issues/273
    def test_stop_iteration_doesnt_block(self):
        """ proves that calling calling next() on a stopped iterator doesn't
        hang. """
        py = create_tmp_test("""
print("cool")
""")
        p = python(py.name, _iter=True)
        for i in range(100):
            try:
                next(p)
            except StopIteration:
                pass

    # https://github.com/amoffat/sh/issues/195
    def test_threaded_with_contexts(self):
        import threading
        import time

        py = create_tmp_test("""
import sys
a = sys.argv
res = (a[1], a[3])
sys.stdout.write(repr(res))
""")

        p1 = python.bake("-u", py.name, 1)
        p2 = python.bake("-u", py.name, 2)
        results = [None, None]

        def f1():
            with p1:
                time.sleep(1)
                results[0] = str(system_python("one"))

        def f2():
            with p2:
                results[1] = str(system_python("two"))

        t1 = threading.Thread(target=f1)
        t1.start()

        t2 = threading.Thread(target=f2)
        t2.start()

        t1.join()
        t2.join()

        correct = [
            "('1', 'one')",
            "('2', 'two')",
        ]
        self.assertEqual(results, correct)

    # https://github.com/amoffat/sh/pull/292
    def test_eintr(self):
        import signal

        def handler(num, frame): pass

        signal.signal(signal.SIGALRM, handler)

        py = create_tmp_test("""
import time
time.sleep(2)
""")
        p = python(py.name, _bg=True)
        signal.alarm(1)
        p.wait()


class StreamBuffererTests(unittest.TestCase):
    def test_unbuffered(self):
        from sh import StreamBufferer
        b = StreamBufferer(0)

        self.assertEqual(b.process(b"test"), [b"test"])
        self.assertEqual(b.process(b"one"), [b"one"])
        self.assertEqual(b.process(b""), [b""])
        self.assertEqual(b.flush(), b"")

    def test_newline_buffered(self):
        from sh import StreamBufferer
        b = StreamBufferer(1)

        self.assertEqual(b.process(b"testing\none\ntwo"), [b"testing\n", b"one\n"])
        self.assertEqual(b.process(b"\nthree\nfour"), [b"two\n", b"three\n"])
        self.assertEqual(b.flush(), b"four")

    def test_chunk_buffered(self):
        from sh import StreamBufferer
        b = StreamBufferer(10)

        self.assertEqual(b.process(b"testing\none\ntwo"), [b"testing\non"])
        self.assertEqual(b.process(b"\nthree\n"), [b"e\ntwo\nthre"])
        self.assertEqual(b.flush(), b"e\n")


@requires_posix
class ExecutionContextTests(unittest.TestCase):
    def test_basic(self):
        import sh
        out = StringIO()
        _sh = sh(_out=out)
        _sh.echo("-n", "TEST")
        self.assertEqual("TEST", out.getvalue())

    def test_no_interfere1(self):
        import sh
        out = StringIO()
        _sh = sh(_out=out)  # noqa: F841
        from _sh import echo
        echo("-n", "TEST")
        self.assertEqual("TEST", out.getvalue())

        # Emptying the StringIO
        out.seek(0)
        out.truncate(0)

        sh.echo("-n", "KO")
        self.assertEqual("", out.getvalue())

    def test_no_interfere2(self):
        import sh
        out = StringIO()
        from sh import echo
        _sh = sh(_out=out)  # noqa: F841
        echo("-n", "TEST")
        self.assertEqual("", out.getvalue())

    def test_no_bad_name(self):
        out = StringIO()

        def fn():
            import sh
            sh = sh(_out=out)

        self.assertRaises(RuntimeError, fn)

    def test_set_in_parent_function(self):
        import sh
        out = StringIO()
        _sh = sh(_out=out)

        def nested1():
            _sh.echo("-n", "TEST1")

        def nested2():
            import sh
            sh.echo("-n", "TEST2")

        nested1()
        nested2()
        self.assertEqual("TEST1", out.getvalue())

    def test_reimport_no_interfere(self):
        import sh
        out = StringIO()
        _sh = sh(_out=out)
        import _sh  # this reimport '_sh' from the eponymous local variable
        _sh.echo("-n", "TEST")
        self.assertEqual("TEST", out.getvalue())

    def test_command_with_baked_call_args(self):
        # Test that sh.Command() knows about baked call args
        import sh
        _sh = sh(_ok_code=1)
        self.assertEqual(sh.Command._call_args['ok_code'], 0)
        self.assertEqual(_sh.Command._call_args['ok_code'], 1)

    def test_importer_detects_module_name(self):
        import sh
        _sh = sh()
        omg = _sh  # noqa: F841
        from omg import cat  # noqa: F401

    def test_importer_only_works_with_sh(self):
        def unallowed_import():
            _os = os  # noqa: F841
            from _os import path  # noqa: F401

        self.assertRaises(ImportError, unallowed_import)

    def test_reimport_from_cli(self):
        # The REPL and CLI both need special handling to create an execution context that is safe to
        # reimport
        if IS_PY3:
            cmdstr = '; '.join(('import sh, io, sys',
                                'out = io.StringIO()',
                                '_sh = sh(_out=out)',
                                'import _sh',
                                '_sh.echo("-n", "TEST")',
                                'sys.stderr.write(out.getvalue())',
                                ))
        else:
            cmdstr = '; '.join(('import sh, StringIO, sys',
                                'out = StringIO.StringIO()',
                                '_sh = sh(_out=out)',
                                'import _sh',
                                '_sh.echo("-n", "TEST")',
                                'sys.stderr.write(out.getvalue())',
                                ))

        err = StringIO()

        python('-c', cmdstr, _err=err)
        self.assertEqual('TEST', err.getvalue())


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(NullHandler())

    test_kwargs = {}

    if IS_PY2 and MINOR_VER != 6:
        test_kwargs["failfast"] = True
        test_kwargs["verbosity"] = 2

    try:
        # if we're running a specific test, we can let unittest framework figure out
        # that test and run it itself.  it will also handle setting the return code
        # of the process if any tests error or fail
        if len(sys.argv) > 1:
            unittest.main(**test_kwargs)

        # otherwise, it looks like we want to run all the tests
        else:
            suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
            test_kwargs["verbosity"] = 2
            result = unittest.TextTestRunner(**test_kwargs).run(suite)

            if not result.wasSuccessful():
                exit(1)

    finally:
        if cov:
            cov.stop()
            cov.save()
