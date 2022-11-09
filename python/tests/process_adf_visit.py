import time
from deca.ff_adf import Adf, AdfDatabase
from deca.db_processor import vfs_structure_open


vfs_config = '/home/krys/prj/work/gz/project.json'
file = '/home/krys/prj/work/gz/extracted/missions/missions.group.hpmissionsc'

t0 = time.time()

vfs = vfs_structure_open(vfs_config)
adf_db = AdfDatabase(vfs)

t1 = time.time()

with open(file, 'rb') as f:
    buffer = f.read()

adf = adf_db._load_adf(buffer)

t2 = time.time()

s = adf.dump_to_string(vfs)

t3 = time.time()

# print(s)

print(f'Vfs load {t1 - t0}')
print(f'Adf load {t2 - t1}')
print(f'Adf to str {t3 - t2}')
