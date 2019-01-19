class TabFileBase:
    def __init__(self):
        self.unk = []
        self.magic = None
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
        self.unk += [f.read_u16()]
        self.unk += [f.read_u16()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        # print(magic, unk)

        t1_len = f.read_u32()
        t1 = []
        for i in range(t1_len):
            t1.append([f.read_u32(), f.read_u32()])
        self.file_block_table = t1

        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]
        self.unk += [f.read_u32()]  # len dup 1 of file entries
        self.unk += [f.read_u32()]  # len dup 2 of file entries
        self.unk += [f.read_u32()]

        self.file_table = []
        self.file_hash_map = {}
        entry = TabEntryFileV4()
        while entry.deserialize(f):
            self.file_table.append(entry)
            self.file_hash_map[entry.hashname] = entry
            entry = TabEntryFileV4()

        # give each file entry its info about its file blocks
        fbt = [None] * len(self.file_block_table)
        for i in range(len(self.file_table)):
            fte = self.file_table[i]
            if fte.file_block_index > 0:
                fbt[fte.file_block_index] = i
                fte.file_block_table = []
        fbt[0] = None
        fbt[-1] = None
        for i in range(2, len(fbt)-1):
            if fbt[i] is None:
                fbt[i] = fbt[i-1]
        for i in range(1, len(fbt)-1):
            self.file_table[fbt[i]].file_block_table.append(self.file_block_table[i])

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
        self.flags = None
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
            self.flags,
            self.file_block_table
        ]


class TabEntryFileV3(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        tmp = f.read_u32()
        if tmp is None:
            return False
        self.hashname = tmp
        self.offset = f.read_u32()
        self.size_c = f.read_u32()
        self.size_u = self.size_c
        self.file_block_table = [[self.size_c, self.size_u]]

        if f.debug:
            self.debug()

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')


class TabEntryFileV4(TabEntryFileBase):
    def __init__(self):
        TabEntryFileBase.__init__(self)

    def deserialize(self, f):
        tmp = f.read_u32()
        if tmp is None:
            return False
        self.hashname = tmp
        self.offset = f.read_u32()
        self.size_c = f.read_u32()
        self.size_u = f.read_u32()
        self.file_block_index = f.read_u16()
        self.flags = f.read_u16()
        self.file_block_table = [[self.size_c, self.size_u]]

        if f.debug:
            print(self.debug())

        return True

    def serialize(self, f):
        raise NotImplementedError('TODO')
