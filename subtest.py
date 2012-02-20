import pbs as sh

def test(line):
    print repr(line)

#p = sh.grep(sh.ls("/usr/lib", "-1", _piped=True), "ao", _out=test)
p = sh.sort(sh.tr(sh.du("/usr/lib", _piped=True), "[:lower:]", "[:upper:]", _piped=True), "-n")
#p = sh.ls("/etc", "-1", _out=test)
p.wait()
#print p