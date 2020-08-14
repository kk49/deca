import sys
import re
import csv

paths = set()

for i in range(1, len(sys.argv)):
    with open(sys.argv[i], 'r') as f:
        db = csv.reader(f, delimiter=',', quotechar='"')

        # p = re.compile(r'^.*\\dropzone\\(.*)$')
        p = re.compile(r'^.*\\theHunterCotW\\(.*\\.*)$')
        for row in db:
            pth = row[4]
            # print(pth)
            r = p.match(pth)
            if r is not None:
                s = r.groups(1)[0]
                s = s.replace('\\', '/')
                paths.add(s)

paths = list(paths)
paths.sort()

for s in paths:
    print(s)
