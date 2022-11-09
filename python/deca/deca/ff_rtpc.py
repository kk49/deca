from deca.file import ArchiveFile
from deca.fast_file_2 import *
from deca.db_core import VfsDatabase
from deca.hashes import hash32_func
import struct
from enum import IntEnum
from typing import List, Optional


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
    type_unk_15 = 15
    type_unk_16 = 16


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
k_type_unk_15 = PropType.type_unk_15.value
k_type_unk_16 = PropType.type_unk_16.value


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
    'unk_15',
    'unk_16',
]

h_prop_class = hash32_func('_class')
h_prop_class_hash = hash32_func('_class_hash')
h_prop_name = hash32_func('name')
h_prop_world = hash32_func('world')
h_prop_script = hash32_func('script')
h_prop_border = hash32_func('border')
h_prop_object_id = hash32_func('_object_id')
h_prop_label_key = hash32_func('label_key')
h_prop_note = hash32_func('note')
h_prop_spline = hash32_func('spline')
h_prop_spawn_tags = hash32_func('spawn_tags')
h_prop_model_skeleton = hash32_func('model_skeleton')
h_prop_skeleton = hash32_func('skeleton')
h_prop_need_type = hash32_func('need_type')
h_prop_start_time = hash32_func('start_time')

h_prop_item_item_id = hash32_func('[Item]  Item ID')
h_prop_ref_apex_identifier = hash32_func('[ref] apex identifier')

# guess at naming these fields
h_prop_deca_crafting_type = 0xa949bc65
h_prop_deca_cpoi_desc = 0xe6b6b3f9


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
            v = self._h48_dict.get(hash48, ())
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


class Rtpc:
    def __init__(self):
        self.magic = None
        self.version = None
        self.root_node: Optional[RtpcNode] = None


def rtpc_prop_from_binary(f, prop):
    prop.pos = f.tell()
    prop.name_hash = f.read_u32()
    prop.data_pos = f.tell()
    prop.data_raw = f.read_u32()
    prop.type = f.read_u8()

    prop.data = prop.data_raw

    raw_buf = struct.pack('I', prop.data_raw)
    if prop.type == k_type_none:
        pass
    elif prop.type == k_type_u32:
        prop.data = struct.unpack('I', raw_buf)[0]
    elif prop.type == k_type_f32:
        prop.data = struct.unpack('f', raw_buf)[0]
    elif prop.type == k_type_str:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = f.read_strz()
        f.seek(opos)
    elif prop.type == k_type_vec2:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = list(f.read_f32(2))
        f.seek(opos)
    elif prop.type == k_type_vec3:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = list(f.read_f32(3))
        f.seek(opos)
    elif prop.type == k_type_vec4:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = list(f.read_f32(4))
        f.seek(opos)
    elif prop.type == k_type_mat3x3:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = list(f.read_f32(9))
        f.seek(opos)
    elif prop.type == k_type_mat4x4:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = list(f.read_f32(16))
        f.seek(opos)
    elif prop.type == k_type_array_u32:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        n = f.read_u32()
        prop.data = []
        if n > 0:
            prop.data = list(f.read_u32(n))
        f.seek(opos)
    elif prop.type == k_type_array_f32:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        n = f.read_u32()
        prop.data = []
        if n > 0:
            prop.data = list(f.read_f32(n))
        f.seek(opos)
    elif prop.type == k_type_array_u8:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        n = f.read_u32()
        prop.data = []
        if n > 0:
            prop.data = list(f.read_u8(n))
        f.seek(opos)
    elif prop.type == k_type_objid:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        prop.data = f.read_u64()
        f.seek(opos)
    elif prop.type == k_type_event:
        opos = f.tell()
        prop.data_pos = prop.data_raw
        f.seek(prop.data_raw)
        n = f.read_u32()
        prop.data = []
        for i in range(n):
            prop.data.append(f.read_u64())
        f.seek(opos)
    elif prop.type == k_type_unk_15:
        pass
    elif prop.type == k_type_unk_16:
        pass
    else:
        raise Exception('NOT HANDLED {}'.format(prop.type))


def rtpc_node_from_binary(f, node):
    node.name_hash = f.read_u32()
    node.data_offset = f.read_u32()
    node.prop_count = f.read_u16()
    node.child_count = f.read_u16()

    old_p = f.tell()
    f.seek(node.data_offset)
    # read properties
    node.prop_table = []
    for i in range(node.prop_count):
        prop = RtpcProperty()
        rtpc_prop_from_binary(f, prop)
        node.prop_table.append(prop)
        node.prop_map[prop.name_hash] = prop

    #  children 4-byte aligned
    pos = f.tell()
    f.seek(pos + (4 - (pos % 4)) % 4)

    # read children
    node.child_table = []
    for i in range(node.child_count):
        child = RtpcNode()
        rtpc_node_from_binary(f, child)
        node.child_table.append(child)
        node.child_map[child.name_hash] = child

    f.seek(old_p)


def rtpc_from_binary(f_raw, rtpc: Optional[Rtpc] = None):
    if rtpc is None:
        rtpc = Rtpc()

    f = ArchiveFile(f_raw)

    rtpc.magic = f.read_strl(4)
    if rtpc.magic != b'RTPC':
        raise Exception('Bad MAGIC {}'.format(rtpc.magic))

    rtpc.version = f.read_u32()

    rtpc.root_node = RtpcNode()
    rtpc_node_from_binary(f, rtpc.root_node)

    return rtpc


def rtpc_prop_to_string(prop0, hash_lookup: FieldNameMap):
    if isinstance(prop0, RtpcProperty):
        prop_pos = prop0.pos
        prop_name_hash = prop0.name_hash
        prop_data_raw = prop0.data_raw
        prop_type = prop0.type
        prop_data = prop0.data
        prop_data_pos = prop0.data_pos
    else:
        prop_pos, prop_name_hash, prop_data_pos0, prop_data_raw, prop_type, prop_data, prop_data_pos = prop0

    data = prop_data
    if prop_type == k_type_objid:
        name6 = hash_lookup.lookup(hash48=data & 0x0000FFFFFFFFFFFF)
        name = 'id:0x{:012X}'.format(data)
        if name6:
            name = 'id:DB:H6:"{}"[{}]'.format(name6, name)
        else:
            name4 = hash_lookup.lookup(hash32=data)
            if name4:
                name = 'id:DB:H4:"{}"[{}]'.format(name4, name)

        data = name

    elif prop_type == k_type_event:
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

    elif prop_type in {k_type_u32, k_type_unk_15, k_type_unk_16}:
        d = data
        name = '{} (0x{:08X})'.format(d, d)
        name4 = hash_lookup.lookup(hash32=d)
        if name4:
            name = 'u32:DB:H4:"{}"[{}]'.format(name4, name)
        data = name
    elif prop_type == k_type_array_u32:
        data_new = []
        for d in data:
            name = '{} (0x{:08X})'.format(d, d)
            name4 = hash_lookup.lookup(hash32=d)
            if name4:
                name = 'u32:DB:H4:"{}"[{}]'.format(name4, name)

            data_new.append(name)
        data = data_new

    name = hash_lookup.lookup(hash32=prop_name_hash)
    if name:
        name = f'"{name}"[0x{prop_name_hash:08x}]'
    else:
        name = f'0x{prop_name_hash:08x}'

    return '@0x{:08x}({: 8d}) {} 0x{:08x} 0x{:02x} {:6s} = @0x{:08x}({: 8d}) {} '.format(
        prop_pos, prop_pos,
        name,
        prop_data_raw,
        prop_type,
        PropType_names[prop_type],
        prop_data_pos, prop_data_pos,
        data)
    # return '0x{:08x}: {} = {}'.format(self.name_hash, PropType.type_names[self.type], self.data,)


def rtpc_node_to_string(node: RtpcNode, hash_lookup: FieldNameMap, indent=0):
    ind0 = ' ' * indent
    ind1 = ' ' * (indent + 2)
    ind2 = ' ' * (indent + 4)
    sbuf = ''
    sbuf = sbuf + ind0 + 'node:\n'
    sbuf = sbuf + ind1 + node.repr_with_name(hash_lookup) + '\n'
    sbuf = sbuf + ind1 + 'properties ---------------\n'
    for p in node.prop_table:
        sbuf = sbuf + ind2 + rtpc_prop_to_string(p, hash_lookup) + '\n'
    sbuf = sbuf + ind1 + 'children -----------------\n'
    for c in node.child_table:
        sbuf = sbuf + rtpc_node_to_string(c, hash_lookup, indent + 4)

    return sbuf


def rtpc_to_string(rtpc: Rtpc, vfs):
    hash_lookup = FieldNameMap(vfs)
    return rtpc_node_to_string(rtpc.root_node, hash_lookup)


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
    elif prop_type == k_type_unk_15:
        prop_data = prop_data_raw
    elif prop_type == k_type_unk_16:
        prop_data = prop_data_raw
    else:
        prop_data = None
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
        prop = (*prop_info, *parse_prop_data(bufn, prop_info))

        self._lines.append(self._ind2 + rtpc_prop_to_string(prop, self.hash_lookup))


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
