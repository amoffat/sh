import openp
import time
import os
import threading


#p = openp.OpenP(["/bin/ls", "/", "-1"])
#p = openp.OpenP(["/usr/bin/tr", "[:lower:]", "[:upper:]"])
p = openp.OpenP(["/usr/bin/ssh", "amoffat@dev02"])

def collect(stream):
    while True:
        try: chunk = os.read(stream, 1024)
        except OSError: break
        if not chunk: break
        print chunk
    
t = threading.Thread(target=collect, args=(p.stdout,))
t.daemon = True
t.start()

time.sleep(1)
os.write(p.stdin, "derp\n")
time.sleep(3)
os.write(p.stdin, chr(4))
time.sleep(3)
print p.wait()
