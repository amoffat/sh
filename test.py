import os
import unittest

@unittest.skipUnless(os.name == 'posix', 'Requires POSIX')
class PbsPosixTestSuite(unittest.TestCase):
    def test_no_arg(self):
        import pwd
        from pbs import whoami
        u1 = unicode(whoami()).strip()
        u2 = pwd.getpwuid(os.geteuid())[0]
        self.assertEqual(u1, u2)

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
        c1 = int(wc(ls(A=True), l=True))
        c2 = len(os.listdir('.'))
        self.assertEqual(c1, c2)

    def test_short_option(self):
        from pbs import sh
        s1 = unicode(sh(c='echo test')).strip()
        s2 = 'test'
        self.assertEqual(s1, s2)

@unittest.skipUnless(os.name == 'nt', 'Requires NT')
class PbsNtTestSuite(unittest.TestCase):
    def test_nt_internal_commands(self):
        from pbs import ECHO

        s1 = unicode(ECHO("test")).strip()
        s2 = 'test'
        self.assertEqual(s1, s2)
 
    def test_nt_internal_commands_pipe(self):
        from pbs import dir, find
        # dir /b /a | find /c /v ""
        c1 = int(find(dir("/b", "/a"),'/c', '/v','""'))
        c2 = len(os.listdir('.'))
        self.assertEqual(c1, c2)
        
    #self.assertIn("Volume Serial Number", s1)  
if __name__ == '__main__':
    unittest.main()
