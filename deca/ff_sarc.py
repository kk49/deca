from deca.file import ArchiveFile
from deca.hash_jenkins import hash_little


class EntrySarc:
    def __init__(self, index=None, vpath=None):
        self.META_entry_ptr = None
        self.META_entry_offset_ptr = None
        self.META_entry_size_ptr = None
        self.index = index
        self.vpath = vpath
        self.string_offset = None
        self.offset = None
        self.length = None
        self.unk_file_type_hash = None
        self.vhash = None

    def deserialize_v2(self, f):
        self.META_entry_ptr = f.tell()
        self.vpath = f.read_strl_u32().strip(b'\00')
        self.META_entry_offset_ptr = f.tell()
        self.offset = f.read_u32()
        self.META_entry_size_ptr = f.tell()
        self.length = f.read_u32()

        self.vhash = hash_little(self.vpath)

    def deserialize_v3(self, f):
        self.META_entry_ptr = f.tell()
        self.string_offset = f.read_u32()
        self.META_entry_offset_ptr = f.tell()
        self.offset = f.read_u32()
        self.META_entry_size_ptr = f.tell()
        self.length = f.read_u32()
        self.vhash = f.read_u32()
        self.unk_file_type_hash = f.read_u32()

    def __repr__(self):
        str_vhash = ''
        if self.vhash is not None:
            str_vhash = ' h:{:08X}'.format(self.vhash)

        str_fthash = ''
        if self.unk_file_type_hash is not None:
            str_fthash = ' ft:{:08X}'.format(self.unk_file_type_hash)

        return 'o:{:9d} s:{:9d}{}{} vp:{}'.format(
            self.offset, self.length, str_vhash, str_fthash, self.vpath.decode('utf-8'))

    def dump_str(self):
        return self.__repr__()


class FileSarc:
    def __init__(self):
        self.version = None
        self.magic = None
        self.ver2 = None
        self.dir_block_len = None
        self.strings0 = None
        self.strings = None
        self.entries = None

    def deserialize(self, fin):
        with ArchiveFile(fin) as f:
            self.version = f.read_u32()
            assert(self.version == 4)
            self.magic = f.read(4)
            assert(self.magic == b'SARC')
            self.ver2 = f.read_u32()
            assert(self.ver2 in {2, 3})
            self.dir_block_len = f.read_u32()

            if self.ver2 == 2:
                self.entries = []
                end_pos = f.tell() + self.dir_block_len
                idx = 0
                while f.tell() + 12 <= end_pos:  # 12 is minimum length of v2 sarc entry and they pad with some zeros
                    entry = EntrySarc(idx)
                    entry.deserialize_v2(f)
                    self.entries.append(entry)
                    idx += 1

            elif self.ver2 == 3:
                string_len = f.read_u32()
                self.strings0 = f.read(string_len)
                self.strings = self.strings0.split(b'\00')
                if len(self.strings[-1]) == 0:
                    self.strings = self.strings[:-1]

                self.entries = [EntrySarc(index=i, vpath=self.strings[i], ) for i in range(len(self.strings))]
                for ent in self.entries:
                    ent.deserialize_v3(f)

    def dump_str(self):
        sbuf = ''
        for ent in self.entries:
            sbuf = sbuf + ent.dump_str() + '\n'
        return sbuf
