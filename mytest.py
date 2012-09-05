import pbs as sh
import logging
import os
import sys
import tempfile

#sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
logging.basicConfig(
    level=logging.DEBUG,
    format="(%(process)d) %(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


stdin = tempfile.NamedTemporaryFile()

data = ",".join((str(num) for num in xrange(1, 3500))) + "\n"
stdin.write(data.encode())
stdin.flush()
stdin.seek(0)

out = sh.tr("[:lower:]", "[:upper:]", _in=data)
#out = sh.cat(stdin.name)
print len(out), len(data)