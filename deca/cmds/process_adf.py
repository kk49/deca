import sys
from deca.file import ArchiveFile
from deca.ff_adf import Adf


class FakeVfs:
    def hash_string_match(self, hash32=None, hash48=None, hash64=None):
        return []


in_file = sys.argv[1]

obj = Adf()
with ArchiveFile(open(in_file, 'rb')) as f:
    obj.deserialize(f)

print(obj.dump_to_string(FakeVfs()))
