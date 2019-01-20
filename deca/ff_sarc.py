from deca.file import ArchiveFile


class EntrySarc:
    def __init__(self, index=None, v_path=None):
        self.META_entry_offset = None
        self.index = index
        self.v_path = v_path
        self.string_offset = None
        self.offset = None
        self.length = None
        self.shash = None
        self.unk_file_type_hash = None

    def deserialize(self, f):
        self.META_entry_offset = f.tell()
        self.string_offset = f.read_u32()
        self.offset = f.read_u32()
        self.length = f.read_u32()
        self.shash = f.read_u32()
        self.unk_file_type_hash = f.read_u32()

    def __repr__(self):
        return 'o:{:9d} s:{:9d} h:{:08X} ft:{:08x} vp:{}'.format(self.offset, self.length, self.shash, self.unk_file_type_hash, self.v_path.decode('utf-8'))

    def dump_str(self):
        return 'o:{:9d} s:{:9d} h:{:08X} ft:{:08x} vp:{}'.format(self.offset, self.length, self.shash, self.unk_file_type_hash, self.v_path.decode('utf-8'))


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
            assert(self.ver2 == 3)
            self.dir_block_len = f.read_u32()

            string_len = f.read_u32()
            self.strings0 = f.read(string_len)
            self.strings = self.strings0.split(b'\00')
            if len(self.strings[-1]) == 0:
                self.strings = self.strings[:-1]

            self.entries = [EntrySarc(v_path=self.strings[i], index=i) for i in range(len(self.strings))]
            for ent in self.entries:
                ent.deserialize(f)

    def dump_str(self):
        sbuf = ''
        for ent in self.entries:
            sbuf = sbuf + ent.dump_str() + '\n'
        return sbuf
