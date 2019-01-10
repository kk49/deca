from deca.file import ArchiveFile
import struct

# Node Types

NT_none = 0
NT_u32 = 1
NT_f32 = 2
NT_str = 3
NT_vec2 = 4
NT_vec3 = 5
NT_vec4 = 6
NT_mat3x3 = 7  # DEPRECIATED?
NT_mat4x4 = 8
NT_array_u32 = 9
NT_array_f32 = 10
NT_array_u8 = 11
NT_depreciated_12 = 12
NT_objid = 13
NT_event = 14

NT_names = [
    'none', 'u32', 'f32', 'str',
    'vec2', 'vec3', 'vec4', 'mat3x3',
    'mat4x4', 'array_u32', 'array_f32', 'array_u8',
    'd12', 'objid', 'event']


class RtpcProperty:
    def __init__(self):
        self.data_position = None
        self.name_hash = None
        self.data = None
        self.data_raw = None
        self.type = None
        self.extra = None

    def __repr__(self):
        return '0x{:08x} @{}(0x{:08x}) {} = 0x{:08x} {}'.format(
            self.name_hash, self.data_position, self.data_position, NT_names[self.type], self.data_raw, self.data)
        # return '0x{:08x}: {} = {}'.format(self.name_hash, NT_names[self.type], self.data,)

    def deserialize(self, f):
        self.name_hash = f.read_u32()
        self.data_position = f.tell()
        self.data_raw = f.read_u32()
        self.type = f.read_u8()
        # self.extra = f.read_u8(3)

        self.data = self.data_raw

        raw_buf = struct.pack('I', self.data_raw)
        if self.type == NT_none:
            pass
        elif self.type == NT_u32:
            self.data = struct.unpack('I', raw_buf)[0]
        elif self.type == NT_f32:
            self.data = struct.unpack('f', raw_buf)[0]
        elif self.type == NT_str:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = f.read_strz()
            f.seek(opos)
        elif self.type == NT_vec2:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = list(f.read_f32(2))
            f.seek(opos)
        elif self.type == NT_vec3:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = list(f.read_f32(3))
            f.seek(opos)
        elif self.type == NT_vec4:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = list(f.read_f32(4))
            f.seek(opos)
        elif self.type == NT_mat3x3:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = list(f.read_f32(9))
            f.seek(opos)
        elif self.type == NT_mat4x4:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = list(f.read_f32(16))
            f.seek(opos)
        elif self.type == NT_array_u32:
            opos = f.tell()
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u32(n))
            f.seek(opos)
        elif self.type == NT_array_f32:
            opos = f.tell()
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_f32(n))
            f.seek(opos)
        elif self.type == NT_array_u8:
            opos = f.tell()
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u8(n))
            f.seek(opos)
        elif self.type == NT_objid:
            opos = f.tell()
            f.seek(self.data_raw)
            self.data = f.read_u8(8)
            f.seek(opos)
        elif self.type == NT_event:
            opos = f.tell()
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            for i in range(n):
                self.data.append(f.read_u32(2))
            f.seek(opos)
        else:
            raise Exception('NOT HANDLED {}'.format(self.type))


class RtpcNode:
    def __init__(self):
        self.name_hash = None
        self.data_offset = None
        self.prop_count = None
        self.child_count = None
        self.prop_table = []
        self.child_table = []

    def __repr__(self):
        return '{:08x} pc:{} cc:{} @ {} {:08x}'.format(
            self.name_hash, self.prop_count, self.child_count, self.data_offset, self.data_offset)

    def dump_to_string(self, indent=0):
        ind0 = ' ' * indent
        ind1 = ' ' * (indent + 2)
        ind2 = ' ' * (indent + 4)
        sbuf = ''
        sbuf = sbuf + ind0 + 'node:\n'
        sbuf = sbuf + ind1 + self.__repr__() + '\n'
        sbuf = sbuf + ind1 + 'properties ---------------\n'
        for p in self.prop_table:
            sbuf = sbuf + ind2 + p.__repr__() + '\n'
        sbuf = sbuf + ind1 + 'children -----------------\n'
        for c in self.child_table:
            sbuf = sbuf + c.dump_to_string(indent + 4)

        return sbuf

    def deserialize(self, f):
        self.name_hash = f.read_u32()
        self.data_offset = f.read_u32()
        self.prop_count = f.read_u16()
        self.child_count = f.read_u16()

        oldp = f.tell()
        f.seek(self.data_offset)
        # read properties
        self.prop_table = [None] * self.prop_count
        for i in range(self.prop_count):
            prop = RtpcProperty()
            prop.deserialize(f)
            self.prop_table[i] = prop

        #  children 4-byte aligned
        np = f.tell()
        f.seek(np + (4 - (np % 4)) % 4)

        # read children
        self.child_table = [None] * self.child_count
        for i in range(self.child_count):
            child = RtpcNode()
            child.deserialize(f)
            self.child_table[i] = child

        f.seek(oldp)


class Rtpc:
    def __init__(self):
        self.magic = None
        self.version = None
        self.root_node = None

    def deserialize(self, fraw):
        f = ArchiveFile(fraw)

        self.magic = f.read_strl(4)
        if self.magic != b'RTPC':
            raise Exception('Bad MAGIC {}'.format(self.magic))

        self.version = f.read_u32()

        self.root_node = RtpcNode()
        self.root_node.deserialize(f)

    def dump_to_string(self):
        return self.root_node.dump_to_string()
