import os
import unittest


requires_posix = unittest.skipUnless(os.name == "posix", "Requires POSIX")


class PbsTestSuite(unittest.TestCase):
    @requires_posix
    def test_print_command(self):
        from pbs import ls, which
        actual_location = which("ls")
        out = str(ls)
        self.assertEqual(out, actual_location)

    @requires_posix
    def test_which(self):
        from pbs import which, ls
        self.assertEqual(which("fjoawjefojawe"), None)
        self.assertEqual(which("ls"), str(ls))
        
    @requires_posix
    def test_no_arg(self):
        import pwd
        from pbs import whoami
        u1 = unicode(whoami()).strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)

    @requires_posix
    def test_short_bool_option(self):
        from pbs import id
        i1 = int(id(u=True))
        i2 = os.geteuid()
        self.assertEqual(i1, i2)

    @requires_posix
    def test_long_bool_option(self):
        from pbs import id
        i1 = int(id(user=True, real=True))
        i2 = os.getuid()
        self.assertEqual(i1, i2)

    @requires_posix
    def test_composition(self):
        from pbs import ls, wc
        c1 = int(wc(ls(A=True), l=True))
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)

    @requires_posix
    def test_short_option(self):
        from pbs import sh
        s1 = unicode(sh(c="echo test")).strip()
        s2 = "test"
        self.assertEqual(s1, s2)
        
    @requires_posix
    def test_long_option(self):
        from pbs import sed, echo
        out = unicode(sed(echo("test"), expression="s/test/lol/")).strip()
        self.assertEqual(out, "lol")
        
    @requires_posix
    def test_command_wrapper(self):
        from pbs import Command, which
        
        ls = Command(which("ls"))
        wc = Command(which("wc"))
        
        c1 = int(wc(ls(A=True), l=True))
        c2 = len(os.listdir("."))
        self.assertEqual(c1, c2)

    @requires_posix
    def test_background(self):
        from pbs import sleep
        import time
        
        start = time.time()
        sleep_time = 1
        p = sleep(sleep_time, _bg=True)

        now = time.time()
        self.assertTrue(now - start < sleep_time)

        p.wait()
        now = time.time()
        self.assertTrue(now - start > sleep_time)
                
    @requires_posix
    def test_with_context(self):
        from pbs import time, ls
        with time:
            out = ls().stderr
        self.assertTrue("pagefaults" in out)


    @requires_posix
    def test_with_context_args(self):
        from pbs import time, ls
        with time(verbose=True, _with=True):
            out = ls().stderr
        self.assertTrue("Voluntary context switches" in out)


    @requires_posix
    def test_err_to_out(self):
        from pbs import time, ls
        with time(_with=True):
            out = ls(_err_to_out=True)

        self.assertTrue("pagefaults" in out)


    @requires_posix
    def test_out_redirection(self):
        import tempfile
        from pbs import ls

        file_obj = tempfile.TemporaryFile()
        out = ls(_out=file_obj)
        
        self.assertTrue(len(out) == 0)

        file_obj.seek(0)
        actual_out = file_obj.read()

        self.assertTrue(len(actual_out) != 0)


    @requires_posix
    def test_err_redirection(self):
        import tempfile
        from pbs import time, ls

        file_obj = tempfile.TemporaryFile()

        with time(_with=True):
            out = ls(_err=file_obj)
        
        file_obj.seek(0)
        actual_out = file_obj.read()

        self.assertTrue(len(actual_out) != 0)





if __name__ == "__main__":
    unittest.main()
