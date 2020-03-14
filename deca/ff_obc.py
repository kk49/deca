import struct
import numpy as np
from deca.db_processor import VfsProcessor


class Obc:
    def __init__(self):
        self.table = None

    def dump_to_string(self, vfs: VfsProcessor):
        s = ''
        if self.table is not None:
            for line in self.table:
                # eles = ['{}'.format(vfs.map_hash_to_vpath.get(idx, idx)) for idx in line[1]]
                # s = s + '\n' + '|'.join(eles)
                s = s + '\n{}'.format(line)
        return s

    def deserialize(self, file):
        header = file.read(8)
        header = struct.unpack('II', header)

        size = 80 * header[1]
        data = file.read(size)

        dtype = np.dtype('20f4')
        self.table = np.frombuffer(data, dtype=dtype)




