import sys
import os
from deca.ff_rtpc import Rtpc


if len(sys.argv) < 2:
    in_file = '/home/krys/prj/work/jc4/__CACHE__/archives_win64/boot_patch/game0.arc/DED58CCC.dat'
else:
    in_file = sys.argv[1]

file_sz = os.stat(in_file).st_size

with open(in_file, 'rb') as f:
    rtpc = Rtpc()
    rtpc.deserialize(f)

print(rtpc.dump_to_string())
