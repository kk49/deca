import sys
import os
from deca.ff_rtpc import Rtpc


if len(sys.argv) < 2:
    in_file = '/home/krys/prj/deca/work/gz/exported/editor/entities/characters/machines/dreadnought/drea_classa_load01.epe'
    in_file = 'dump.dat'
    in_file = '/home/krys/prj/deca/work/gz/exported/global/global.blo'
else:
    in_file = sys.argv[1]

file_sz = os.stat(in_file).st_size

with open(in_file, 'rb') as f:
    rtpc = Rtpc()
    rtpc.deserialize(f)

print(rtpc.dump_to_string())
