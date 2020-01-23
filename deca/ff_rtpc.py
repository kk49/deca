from deca.file import ArchiveFile
from deca.vfs_db import VfsDatabase
import struct
from enum import IntEnum
from typing import List, Optional

# Node Types


class PropType(IntEnum):
    type_none = 0
    type_u32 = 1
    type_f32 = 2
    type_str = 3
    type_vec2 = 4
    type_vec3 = 5
    type_vec4 = 6
    type_mat3x3 = 7  # DEPRECIATED?
    type_mat4x4 = 8
    type_array_u32 = 9
    type_array_f32 = 10
    type_array_u8 = 11
    type_depreciated_12 = 12
    type_objid = 13
    type_event = 14


PropType_names = [
    'none',
    'u32',
    'f32',
    'str',
    'vec2',
    'vec3',
    'vec4',
    'mat3x3',
    'mat4x4',
    'A[u32]',
    'A[f32]',
    'A[u8]',
    'd12',
    'objid',
    'event',
]


class PropName(IntEnum):
    CLASS_NAME = 0x1473b179
    CLASS_NAME_HASH = 0xd04059e6
    CREGION_BORDER = 0x1c1d51a9
    CLASS_COMMENT = 0xd31ab684
    INSTANCE_UID = 0xcfff8405
    ROTPOS_TRANSFORM = 0x6ca6d4b9
    CPOI_NAME = 0x6f24d4e5
    CPOI_DESC = 0xe6b6b3f9
    BOOKMARK_NAME = 0x2314c9ea


class RtpcProperty:
    def __init__(self):
        self.pos = None
        self.name_hash = None
        self.data_pos = None
        self.data_raw = None
        self.data = None
        self.type = None

    def __repr__(self):
        data = self.data
        if self.type == PropType.type_objid.value:
            data = 'id:0x{:012X}'.format(data)
        elif self.type == PropType.type_event.value:
            data = ['ev:0x{:012X}'.format(d) for d in data]

        return '@0x{:08x}({: 8d}) 0x{:08x} 0x{:08x} 0x{:02x} {:6s} = @0x{:08x}({: 8d}) {} '.format(
            self.pos, self.pos,
            self.name_hash,
            self.data_raw,
            self.type,
            PropType_names[self.type],
            self.data_pos, self.data_pos,
            data)
        # return '0x{:08x}: {} = {}'.format(self.name_hash, PropType.type_names[self.type], self.data,)

    def repr_with_name(self, vfs: VfsDatabase):
        data = self.data
        if self.type == PropType.type_objid.value:
            name6 = vfs.hash6_where_vhash_select_all(data & 0x0000FFFFFFFFFFFF)
            name4 = vfs.hash4_where_vhash_select_all(data)
            if len(name6):
                name = 'id:DB:H6:"{}"'.format(name6[0][2].decode('utf-8'))
            elif len(name4):
                name = 'id:DB:H4:"{}"'.format(name4[0][2].decode('utf-8'))
            else:
                name = 'id:0x{:012X}'.format(data)
            data = name

        elif self.type == PropType.type_event.value:
            data_new = []
            for d in data:
                name6 = vfs.hash6_where_vhash_select_all(d & 0x0000FFFFFFFFFFFF)
                name4 = vfs.hash4_where_vhash_select_all(d)
                if len(name6):
                    name = 'ev:DB:H6:"{}"'.format(name6[0][2].decode('utf-8'))
                elif len(name4):
                    name = 'ev:DB:H4:"{}"'.format(name4[0][2].decode('utf-8'))
                else:
                    name = 'ev:0x{:012X}'.format(d)
                data_new.append(name)
            data = data_new

        name = vfs.hash4_where_vhash_select_all(self.name_hash)
        if len(name):
            name = '"{}"'.format(name[0][2].decode('utf-8'))
        else:
            name = f'0x{self.name_hash:08x}'

        return '@0x{:08x}({: 8d}) {} 0x{:08x} 0x{:02x} {:6s} = @0x{:08x}({: 8d}) {} '.format(
            self.pos, self.pos,
            name,
            self.data_raw,
            self.type,
            PropType_names[self.type],
            self.data_pos, self.data_pos,
            data)
        # return '0x{:08x}: {} = {}'.format(self.name_hash, PropType.type_names[self.type], self.data,)

    def deserialize(self, f):
        self.pos = f.tell()
        self.name_hash = f.read_u32()
        self.data_pos = f.tell()
        self.data_raw = f.read_u32()
        self.type = f.read_u8()

        self.data = self.data_raw

        raw_buf = struct.pack('I', self.data_raw)
        if self.type == PropType.type_none:
            pass
        elif self.type == PropType.type_u32:
            self.data = struct.unpack('I', raw_buf)[0]
        elif self.type == PropType.type_f32:
            self.data = struct.unpack('f', raw_buf)[0]
        elif self.type == PropType.type_str:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = f.read_strz()
            f.seek(opos)
        elif self.type == PropType.type_vec2:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(2))
            f.seek(opos)
        elif self.type == PropType.type_vec3:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(3))
            f.seek(opos)
        elif self.type == PropType.type_vec4:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(4))
            f.seek(opos)
        elif self.type == PropType.type_mat3x3:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(9))
            f.seek(opos)
        elif self.type == PropType.type_mat4x4:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(16))
            f.seek(opos)
        elif self.type == PropType.type_array_u32:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u32(n))
            f.seek(opos)
        elif self.type == PropType.type_array_f32:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_f32(n))
            f.seek(opos)
        elif self.type == PropType.type_array_u8:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u8(n))
            f.seek(opos)
        elif self.type == PropType.type_objid:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = f.read_u64()
            f.seek(opos)
        elif self.type == PropType.type_event:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            for i in range(n):
                self.data.append(f.read_u64())
            f.seek(opos)
        else:
            raise Exception('NOT HANDLED {}'.format(self.type))


class RtpcNode:
    def __init__(self):
        self.name_hash = None
        self.data_offset = None
        self.prop_count = None
        self.child_count = None
        self.prop_table: List[RtpcProperty] = []
        self.prop_map = {}
        self.child_table: List[RtpcNode] = []
        self.child_map = {}

    def __repr__(self):
        return '{:08x} pc:{} cc:{} @ {} {:08x}'.format(
            self.name_hash, self.prop_count, self.child_count, self.data_offset, self.data_offset)

    def repr_with_name(self, vfs):
        name = vfs.hash4_where_vhash_select_all(self.name_hash)

        if len(name):
            name = '"{}"'.format(name[0][2].decode('utf-8'))
        else:
            name = f'0x{self.name_hash:08x}'

        return 'n:{} pc:{} cc:{} @ {} {:08x}'.format(
            name, self.prop_count, self.child_count, self.data_offset, self.data_offset)

    def dump_to_string(self, vfs, indent=0):
        ind0 = ' ' * indent
        ind1 = ' ' * (indent + 2)
        ind2 = ' ' * (indent + 4)
        sbuf = ''
        sbuf = sbuf + ind0 + 'node:\n'
        sbuf = sbuf + ind1 + self.repr_with_name(vfs) + '\n'
        sbuf = sbuf + ind1 + 'properties ---------------\n'
        for p in self.prop_table:
            sbuf = sbuf + ind2 + p.repr_with_name(vfs) + '\n'
        sbuf = sbuf + ind1 + 'children -----------------\n'
        for c in self.child_table:
            sbuf = sbuf + c.dump_to_string(vfs, indent + 4)

        return sbuf

    def deserialize(self, f):
        self.name_hash = f.read_u32()
        self.data_offset = f.read_u32()
        self.prop_count = f.read_u16()
        self.child_count = f.read_u16()

        oldp = f.tell()
        f.seek(self.data_offset)
        # read properties
        self.prop_table = []
        for i in range(self.prop_count):
            prop = RtpcProperty()
            prop.deserialize(f)
            self.prop_table.append(prop)
            self.prop_map[prop.name_hash] = prop

        #  children 4-byte aligned
        np = f.tell()
        f.seek(np + (4 - (np % 4)) % 4)

        # read children
        self.child_table = []
        for i in range(self.child_count):
            child = RtpcNode()
            child.deserialize(f)
            self.child_table.append(child)
            self.child_map[child.name_hash] = child

        f.seek(oldp)


class Rtpc:
    def __init__(self):
        self.magic = None
        self.version = None
        self.root_node: Optional[RtpcNode] = None

    def deserialize(self, fraw):
        f = ArchiveFile(fraw)

        self.magic = f.read_strl(4)
        if self.magic != b'RTPC':
            raise Exception('Bad MAGIC {}'.format(self.magic))

        self.version = f.read_u32()

        self.root_node = RtpcNode()
        self.root_node.deserialize(f)

        return self

    def visit(self, visitor, node=None):
        if node is None:
            node = self.root_node

        visitor.process(node)

        for child in node.child_table:
            self.visit(visitor, node=child)

    def dump_to_string(self, vfs):
        return self.root_node.dump_to_string(vfs)
