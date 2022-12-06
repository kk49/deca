import time
from deca.ff_rtpc import Rtpc, RtpcVisitorDumpToString, RtpcVisitorGatherStrings
from deca.db_processor import vfs_structure_open


vfs_config = '/home/krys/prj/work/gz/project.json'
file = '/home/krys/prj/work/gz/extracted/locations/dlc_island_01/abandoned_foa_facility_entrance.blo'

tv0 = time.time()

vfs = vfs_structure_open(vfs_config)

tv1 = time.time()

print(f'Vfs load {tv1 - tv0}')

# TEST Traditional
t0 = time.time()
rtpc = Rtpc()
with open(file, 'rb') as f:
    rtpc.deserialize(f)
t1 = time.time()
s0 = rtpc.dump_to_string(vfs)
t2 = time.time()

print(f'Org: Rtpc load {t1 - t0}')
print(f'Org: Rtpc to str {t2 - t1}')
print(f'Org: Rtpc total {t2 - t0}')

# Test visitor
t0 = time.time()
with open(file, 'rb') as f:
    buffer = f.read()
t1 = time.time()
dump = RtpcVisitorDumpToString(vfs)
dump.visit(buffer)
s1 = dump.result()
t2 = time.time()

print('----------- Numba compile run')
print(f'Vis: Rtpc load {t1 - t0}')
print(f'Vis: Rtpc to str {t2 - t1}')
print(f'Vis: Rtpc total {t2 - t0}')

# Test visitor
t0 = time.time()
with open(file, 'rb') as f:
    buffer = f.read()
t1 = time.time()
dump = RtpcVisitorDumpToString(vfs)
dump.visit(buffer)
s1 = dump.result()
t2 = time.time()

print('----------- Numba already compiled run')
print(f'Vis: Rtpc load {t1 - t0}')
print(f'Vis: Rtpc to str {t2 - t1}')
print(f'Vis: Rtpc total {t2 - t0}')

with open('rtpc_org.txt', 'w') as f:
    f.write(s0)

with open('rtpc_new.txt', 'w') as f:
    f.write(s1)

# Test visitor
t0 = time.time()
with open(file, 'rb') as f:
    buffer = f.read()
t1 = time.time()
dump = RtpcVisitorGatherStrings()
dump.visit(buffer)
t2 = time.time()

print('----------- Numba compile run')
print(f'Vis: Rtpc load {t1 - t0}')
print(f'Vis: Rtpc gather strings {t2 - t1}')
print(f'Vis: Rtpc total {t2 - t0}')

# Test visitor
t0 = time.time()
with open(file, 'rb') as f:
    buffer = f.read()
t1 = time.time()
dump = RtpcVisitorGatherStrings()
dump.visit(buffer)
t2 = time.time()

print('----------- Numba already compiled run')
print(f'Vis: Rtpc load {t1 - t0}')
print(f'Vis: Rtpc gather strings {t2 - t1}')
print(f'Vis: Rtpc total {t2 - t0}')
