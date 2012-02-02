import os
import unittest

requires_posix = unittest.skipUnless(os.name == "posix", "Requires POSIX")
requires_nt = unittest.skipUnless(os.name == 'nt', 'Requires NT')

class PbsTestSuite(unittest.TestCase):
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

    @requires_nt
    def test_nt_internal_commands(self):
        from pbs import ECHO

        s1 = unicode(ECHO("test")).strip()
        s2 = 'test'
        self.assertEqual(s1, s2)
        
    @requires_nt
    def test_nt_internal_commands_pipe(self):
        from pbs import dir, find
        # dir /b /a | find /c /v ""
        c1 = int(find(dir("/b", "/a"),'/c', '/v','""'))
        c2 = len(os.listdir('.'))
        self.assertEqual(c1, c2)
        
    @requires_nt
    def test_nt_noglob(self):
        from pbs import ipconfig, ErrorReturnCode_1
        try:
            ret = ipconfig("/?", _noglob=True)
        except Exception as err:
            self.assertIn("/?" , err.full_cmd)
        try:
            ret = ipconfig("/?", _noglob=False)
        except Exception as err:
            self.assertNotIn("/?", err.full_cmd)
        
if __name__ == '__main__':
    unittest.main()