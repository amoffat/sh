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
        test = "漢字".decode("utf8")
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
    
    def test_list_arg(self):
        from pbs import python
        
        py = create_tmp_test("""
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-l", dest="list_arg")
options, args = parser.parse_args()
print options.list_arg
""")
        
        out = python(py.name, l=[1, 2, 3]).strip()
        self.assertEqual(out, "1 2 3")
    
    def test_quote_escaping(self):
        raise NotImplementedError
    
    def test_multiple_pipes(self):
        raise NotImplementedError
    
    def test_environment(self):
        from pbs import python
        import os
        
        env_value = "DERP"
        
        py = create_tmp_test("""
import os
print os.environ["HERP"]
""")
        os.environ["HERP"] = env_value
        out = python(py.name).strip()
        self.assertEqual(out, env_value)
    
        py = create_tmp_test("""
import pbs
print pbs.HERP
""")
        out = python(py.name).strip()
        self.assertEqual(out, env_value)
        
    
    def test_which(self):
        from pbs import which, ls
        self.assertEqual(which("fjoawjefojawe"), None)
        self.assertEqual(which("ls"), str(ls))
        
        
    def test_foreground(self):
        raise NotImplementedError
    
    def test_no_arg(self):
        import pwd
        from pbs import whoami
        u1 = whoami().strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)

    def test_incompatible_special_args(self):
        from pbs import ls
        self.assertRaises(TypeError, ls, _fg=True, _bg=True)
            
            
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
        
        num_args = int(python(py.name, "-l", "one's two's three's"))
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
        self.assertEqual(c1, c2)
        
    def test_incremental_composition(self):
        from pbs import ls, wc
        c1 = int(wc(ls("-A1"), l=True, _piped=True))
        c2 = len(os.listdir("."))
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
        
    def test_background_exception(self):
        raise NotImplementedError
                
    
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
        
        self.assertTrue(len(out) != 0)

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


    def test_bake_args_come_first(self):
        from pbs import ls
        ls = ls.bake(full_time=True)
        
        ran = ls("-la").ran
        ft = ran.index("full-time")
        self.assertTrue("-la" in ran[ft:]) 

    
    def test_output_equivalence(self):
        from pbs import whoami

        iam1 = whoami()
        iam2 = whoami()

        self.assertEqual(iam1, iam2)


    def test_stdout_callback(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): print i
""")
        stdout = []
        def agg(line):
            stdout.append(line)
        
        p = python(py.name, _out=agg)
        p.wait()
        
        self.assertTrue(len(stdout) == 5)
        
        
        
    def test_stdout_callback_no_wait(self):
        from pbs import python
        import time
        
        py = create_tmp_test("""
import sys
import os
import time

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5):
    print i
    time.sleep(.5)
""")
        
        stdout = []
        def agg(line): stdout.append(line)
        
        p = python(py.name, _out=agg)
        
        # we give a little pause to make sure that the NamedTemporaryFile
        # exists when the python process actually starts
        time.sleep(.5)
        
        self.assertTrue(len(stdout) != 5)
        
        
        
    def test_stdout_callback_line_buffered(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): print "herpderp"
""")
        
        stdout = []
        def agg(line): stdout.append(line)
        
        p = python(py.name, _out=agg, _bufsize=1)
        p.wait()
        
        self.assertTrue(len(stdout) == 5)
        
        
        
    def test_stdout_callback_line_unbuffered(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): print "herpderp"
""")
        
        stdout = []
        def agg(char): stdout.append(char)
        
        p = python(py.name, _out=agg, _bufsize=0)
        p.wait()
        
        # + 5 newlines
        self.assertTrue(len(stdout) == (len("herpderp") * 5 + 5))
        
        
    def test_stdout_callback_buffered(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): sys.stdout.write("herpderp")
""")
        
        stdout = []
        def agg(chunk): stdout.append(chunk)
        
        p = python(py.name, _out=agg, _bufsize=4)
        p.wait()

        self.assertTrue(len(stdout) == (len("herp")/2 * 5))
        
        
        
    def test_stdout_callback_with_input(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): print i
derp = raw_input("herp? ")
print derp
""")
        
        def agg(line, stdin):
            if line.strip() == "4": stdin.put("derp\n")
        
        p = python(py.name, _out=agg)
        p.wait()
        
        self.assertTrue("derp" in p)
        
        
        
    def test_stdout_callback_exit(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): print i
""")
        
        stdout = []
        def agg(line):
            line = line.strip()
            stdout.append(line)
            if line == "2": return True
        
        p = python(py.name, _out=agg)
        p.wait()
        
        self.assertTrue("4" in p)
        self.assertTrue("4" not in stdout)
        
        
        
    def test_stdout_callback_terminate(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os
import time

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): 
    print i
    time.sleep(.5)
""")
        
        stdout = []
        def agg(line, stdin, process):
            line = line.strip()
            stdout.append(line)
            if line == "0":
                process.terminate()
                return True
        
        p = python(py.name, _out=agg)
        p.wait()
        
        self.assertTrue("4" not in p)
        self.assertTrue("4" not in stdout)
        
        
        
    def test_stdout_callback_kill(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os
import time

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for i in xrange(5): 
    print i
    time.sleep(.5)
""")
        
        stdout = []
        def agg(line, stdin, process):
            line = line.strip()
            stdout.append(line)
            if line == "0":
                process.kill()
                return True
        
        p = python(py.name, _out=agg)
        p.wait()
        
        self.assertTrue("4" not in p)
        self.assertTrue("4" not in stdout)
        
        
    def test_for_generator(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

for i in xrange(42): 
    print i
""")

        out = []
        for line in python(py.name, _for=True): out.append(line)
        self.assertTrue(len(out) == 42)
        
       
    def test_nonblocking_for(self):
        raise NotImplementedError
        
    def test_for_generator_to_err(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

for i in xrange(42): 
    sys.stderr.write(str(i)+"\\n")
""")

        out = []
        for line in python(py.name, _for="err"): out.append(line)
        self.assertTrue(len(out) == 42)



    def test_piped_generator(self):
        from pbs import python, tr
        from string import ascii_uppercase
        import time
        
        py1 = create_tmp_test("""
import sys
import os
from string import ascii_lowercase
import time

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

for letter in ascii_lowercase:
    time.sleep(0.03)
    print letter
        """)
        
        py2 = create_tmp_test("""
import sys
import os
from string import ascii_lowercase
import time

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

while True:
    line = sys.stdin.readline()
    if not line: break
    print line.strip().upper()
        """)
        
        letters = ""
        for line in python(python(py1.name, _piped="out"), py2.name, _for=True):
            if not letters: start = time.time()
            letters += line.strip()
            if len(letters) == 13: half_elapsed = time.time() - start
        
        self.assertEqual(ascii_uppercase, letters)
        self.assertTrue(.3 < half_elapsed < .4)
        
        
    def test_generator_and_callback(self):
        from pbs import python
        
        py = create_tmp_test("""
import sys
import os

# unbuffered stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

for i in xrange(42):
    sys.stderr.write(str(i * 2)+"\\n") 
    print i
""")
        
        stderr = []
        def agg(line): stderr.append(int(line.strip()))

        out = []
        for line in python(py.name, _for=True, _err=agg): out.append(line)
        
        self.assertTrue(len(out) == 42)
        self.assertTrue(sum(stderr) == 1722)



if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(Basic)
        unittest.TextTestRunner(verbosity=2).run(suite)
