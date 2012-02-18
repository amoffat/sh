import openp
import time
import os
import threading


p = openp.OProc(["/bin/ls", "/usr/lib"])
#p = openp.OProc(["/usr/bin/gcc", "-v"])
#p = openp.OProc(["/usr/bin/tr", "[:lower:]", "[:upper:]"])
#p = openp.OProc(["/usr/bin/ssh", "amoffat@dev02"])

#p.stdin.put("lol\n")

#time.sleep(1)
#p.kill()
#print p.stdout