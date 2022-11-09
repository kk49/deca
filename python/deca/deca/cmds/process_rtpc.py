import sys
from deca.ff_rtpc import Rtpc


class FakeVfs:
    def hash_string_match(self, hash32=None, hash48=None, hash64=None):
        return []


in_file = sys.argv[1]

with open(in_file, 'rb') as f:
    rtpc = Rtpc()
    rtpc.deserialize(f)

print(rtpc.dump_to_string(FakeVfs()))
