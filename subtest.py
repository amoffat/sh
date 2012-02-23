import pbs as sh

def test(line):
    print line

#p = sh.grep(sh.ls("/usr/lib", "-1", _piped=True), "ao", _out=test)
#p = sh.head(sh.tr(sh.du("/home/amoffat", _piped=True), "[:lower:]", "[:upper:]", _piped=True))
p = sh.ls("/etc", "-1")
print p
