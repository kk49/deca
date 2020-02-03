from deca.errors import EDecaOutOfData
from deca.ff_types import *


class TabFileBase:
    def __init__(self):
        self.unk = []
        self.magic = None
        self.file_version = None
        self.file_table = None
        self.file_hash_map = None
        self.file_block_table = None

    def deserialize(self, f):
        raise NotImplementedError('Interface Class')

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabFileV3(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.unk += [f.read_u16()]
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]

        # print(self.magic, self.unk)

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV3()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV3()

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabFileV4(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.file_version = f.read_u16()  # just cause 4 was still 2, rage 2 is 3
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]

        t1_len = f.read_u32()

        t1 = []
        for i in range(t1_len):
            len_c = f.read_u32()
            len_u = f.read_u32()
            t1.append([len_c, len_u])
        self.file_block_table = t1

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV4()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV4()

        # give each file entry its info about its file blocks
        no_block = [0xffffffff, 0xffffffff]
        fbt = [None] * len(self.file_block_table)
        for i, fte in enumerate(self.file_table):
            fbi = fte.file_block_index
            if self.file_block_table[fbi] != no_block:
                fbt[fbi] = i
                fte.file_block_table = []

        for i, fb in enumerate(self.file_block_table):
            if fb == no_block:
                fbt[i] = None

        for i in range(2, len(fbt)-1):
            if fbt[i] is None:
                fbt[i] = fbt[i-1]
        for i in range(1, len(fbt)-1):
            if fbt[i] is not None:
                self.file_table[fbt[i]].file_block_table.append(self.file_block_table[i])
            else:
                pass

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabFileV5(TabFileBase):
    def __init__(self):
        TabFileBase.__init__(self)

    def deserialize(self, f):
        self.magic = f.read(4)
        self.file_version = f.read_u16()  # just cause 4 was still 2, rage 2 is 3
        assert 3 == self.file_version
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]
        file_count = f.read_u32()
        block_count = f.read_u32()
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]

        t1 = []
        for i in range(block_count):
            len_c = f.read_u32()
            len_u = f.read_u32()
            t1.append([len_c, len_u])
        self.file_block_table = t1

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV5()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV4()

        # give each file entry its info about its file blocks
        no_block = [0xffffffff, 0xffffffff]
        fbt = [None] * len(self.file_block_table)
        for i, fte in enumerate(self.file_table):
            fbi = fte.file_block_index
            if self.file_block_table[fbi] != no_block:
                fbt[fbi] = i
                fte.file_block_table = []

        for i, fb in enumerate(self.file_block_table):
            if fb == no_block:
                fbt[i] = None

        for i in range(2, len(fbt)-1):
            if fbt[i] is None:
                fbt[i] = fbt[i-1]
        for i in range(1, len(fbt)-1):
            if fbt[i] is not None:
                self.file_table[fbt[i]].file_block_table.append(self.file_block_table[i])
            else:
                pass

        return True

    def serialize(self, f):
        raise NotImplementedError('Interface Class')


class TabEntryFileBase:
    def __init__(self):
        self.hashname = None
        self.offset = None
        self.size_c = None
        self.size_u = None
        self.file_block_index = None
        self.compression_type = None
        self.compression_flags = None
        self.file_block_table = []

    def deserialize(self, f):
        raise NotImplementedError('Interface Class')

    def serialize(self, f):
        raise NotImplementedError('Interface Class')

    def debug(self):
        l = [self.offset, self.size_c, self.size_u]
        return [
            '{:08x}'.format(self.hashname),
            l,
            ['{:08x}'.format(v) for v in l],
            self.file_block_index,
            self.compression_type,
            self.compression_flags,
            self.file_block_table
        ]


class TabEntryFileV3(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_u32(raise_on_no_data=True)
            self.offset = f.read_u32(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = self.size_c
            self.file_block_table = [[self.size_c, self.size_u]]
            self.compression_flags = 0
            if self.size_c == self.size_u:
                self.compression_type = compression_00_none
            else:
                self.compression_type = compression_v3_zlib

            if f.debug:
                self.debug()
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')


class TabEntryFileV4(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_u32(raise_on_no_data=True)
            self.offset = f.read_u32(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = f.read_u32(raise_on_no_data=True)
            self.file_block_index = f.read_u16(raise_on_no_data=True)
            self.compression_type = f.read_u8(raise_on_no_data=True)
            self.compression_flags = f.read_u8(raise_on_no_data=True)
            self.file_block_table = [[self.size_c, self.size_u]]

            if f.debug:
                print(self.debug())
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')


class TabEntryFileV5(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        try:
            self.hashname = f.read_u32(raise_on_no_data=True)
            self.offset = f.read_u32(raise_on_no_data=True)
            self.xxx = f.read_u32(raise_on_no_data=True)
            self.file_block_index = f.read_u16(raise_on_no_data=True)
            self.size_c = f.read_u32(raise_on_no_data=True)
            self.size_u = f.read_u32(raise_on_no_data=True)
            self.compression_type = f.read_u8(raise_on_no_data=True)
            self.compression_flags = f.read_u8(raise_on_no_data=True)
            self.file_block_table = [[self.size_c, self.size_u]]

            if f.debug:
                print(self.debug())
        except EDecaOutOfData:
            return False

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')
