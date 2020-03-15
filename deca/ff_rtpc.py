from io import BytesIO
from deca.file import ArchiveFile
from deca.fast_file_2 import *
from deca.db_core import VfsDatabase
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


k_type_none = PropType.type_none.value
k_type_u32 = PropType.type_u32.value
k_type_f32 = PropType.type_f32.value
k_type_str = PropType.type_str.value
k_type_vec2 = PropType.type_vec2.value
k_type_vec3 = PropType.type_vec3.value
k_type_vec4 = PropType.type_vec4.value
k_type_mat3x3 = PropType.type_mat3x3.value
k_type_mat4x4 = PropType.type_mat4x4.value
k_type_array_u32 = PropType.type_array_u32.value
k_type_array_f32 = PropType.type_array_f32.value
k_type_array_u8 = PropType.type_array_u8.value
k_type_depreciated_12 = PropType.type_depreciated_12.value
k_type_objid = PropType.type_objid.value
k_type_event = PropType.type_event.value


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


class FieldNameMap:
    def __init__(self, vfs: VfsDatabase):
        self._vfs = vfs
        self._h32_dict = {}
        self._h48_dict = {}
        self._h64_dict = {}

    def lookup(self, hash32=None, hash48=None, hash64=None) -> Optional[str]:
        if hash32 is not None:
            v = self._h32_dict.get(hash32, ())
            if v != ():
                return v
            else:
                v = self._vfs.hash_string_match(hash32=hash32)
                if len(v) > 0:
                    v = v[0][1].decode('utf-8')
                else:
                    v = None
                self._h32_dict[hash32] = v
                return v

        if hash48 is not None:
            v = self._h48_dict.get(hash32, ())
            if v != ():
                return v
            else:
                v = self._vfs.hash_string_match(hash48=hash48)
                if len(v) > 0:
                    v = v[0][1].decode('utf-8')
                else:
                    v = None
                self._h48_dict[hash48] = v
                return v

        if hash64 is not None:
            v = self._h64_dict.get(hash64, ())
            if v != ():
                return v
            else:
                v = self._vfs.hash_string_match(hash64=hash64)
                if len(v) > 0:
                    v = v[0][1].decode('utf-8')
                else:
                    v = None
                self._h64_dict[hash64] = v
                return v

        return None


class RtpcProperty:
    __slots__ = ('pos', 'name_hash', 'data_pos', 'data_raw', 'data', 'type')

    def __init__(self):
        self.pos = None
        self.name_hash = None
        self.data_pos = None
        self.data_raw = None
        self.data = None
        self.type = None

    def __repr__(self):
        data = self.data
        if self.type == k_type_objid:
            data = 'id:0x{:012X}'.format(data)
        elif self.type == k_type_event:
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

    def repr_with_name(self, hash_lookup: FieldNameMap):
        data = self.data
        if self.type == k_type_objid:
            name6 = hash_lookup.lookup(hash48=data & 0x0000FFFFFFFFFFFF)
            name = 'id:0x{:012X}'.format(data)
            if name6:
                name = 'id:DB:H6:"{}"[{}]'.format(name6, name)
            else:
                name4 = hash_lookup.lookup(hash32=data)
                if name4:
                    name = 'id:DB:H4:"{}"[{}]'.format(name4, name)

            data = name

        elif self.type == k_type_event:
            data_new = []
            for d in data:
                name6 = hash_lookup.lookup(hash48=d & 0x0000FFFFFFFFFFFF)
                name = 'ev:0x{:012X}'.format(d)
                if name6:
                    name = 'ev:DB:H6:"{}"[{}]'.format(name6, name)
                else:
                    name4 = hash_lookup.lookup(hash32=d)
                    if name4:
                        name = 'ev:DB:H4:"{}"[{}]'.format(name4, name)

                data_new.append(name)
            data = data_new

        name = hash_lookup.lookup(hash32=self.name_hash)
        if name:
            name = '"{}"'.format(name)
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
        if self.type == k_type_none:
            pass
        elif self.type == k_type_u32:
            self.data = struct.unpack('I', raw_buf)[0]
        elif self.type == k_type_f32:
            self.data = struct.unpack('f', raw_buf)[0]
        elif self.type == k_type_str:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = f.read_strz()
            f.seek(opos)
        elif self.type == k_type_vec2:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(2))
            f.seek(opos)
        elif self.type == k_type_vec3:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(3))
            f.seek(opos)
        elif self.type == k_type_vec4:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(4))
            f.seek(opos)
        elif self.type == k_type_mat3x3:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(9))
            f.seek(opos)
        elif self.type == k_type_mat4x4:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = list(f.read_f32(16))
            f.seek(opos)
        elif self.type == k_type_array_u32:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u32(n))
            f.seek(opos)
        elif self.type == k_type_array_f32:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_f32(n))
            f.seek(opos)
        elif self.type == k_type_array_u8:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            n = f.read_u32()
            self.data = []
            if n > 0:
                self.data = list(f.read_u8(n))
            f.seek(opos)
        elif self.type == k_type_objid:
            opos = f.tell()
            self.data_pos = self.data_raw
            f.seek(self.data_raw)
            self.data = f.read_u64()
            f.seek(opos)
        elif self.type == k_type_event:
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
    __slots__ = (
        'name_hash', 'data_offset', 'prop_count', 'child_count', 'prop_table', 'prop_map', 'child_table', 'child_map'
    )

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

    def repr_with_name(self, hash_lookup: FieldNameMap):
        name4 = hash_lookup.lookup(hash32=self.name_hash)
        name = f'0x{self.name_hash:08x}'

        if name4:
            name = 'DB:H4:"{}"[{}]'.format(name4, name)

        return 'n:{} pc:{} cc:{} @ {} {:08x}'.format(
            name, self.prop_count, self.child_count, self.data_offset, self.data_offset)

    def dump_to_string(self, hash_lookup: FieldNameMap, indent=0):
        ind0 = ' ' * indent
        ind1 = ' ' * (indent + 2)
        ind2 = ' ' * (indent + 4)
        sbuf = ''
        sbuf = sbuf + ind0 + 'node:\n'
        sbuf = sbuf + ind1 + self.repr_with_name(hash_lookup) + '\n'
        sbuf = sbuf + ind1 + 'properties ---------------\n'
        for p in self.prop_table:
            sbuf = sbuf + ind2 + p.repr_with_name(hash_lookup) + '\n'
        sbuf = sbuf + ind1 + 'children -----------------\n'
        for c in self.child_table:
            sbuf = sbuf + c.dump_to_string(hash_lookup, indent + 4)

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
        hash_lookup = FieldNameMap(vfs)
        return self.root_node.dump_to_string(hash_lookup)


"""
Visitor pattern for RTPC files
node_start
    props_start   
        prop_start
        prop_end
        ...
        prop_start
        prop_end
    props_end
    children_start
        node_start
            ...
        node_end
        ...
        node_start
            ...
        node_end
    children_end
node_end 
"""


# @njit()
def parse_prop_data_raise_error(prop_type):
    raise Exception('NOT HANDLED {}'.format(prop_type))


# @njit()
def parse_prop_data(bufn, prop_info):
    prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info

    if prop_type == k_type_none:
        prop_data = prop_data_raw
    elif prop_type == k_type_u32:
        prop_data, pos = ff_read_u32(bufn, prop_data_pos)
    elif prop_type == k_type_f32:
        prop_data, pos = ff_read_f32(bufn, prop_data_pos)
    elif prop_type == k_type_str:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_strz(bufn, prop_data_pos)
    elif prop_type == k_type_vec2:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_f32s(bufn, prop_data_pos, 2)
    elif prop_type == k_type_vec3:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_f32s(bufn, prop_data_pos, 3)
    elif prop_type == k_type_vec4:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_f32s(bufn, prop_data_pos, 4)
    elif prop_type == k_type_mat3x3:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_f32s(bufn, prop_data_pos, 9)
    elif prop_type == k_type_mat4x4:
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_f32s(bufn, prop_data_pos, 16)
    elif prop_type == k_type_array_u32:
        prop_data_pos = prop_data_raw
        pos = prop_data_pos
        n, pos = ff_read_u32(bufn, pos)
        prop_data, pos = ff_read_u32s(bufn, pos, n)
    elif prop_type == k_type_array_f32:
        prop_data_pos = prop_data_raw
        pos = prop_data_pos
        n, pos = ff_read_u32(bufn, pos)
        prop_data, pos = ff_read_f32s(bufn, pos, n)
    elif prop_type == k_type_array_u8:
        prop_data_pos = prop_data_raw
        pos = prop_data_pos
        n, pos = ff_read_u32(bufn, pos)
        prop_data, pos = ff_read_u8s(bufn, pos, n)
    elif prop_type == k_type_objid:
        # todo is the obj id really 64 bits?
        prop_data_pos = prop_data_raw
        prop_data, pos = ff_read_s64(bufn, prop_data_pos)
    elif prop_type == k_type_event:
        prop_data_pos = prop_data_raw
        pos = prop_data_pos
        n, pos = ff_read_u32(bufn, pos)
        prop_data, pos = ff_read_s64s(bufn, pos, n)
    else:
        parse_prop_data_raise_error(prop_type)

    return prop_data, prop_data_pos


class RtpcVisitor:
    def __init__(self):
        pass

    def node_start(self, bufn, pos, index, node_info):
        pass

    def node_end(self, bufn, pos, index, node_info):
        pass

    def props_start(self, bufn, pos, count):
        pass

    def props_end(self, bufn, pos, count):
        pass

    def prop_start(self, bufn, pos, index, prop_info):
        pass

    def children_start(self, bufn, pos, count):
        pass

    def children_end(self, bufn, pos, count):
        pass

    def visit_prop(self, bufn, pos, index):
        prop_pos = pos
        prop_name_hash, pos = ff_read_u32(bufn, pos)
        prop_data_pos = pos
        prop_data_raw, pos = ff_read_u32(bufn, pos)
        prop_type, pos = ff_read_u8(bufn, pos)
        prop_info = (prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type)
        self.prop_start(bufn, prop_pos, index, prop_info)

        return pos

    def visit_node(self, bufn, pos, index):
        node_start_pos = pos

        name_hash, pos = ff_read_u32(bufn, pos)
        data_offset, pos = ff_read_u32(bufn, pos)
        prop_count, pos = ff_read_u16(bufn, pos)
        child_count, pos = ff_read_u16(bufn, pos)
        node_info = (name_hash, data_offset, prop_count, child_count)

        end_header_pos = pos

        self.node_start(bufn, node_start_pos, index, node_info)

        # read properties
        pos = data_offset

        self.props_start(bufn, pos, prop_count)
        for i in range(prop_count):
            pos = self.visit_prop(bufn, pos, i)
        self.props_end(bufn, pos, prop_count)

        # read children
        #  children 4-byte aligned
        org_pos = pos
        pos = pos + (4 - (pos % 4)) % 4
        self.children_start(bufn, pos, child_count)
        for i in range(child_count):
            pos = self.visit_node(bufn, pos, i)
        self.children_end(bufn, pos, child_count)

        self.node_end(bufn, node_start_pos, index, node_info)

        return end_header_pos

    def visit(self, buffer):
        pos = 0
        n_buffer = len(buffer)
        bufn = (buffer, n_buffer)
        magic, pos = ff_read(bufn, pos, 4)
        if magic != b'RTPC':
            raise Exception('Bad MAGIC {}'.format(magic))

        version, pos = ff_read_u32(bufn, pos)

        self.visit_node(bufn, pos, 0)


class RtpcVisitorDumpToString(RtpcVisitor):
    def __init__(self, vfs: VfsDatabase):
        super(RtpcVisitorDumpToString, self).__init__()
        self.hash_lookup = FieldNameMap(vfs)
        self._result = None
        self._lines = []
        self._depth = -1
        self._ind0 = None
        self._ind1 = None
        self._ind2 = None

    def result(self):
        self._result = '\n'.join(self._lines)
        return self._result

    def process_depth(self):
        self._ind0 = ' ' * self._depth
        self._ind1 = ' ' * (self._depth + 2)
        self._ind2 = ' ' * (self._depth + 4)

    def visit(self, buffer):
        self._result = ''
        self._lines = []
        self._depth = -2
        super(RtpcVisitorDumpToString, self).visit(buffer)

    def node_start(self, bufn, pos, index, node_info):
        self._depth += 2
        self.process_depth()

        name_hash, data_offset, prop_count, child_count = node_info
        name4 = self.hash_lookup.lookup(hash32=name_hash)
        name = f'0x{name_hash:08x}'

        if name4:
            name = 'DB:H4:"{}"[{}]'.format(name4, name)

        node_info_str = 'n:{} pc:{} cc:{} @ {} {:08x}'.format(
            name, prop_count, child_count, data_offset, data_offset)

        self._lines.append(self._ind0 + 'node:')
        self._lines.append(self._ind1 + node_info_str)

    def node_end(self, bufn, pos, index, node_info):
        self._depth -= 2
        self.process_depth()

    def children_start(self, bufn, pos, count):
        self._lines.append(self._ind1 + 'children -----------------')
        self._depth += 2
        self.process_depth()

    def children_end(self, bufn, pos, count):
        self._depth -= 2
        self.process_depth()

    def props_start(self, bufn, pos, count):
        self._lines.append(self._ind1 + 'properties ---------------')

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info

        prop_data, prop_data_pos = parse_prop_data(bufn, prop_info)

        if prop_type == k_type_objid:
            name6 = self.hash_lookup.lookup(hash48=prop_data & 0x0000FFFFFFFFFFFF)
            name = 'id:0x{:012X}'.format(prop_data)
            if name6:
                name = 'id:DB:H6:"{}"[{}]'.format(name6, name)
            else:
                name4 = self.hash_lookup.lookup(hash32=prop_data)
                if name4:
                    name = 'id:DB:H4:"{}"[{}]'.format(name4, name)

            prop_data = name

        elif prop_type == k_type_event:
            data_new = []
            for d in prop_data:
                name6 = self.hash_lookup.lookup(hash48=d & 0x0000FFFFFFFFFFFF)
                name = 'ev:0x{:012X}'.format(d)
                if name6:
                    name = 'ev:DB:H6:"{}"[{}]'.format(name6, name)
                else:
                    name4 = self.hash_lookup.lookup(hash32=d)
                    if name4:
                        name = 'ev:DB:H4:"{}"[{}]'.format(name4, name)

                data_new.append(name)
            prop_data = data_new

        name = self.hash_lookup.lookup(hash32=prop_name_hash)
        if name:
            name = '"{}"'.format(name)
        else:
            name = f'0x{prop_name_hash:08x}'

        self._lines.append(
            self._ind2 + '@0x{:08x}({: 8d}) {} 0x{:08x} 0x{:02x} {:6s} = @0x{:08x}({: 8d}) {}'.format(
                prop_pos, prop_pos,
                name,
                prop_data_raw,
                prop_type,
                PropType_names[prop_type],
                prop_data_pos, prop_data_pos,
                prop_data
            )
        )


class RtpcVisitorGatherStrings(RtpcVisitor):
    def __init__(self):
        super(RtpcVisitorGatherStrings, self).__init__()
        self.strings = set()

    def visit(self, buffer):
        self.strings = set()
        super(RtpcVisitorGatherStrings, self).visit(buffer)

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info

        if prop_type == k_type_str:
            prop_data, prop_data_pos = parse_prop_data(bufn, prop_info)
            self.strings.add(prop_data)
