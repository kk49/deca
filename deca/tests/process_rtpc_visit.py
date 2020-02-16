import time
from deca.ff_rtpc import Rtpc
from deca.vfs_processor import vfs_structure_open


vfs_config = '/home/krys/prj/work/gz/project.json'
file = '/home/krys/prj/work/gz/extracted/locations/dlc_island_01/abandoned_foa_facility_entrance.blo'

t0 = time.time()

vfs = vfs_structure_open(vfs_config)

t1 = time.time()

rtpc = Rtpc()
with open(file, 'rb') as f:
    rtpc.deserialize(f)

t2 = time.time()

s = rtpc.dump_to_string(vfs)

t3 = time.time()

print(s)

print(f'Vfs load {t1 - t0}')
print(f'Rtpc load {t2 - t1}')
print(f'Rtpc to str {t3 - t2}')
