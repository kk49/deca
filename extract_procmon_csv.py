import pandas as pd
import sys
import re

paths = set()

for i in range(1, len(sys.argv)):
    db = pd.read_csv(sys.argv[i])
    paths0 = db['Path']
    p = re.compile('^.*\\\dropzone\\\(.*)$')
    for path in paths0:
        r = p.match(path)
        if r is not None:
            s = r.groups(1)[0]
            s = s.replace('\\', '/')
            paths.add(s)

paths = [s for s in paths]
paths.sort()

for s in paths:
    print(s)
