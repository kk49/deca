import os
prefix = '/home/krys/prj/avalanche_debug/gz/archives_win64'

fl = [prefix]

final_lines = set()
while fl:
    current = fl[0]
    fl = fl[1:]

    if os.path.isfile(current) and current.find('content_hashed.txt') >= 0:
        with open(current, 'r') as f:
            lines = f.readlines()
        lines = lines[2:]
        for line in lines:
            line = line.strip('\n')
            ff = line.split(' ')
            ff = ff[-1]
            final_lines.add(ff)

    elif os.path.isdir(current):
        fs = os.listdir(current)
        for f in fs:
            fl.append(os.path.join(current, f))

final_lines = list(final_lines)
final_lines = sorted(final_lines)

with open('vpaths_gen.txt', 'w') as f:
    for line in final_lines:
        f.write(line + '\n')
