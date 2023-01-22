import io
import os
import enum
import struct
from typing import List, Dict
from io import BytesIO
from deca.errors import *
from deca.file import ArchiveFile
from deca.fast_file import *
from deca.hashes import hash32_func
from deca.ff_types import FTYPE_ADF_BARE, FTYPE_ADF0, FTYPE_ADF5
from deca.db_core import VfsDatabase, VfsNode

# https://github.com/tim42/gibbed-justcause3-tools-fork/blob/master/Gibbed.JustCause3.FileFormats/AdfFile.cs

# TODO first pass find types?
# TODO first pass find string hashes?
# TODO ./files/effects/vehicles/wheels/rear_snow.effc good for basic types

adf_hash_fields = {
    'EquipmentHash', 'Name', 'RegionHash',
    'Character', 'SkinTone', 'Stereotype',
    'LocationId',
}


class GdcArchiveEntry:
    __slots__ = (
        'index',
        'offset',
        'size',
        'v_path',
        'v_hash',
        'filetype_hash',
        'adf_type_hash',
    )

    def __init__(self, index, offset, size, v_hash, filetype_hash, adf_type_hash, v_path):
        self.index = index
        self.offset = offset
        self.size = size
        self.v_path = v_path
        self.v_hash = v_hash
        self.filetype_hash = filetype_hash
        self.adf_type_hash = adf_type_hash

    def __repr__(self):
        str_vhash = ''
        if self.v_hash is not None:
            str_vhash = ' h:{:08X}'.format(self.v_hash)

        str_fthash = ''
        if self.filetype_hash is not None:
            str_fthash = ' ft:{:08x}'.format(self.filetype_hash)

        str_adfhash = ''
        if self.adf_type_hash is not None:
            str_adfhash = ' adf:{:08x}'.format(self.adf_type_hash)

        str_size = 's:None'
        if self.size is not None:
            str_size = 's:{:9d}'.format(self.size)

        return 'i:{:4d} o:{:9d} {}{}{}{} vp:{}'.format(
            self.index, self.offset, str_size, str_vhash, str_fthash, str_adfhash, self.v_path.decode('utf-8'))


class StringHash:
    def __init__(self):
        self.value = None
        self.value_hash = None

    def deserialize(self, f, nt):
        self.value = f.read_strz()
        self.value_hash = f.read_u64()


class MemberDef:
    def __init__(self):
        self.name = None
        self.name_utf8 = None
        self.type_hash = None
        self.size = None
        self.offset = None
        self.bit_offset = None
        self.default_type = None
        self.default_value = None

    def deserialize(self, f, nt):
        self.name = nt[f.read_u64()][1]
        self.name_utf8 = self.name.decode('utf-8')
        self.type_hash = f.read_u32()
        self.size = f.read_u32()
        offset = f.read_u32()
        self.bit_offset = (offset >> 24) & 0xff
        self.offset = offset & 0x00ffffff
        self.default_type = f.read_u32()
        self.default_value = f.read_u64()


class EnumDef:
    def __init__(self):
        self.name = None
        self.value = None

    def deserialize(self, f, nt):
        self.name = nt[f.read_u64()][1]
        self.value = f.read_u32()

        # print(self.name, self.value)


class MetaType(enum.IntEnum):
    Primative = 0
    Structure = 1
    Pointer = 2
    Array = 3
    InlineArray = 4
    String = 5
    MetaType6 = 6
    Bitfield = 7
    Enumeration = 8
    StringHash = 9


class TypeDef:
    def __init__(self):
        self.META_position = None
        self.metatype = None
        self.size = None
        self.alignment = None
        self.type_hash = None
        self.name = None
        self.flags = None
        self.element_type_hash = None
        self.element_length = None
        self.members = None

    def deserialize(self, f, nt):
        self.META_position = f.tell()
        self.metatype = f.read_u32()
        self.size = f.read_u32()
        self.alignment = f.read_u32()
        self.type_hash = f.read_u32()
        self.name = nt[f.read_u64()][1]
        self.flags = f.read_u32()
        self.element_type_hash = f.read_u32()
        self.element_length = f.read_u32()

        if self.metatype == 0:  # Primative
            pass
        elif self.metatype == 1:  # Structure
            member_count = f.read_u32()
            self.members = [MemberDef() for _ in range(member_count)]
            for i in range(member_count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 2:  # Pointer
            count = f.read_u32()
            if count != 0:
                # raise Exception('Not Implemented: count == {}'.format(count))
                print('Pointer: Not Implemented: count == {}'.format(count))
        elif self.metatype == 3:  # Array
            count = f.read_u32()
            if count != 0:
                # raise Exception('Not Implemented: count == {}'.format(count))
                print('Array: Not Implemented: count == {}'.format(count))
        elif self.metatype == 4:  # Inline Array
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        elif self.metatype == 7:  # BitField
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        elif self.metatype == 8:  # Enumeration
            count = f.read_u32()
            self.members = [EnumDef() for _ in range(count)]
            for i in range(count):
                self.members[i].deserialize(f, nt)
        elif self.metatype == 9:  # String Hash
            count = f.read_u32()
            if count != 0:
                raise Exception('Not Implemented: count == {}'.format(count))
        else:
            raise Exception('Unknown Typedef Type {}'.format(self.metatype))


class InstanceEntry:
    def __init__(self):
        self.META_position = None
        self.name_hash = None
        self.type_hash = None
        self.offset = None
        self.size = None
        self.name = None

    def deserialize(self, f, nt):
        self.META_position = f.tell()
        self.name_hash = f.read_u32()
        self.type_hash = f.read_u32()
        self.offset = f.read_u32()
        self.size = f.read_u32()
        self.name = nt[f.read_u64()][1]
        # print('{:08x}'.format(self.name_hash), '{:08x}'.format(self.type_hash), self.offset, self.size, self.name)
        # print('FP End', f.tell())

    # def read(self, type_systems, f):
    #     if self.type_hash not in type_systems:
    #         raise EDecaMissingAdfType(self.type_hash)
    #     td = type_systems[self.type_hash]
    #     f.seek(self.offset)
    #     v = td.read(type_systems, f)
    #     return v


typedef_s8 = 0x580D0A62
typedef_u8 = 0x0ca2821d
typedef_s16 = 0xD13FCF93
typedef_u16 = 0x86d152bd
typedef_s32 = 0x192fe633
typedef_u32 = 0x075e4e4f
typedef_s64 = 0xAF41354F
typedef_u64 = 0xA139E01F
typedef_f32 = 0x7515a207
typedef_f64 = 0xC609F663

prim_types = {
    typedef_s8,
    typedef_u8,
    typedef_s16,
    typedef_u16,
    typedef_s32,
    typedef_u32,
    typedef_s64,
    typedef_u64,
    typedef_f32,
    typedef_f64,
}

prim_type_names = {
    0x580D0A62: 'sint08',
    0x0ca2821d: 'uint08',
    0xD13FCF93: 'sint16',
    0x86d152bd: 'uint16',
    0x192fe633: 'sint32',
    0x075e4e4f: 'uint32',
    0xAF41354F: 'sint64',
    0xA139E01F: 'uint64',
    0x7515a207: 'float',
    0xC609F663: 'double',
    0x8955583e: 'string',
}


def dump_type(type_id, type_map, offset=0, displayed_types=None):
    if displayed_types is None:
        displayed_types = []

    if type_id in prim_type_names:
        return '{}PrimType: {}\n'.format(' ' * offset, prim_type_names[type_id])

    if type_id not in type_map:
        return '{}UNKNOWN TYPE: {:08x}\n'.format(' ' * offset, type_id)
        # raise EDecaMissingAdfType(type_id)
    type_def = type_map[type_id]

    space = ' ' * offset

    if type_id in displayed_types:
        return space + 'Recursive use of {} type 0x{:08x}\n'.format(MetaType(type_def.metatype).name, type_id)

    sbuf = space + '{}\n'.format(MetaType(type_def.metatype).name)

    if type_def.metatype == 0:  # Primative
        pass
    elif type_def.metatype == 1:  # Structure
        for m in type_def.members:
            sbuf = sbuf + '{}{} o:{}({:08x})[{}] s:{} t:{:08x} dt:{:08x} dv:{:016x}\n'.format(
                ' ' * (offset + 2), m.name_utf8, m.offset, m.offset, m.bit_offset, m.size, m.type_hash, m.default_type, m.default_value)
            sbuf = sbuf + dump_type(m.type_hash, type_map, offset + 4, displayed_types=displayed_types + [type_id])
    elif type_def.metatype == 2:  # Pointer
        pass
    elif type_def.metatype == 3:  # Array
        sbuf = sbuf + '{}Length: {}\n'.format(' ' * (offset + 2), type_def.element_length)
        sbuf = sbuf + dump_type(type_def.element_type_hash, type_map, offset+2, displayed_types=displayed_types + [type_id])
    elif type_def.metatype == 4:  # Inline Array
        sbuf = sbuf + '{}Length: {}\n'.format(' ' * (offset + 2), type_def.element_length)
        sbuf = sbuf + dump_type(type_def.element_type_hash, type_map, offset+2, displayed_types=displayed_types + [type_id])
    elif type_def.metatype == 7:  # BitField
        pass
    elif type_def.metatype == 8:  # Enumeration
        pass
    elif type_def.metatype == 9:  # String Hash
        pass
    else:
        raise Exception('Unknown Typedef Type {}'.format(type_def.metatype))

    # print(sbuf)

    return sbuf


def adf_type_id_to_str(type_id, type_map):
    if type_id in prim_type_names:
        return prim_type_names[type_id]
    if type_id == 0xdefe88ed:
        return 'DEFERRED'

    type_def = type_map[type_id]

    if type_def.metatype == 0:  # Primative
        pass
    elif type_def.metatype == 1:  # Structure
        return 'Structure {}'.format(type_def.name.decode('utf-8'))
    elif type_def.metatype == 2:  # Pointer
        return 'Pointer'
    elif type_def.metatype == 3:  # Array
        return 'Array of {}'.format(adf_type_id_to_str(type_def.element_type_hash, type_map))
    elif type_def.metatype == 4:  # Inline Array
        return 'Inline Array of {}'.format(adf_type_id_to_str(type_def.element_type_hash, type_map))
    elif type_def.metatype == 7:  # BitField
        return 'Bitfield'
    elif type_def.metatype == 8:  # Enumeration
        return 'Enum'
    elif type_def.metatype == 9:  # String Hash
        return 'String Hash'
    else:
        raise Exception('Unknown Typedef Type {}'.format(type_def.metatype))


class AdfValue:
    __slots__ = ('value', 'type_id', 'info_offset', 'data_offset', 'bit_offset', 'enum_string', 'hash_string')

    def __init__(self, value, type_id, info_offset, data_offset=None, bit_offset=None, enum_string=None, hash_string=None):
        self.value = value
        self.type_id = type_id
        self.info_offset = info_offset
        if data_offset is None:
            self.data_offset = info_offset
        else:
            self.data_offset = data_offset
        self.bit_offset = bit_offset
        self.enum_string = enum_string
        self.hash_string = hash_string

    def __repr__(self):
        s = '{} : 0x{:08X} @ {}(0x{:08x})'.format(self.value, self.type_id, self.data_offset, self.data_offset)

        if self.bit_offset is not None:
            s = s + '[{}]'.format(self.bit_offset)

        if self.data_offset != self.info_offset:
            s = s + ' <- {}(0x{:08x})'.format(self.info_offset, self.info_offset)

        if self.enum_string is not None:
            s = s + '  # {}'.format(self.enum_string)

        if self.hash_string is not None:
            s = s + '  # {}'.format(self.hash_string)

        return s


def hash_lookup(vfs: VfsDatabase, hash_code, default=None, prefix=''):
    if isinstance(hash_code, int):
        ele = vfs.lookup_equipment_from_hash(hash_code)
        if ele is not None:
            display_name_hash = ele["DisplayNameHash"]
            display_name = vfs.hash_string_match(hash32=display_name_hash)
            if display_name:
                display_name = display_name[0][1].decode('utf-8')
                display_translated = vfs.lookup_translation_from_name(display_name)
                if display_translated is None:
                    display_translated = display_name
            else:
                display_translated = display_name_hash
            return f'{prefix}# {ele["EquipmentName"].decode("utf-8")} "{display_translated}"'
        else:
            hsm = vfs.hash_string_match(hash32=hash_code)
            if hsm:
                display_name = hsm[0][1].decode('utf-8')
                return f'{prefix}# {display_name}'

    return default


def adf_format(v, vfs: VfsDatabase, type_map, indent=0):
    if isinstance(v, AdfValue):
        type_def = type_map.get(v.type_id, TypeDef())

        s = ''
        s = s + '{}(0x{:08X}), Data Offset: {}(0x{:08x})'.format(
            adf_type_id_to_str(v.type_id, type_map), v.type_id, v.data_offset, v.data_offset)

        if v.bit_offset is not None:
            s = s + '[{}]'.format(v.bit_offset)

        if v.data_offset != v.info_offset:
            s = s + ', Info Offset: {}(0x{:08x})'.format(v.info_offset, v.info_offset)

        value_info = s
        s = ''
        if v.type_id == 0xdefe88ed:
            s = s + '  ' * indent + '# {}\n'.format(value_info)
            s = s + adf_format(v.value, vfs, type_map, indent)
        elif type_def.metatype is None or type_def.metatype == MetaType.Primative:
            s = s + '  ' * indent + '{}  # {}\n'.format(v.value, value_info)
        elif type_def.metatype == MetaType.Structure:
            s = s + '  ' * indent + '# ' + value_info + '\n'
            s = s + '  ' * indent + '{\n'
            for k, iv in v.value.items():
                s = s + '  ' * (indent + 1) + k + ':\n'
                s = s + adf_format(iv, vfs, type_map, indent + 2)
                # add details for equipment hashes
                # if isinstance(iv.value, int) and k in adf_hash_fields:
                if not hasattr(iv, 'value'):
                    pass
                elif isinstance(iv.value, int):
                    hs = hash_lookup(vfs, iv.value)
                    if hs:
                        s = s + '  ' * (indent + 2) + hs + '\n'

            s = s + '  ' * indent + '}\n'
        elif type_def.metatype == MetaType.Pointer:
            s = s + '  ' * indent + '{}  # {}\n'.format(v.value, value_info)
        elif type_def.metatype in {MetaType.Array, MetaType.InlineArray}:
            s = s + '  ' * indent + '# ' + value_info + '\n'
            s = s + '  ' * indent + '[\n'
            for iv in v.value:
                s = s + adf_format(iv, vfs, type_map, indent + 1)
            s = s + '  ' * indent + ']\n'
        elif type_def.metatype == MetaType.String:
            s = s + '  ' * indent + '{}  # {}\n'.format(v.value, value_info)
        elif type_def.metatype == MetaType.Bitfield:
            s = s + '  ' * indent + '{}  # {}\n'.format(v.value, value_info)
        elif type_def.metatype == MetaType.Enumeration:
            s = s + '  ' * indent + '{} ({})  # {}\n'.format(v.enum_string, v.value, value_info)
        elif type_def.metatype == MetaType.StringHash:
            if type_def.size == 4:
                vp = '0x{:08x}'.format(v.value)
                hash_string = v.hash_string
                if hash_string is None:
                    name = vfs.hash_string_match(hash32=v.value)
                    if len(name):
                        hash_string = 'DB:"{}"'.format(name[0][1].decode('utf-8'))
                    else:
                        hash_string = 'Hash4:0x{:08x}'.format(v.value)
            elif type_def.size == 6:
                vp = '0x{:012x}'.format(v.value)
                hash_string = v.hash_string
                if hash_string is None:
                    name = vfs.hash_string_match(hash48=v.value & 0x0000FFFFFFFFFFFF)
                    if len(name):
                        hash_string = 'DB:"{}"'.format(name[0][1].decode('utf-8'))
                    else:
                        hash_string = 'Hash6:0x{:012x}'.format(v.value)
            elif type_def.size == 8:
                vp = '0x{:016x}'.format(v.value)
                hash_string = v.hash_string
                if hash_string is None:
                    name48 = vfs.hash_string_match(hash48=v.value & 0x0000FFFFFFFFFFFF)
                    if len(name48):
                        hash_string = 'DB:H6:"{}"'.format(name48[0][1].decode('utf-8'))
                    else:
                        name64 = vfs.hash_string_match(hash48=v.value)
                        if len(name64):
                            hash_string = 'DB:H6:"{}"'.format(name64[0][1].decode('utf-8'))
                        else:
                            hash_string = 'Hash8:0x{:016x}'.format(v.value)
            else:
                vp = v.value
                hash_string = v.hash_string
                if hash_string is None:
                    hash_string = 'OTHER HASH {}'.format(type_def.size)

            s = s + '  ' * indent + '{} ({})  # {}\n'.format(hash_string, vp, value_info)

        return s
    elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], GdcArchiveEntry):
        s = ''
        s = s + '  ' * indent + '[\n'
        for ent in v:
            comment = hash_lookup(vfs, ent, default='', prefix='  ')
            s = s + '  ' * (indent + 1) + f'{ent}{comment}\n'
        s = s + '  ' * indent + ']\n'

        return s
    else:
        comment = hash_lookup(vfs, v, default='', prefix='  ')
        return '  ' * indent + f'{v}{comment}\n'


def adf_value_extract(v):
    if isinstance(v, AdfValue):
        return adf_value_extract(v.value)
    elif isinstance(v, dict):
        n = {}
        for k, iv in v.items():
            n[k] = adf_value_extract(iv)
        return n
    elif isinstance(v, list):
        return [adf_value_extract(iv) for iv in v]
    else:
        return v


def read_instance(
        buffer, n_buffer, buffer_pos, type_id, map_typedef, map_string_hash, abs_offset,
        bit_offset=None, found_strings=None):

    dpos = buffer_pos
    if type_id == typedef_s8:
        v, buffer_pos = ff_read_s8(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_u8:
        v, buffer_pos = ff_read_u8(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_s16:
        v, buffer_pos = ff_read_s16(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_u16:
        v, buffer_pos = ff_read_u16(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_s32:
        v, buffer_pos = ff_read_s32(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_u32:
        v, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_s64:
        v, buffer_pos = ff_read_s64(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_u64:
        v, buffer_pos = ff_read_u64(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_f32:
        v, buffer_pos = ff_read_f32(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)
    elif type_id == typedef_f64:
        v, buffer_pos = ff_read_f64(buffer, n_buffer, buffer_pos)
        v = AdfValue(v, type_id, dpos + abs_offset)

    elif type_id == 0x8955583e:
        offset, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
        length, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
        opos = buffer_pos
        buffer_pos = offset
        # TODO Size may be needed for byte codes?

        # v = f.read_c8(length)
        # v = b''.join(v)
        v, buffer_pos = ff_read_strz(buffer, n_buffer, buffer_pos)

        if found_strings is not None:
            found_strings.add(v)

        buffer_pos = opos

        v = AdfValue(v, type_id, dpos + abs_offset, offset + abs_offset)

    # TODO: this seems to be missing in some cases, i.e. the case of meshc files for CharacterMesh1UVMesh
    elif type_id == 0xdefe88ed:  # deferred value
        v0, buffer_pos = ff_read_u32s(buffer, n_buffer, buffer_pos, 4)
        if v0[0] == 0 or v0[2] == 0:
            v = None
        else:
            opos = buffer_pos
            buffer_pos = v0[0]
            try:
                v, buffer_pos = read_instance(
                    buffer, n_buffer, buffer_pos, v0[2], map_typedef, map_string_hash, abs_offset,
                    found_strings=found_strings)
            except EDecaMissingAdfType as e:
                v = f"!!!MISSING TYPE:  0x{e.type_id:08x} in 0x{v0[2]:08x}[{v0[1]}]"
            buffer_pos = opos
            v = AdfValue(v, type_id, dpos + abs_offset, v0[0] + abs_offset)

    elif type_id == 0x178842fe:  # gdc/global.gdcc
        # TODO this should probably be it's own file type and the adf should be considered a wrapper
        gdf_buffer = buffer[buffer_pos:]
        gdf_n_buffer = len(gdf_buffer)
        gdf_buffer_pos = 0

        count, gdf_buffer_pos = ff_read_u32s(gdf_buffer, gdf_n_buffer, gdf_buffer_pos, 8)
        assert(count[0] == 32)
        assert(count[1] == 16)
        assert(count[2] == count[6])
        assert(count[3] == 0)
        # assert(count[4] == filesize +- k)
        assert(count[5] == 16)
        assert(count[6] == count[2])
        assert(count[7] == 0)
        dir_list = []
        for i in range(count[2]):
            d00_offset, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d04_unk, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d08_filetype_hash, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d12_unk, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d16_vpath_offset, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d20_unk, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d24_unk, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            d28_unk, gdf_buffer_pos = ff_read_u32(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            assert(d04_unk == 16)
            assert(d12_unk == 0)
            assert(d20_unk == 16)
            assert(d24_unk == 0)
            assert(d28_unk == 0)
            entry = [d00_offset, d16_vpath_offset, d08_filetype_hash, d04_unk, d12_unk, d20_unk, d24_unk, d28_unk]
            dir_list.append(entry)

        dir_contents = []
        idx = 0
        for e1 in dir_list:
            # TODO something weird is going on with this second header, sometimes it makes sense, sometimes it may
            # have floats? or indicate that is should be 24 byte long?
            string_offset = e1[1]
            ftype_hash = e1[2]

            gdf_buffer_pos = string_offset
            v_path, gdf_buffer_pos = ff_read_strz(gdf_buffer, gdf_n_buffer, gdf_buffer_pos)
            v_hash = hash32_func(v_path)

            if ftype_hash in {0xD74CC4CB}:  # RTPC read directly
                # TODO this follows the data structure for an array of some type, 0xD74CC4CB is probably it's hash
                gdf_buffer_pos = e1[0]
                header2, gdf_buffer_pos = ff_read_u32s(gdf_buffer, gdf_n_buffer, gdf_buffer_pos, 4)
                actual_offset = header2[0]
                actual_size = header2[2]
                adf_type_hash = None
            else:  # TODO current guess is that it is a bare ADF instance
                actual_offset = e1[0]
                actual_size = None
                adf_type_hash = ftype_hash

            entry = GdcArchiveEntry(
                index=idx,
                offset=actual_offset,
                size=actual_size,
                v_hash=v_hash,
                filetype_hash=ftype_hash,
                adf_type_hash=adf_type_hash,
                v_path=v_path)
            dir_contents.append(entry)
            idx += 1
        v = dir_contents

    else:
        if type_id not in map_typedef:
            raise EDecaMissingAdfType(type_id)
        type_def = map_typedef[type_id]

        if type_def.metatype == 0:  # Primative
            raise EDecaMissingAdfType(type_id)
        elif type_def.metatype == 1:  # Structure
            v = {}
            p0 = buffer_pos
            for m in type_def.members:
                buffer_pos = p0 + m.offset
                nm = m.name_utf8
                vt, buffer_pos = read_instance(
                    buffer, n_buffer, buffer_pos, m.type_hash, map_typedef, map_string_hash, abs_offset,
                    bit_offset=m.bit_offset, found_strings=found_strings)
                v[nm] = vt
                # print(nm, vt)
            p1 = buffer_pos
            buffer_pos = p0 + type_def.size

            v = AdfValue(v, type_id, p0 + abs_offset)

        elif type_def.metatype == 2:  # Pointer
            v0, buffer_pos = ff_read_u64(buffer, n_buffer, buffer_pos)
            v = (v0, 'NOTE: {}: {:016x} to {:08x}'.format(type_def.name, v0, type_def.element_type_hash))
            # TODO not sure how this is used yet, but it's used by effects so lower priority
            # raise EDecaMissingAdfType(type_id)
        elif type_def.metatype in {3, 4}:  # Array or Inline Array
            if type_def.metatype == 3:
                v0, buffer_pos = ff_read_u32s(buffer, n_buffer, buffer_pos, 3)
                opos = buffer_pos

                offset = v0[0]
                flags = v0[1]
                length = v0[2]
                # unknown = v0[3] sometimes does not exist, is it even real data, in some cases it removed in GZ EXE
                align = None
                # aligning based on element size info
                # if type_def.element_type_hash not in prim_types:
                #     align = 4
                buffer_pos = offset
            else:
                opos = None
                offset = buffer_pos
                length = type_def.element_length
                align = None

            if type_def.element_type_hash == typedef_u8:
                # v, buffer_pos = ff_read_u8s(buffer, n_buffer, buffer_pos, length)
                v, buffer_pos = ff_read(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_s8:
                # v, buffer_pos = ff_read_s8s(buffer, n_buffer, buffer_pos, length)
                v, buffer_pos = ff_read(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_u16:
                v, buffer_pos = ff_read_u16s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_s16:
                v, buffer_pos = ff_read_s16s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_u32:
                v, buffer_pos = ff_read_u32s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_s32:
                v, buffer_pos = ff_read_s32s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_u64:
                v, buffer_pos = ff_read_u64s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_s64:
                v, buffer_pos = ff_read_s64s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_f32:
                v, buffer_pos = ff_read_f32s(buffer, n_buffer, buffer_pos, length)
            elif type_def.element_type_hash == typedef_f64:
                v, buffer_pos = ff_read_f64s(buffer, n_buffer, buffer_pos, length)
            else:
                v = [None] * length
                for i in range(length):
                    p0 = buffer_pos
                    if align is not None:
                        nudge = (align - p0 % align) % align
                        buffer_pos = p0 + nudge  # v0[0] offset ele 0, v0[1] stride?

                    v[i], buffer_pos = read_instance(
                        buffer, n_buffer, buffer_pos,
                        type_def.element_type_hash, map_typedef, map_string_hash, abs_offset,
                        found_strings=found_strings)

                    p1 = buffer_pos
                    # print(p0, p1, p1-p0)

            if opos is not None:
                buffer_pos = opos

            v = AdfValue(v, type_id, dpos + abs_offset, offset + abs_offset)
        elif type_def.metatype == 7:  # BitField
            if type_def.size == 1:
                v, buffer_pos = ff_read_u8(buffer, n_buffer, buffer_pos)
            elif type_def.size == 2:
                v, buffer_pos = ff_read_u16(buffer, n_buffer, buffer_pos)
            elif type_def.size == 4:
                v, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
            elif type_def.size == 8:
                v, buffer_pos = ff_read_u64(buffer, n_buffer, buffer_pos)
            else:
                raise Exception('Unknown bitfield size')

            if bit_offset is None:
                bit_offset = 0
                print('Missing bit offset')
                # raise Exception('Missing bit offset')
            v = (v >> bit_offset) & 1

            v = AdfValue(v, type_id, dpos + abs_offset, bit_offset=bit_offset)
        elif type_def.metatype == 8:  # Enumeration
            if type_def.size != 4:
                raise Exception('Unknown enum size')
            v, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
            if v < len(type_def.members):
                vs = type_def.members[v].name
            else:
                vs = None

            v = AdfValue(v, type_id, dpos + abs_offset, enum_string=vs)
        elif type_def.metatype == 9:  # String Hash
            if type_def.size == 4:
                v, buffer_pos = ff_read_u32(buffer, n_buffer, buffer_pos)
                if v in map_string_hash:
                    vs = map_string_hash[v].value
                else:
                    vs = None
            elif type_def.size == 6:
                v0, buffer_pos = ff_read_u16(buffer, n_buffer, buffer_pos)
                v1, buffer_pos = ff_read_u16(buffer, n_buffer, buffer_pos)
                v2, buffer_pos = ff_read_u16(buffer, n_buffer, buffer_pos)
                v = v0 << 32 | v1 << 16 | v2
                if v in map_string_hash:
                    vs = map_string_hash[v].value
                else:
                    vs = None
            elif type_def.size == 8:
                v, buffer_pos = ff_read_u64(buffer, n_buffer, buffer_pos)
                if v in map_string_hash:
                    vs = map_string_hash[v].value
                else:
                    vs = None
            else:
                v, buffer_pos = ff_read(buffer, n_buffer, buffer_pos, type_def.size)
                vs = None

            v = AdfValue(v, type_id, dpos + abs_offset, hash_string=vs)
        else:
            raise Exception('Unknown Typedef Type {}'.format(type_def.metatype))

    return v, buffer_pos


class Adf:
    def __init__(self):
        self.version = None
        self.instance_count = None
        self.instance_offset = None
        self.typedef_count = None
        self.typedef_offset = None
        self.stringhash_count = None
        self.stringhash_offset = None
        self.nametable_count = None
        self.nametable_offset = None
        self.total_size = None

        self.unknown = []

        self.comment = b''
        self.table_name = []
        self.table_stringhash = []
        self.map_stringhash = {}

        self.table_typedef: List[TypeDef] = []
        self.map_typedef: Dict[int, TypeDef] = {}
        self.extended_map_typedef = {}

        self.table_instance = []
        self.map_instance = {}

        self.found_strings = set()
        self.table_instance_full_values = []
        self.table_instance_values = []

    def dump_to_string(self, vfs):
        sbuf = ''
        sbuf = sbuf + '--------header\n'
        sbuf = sbuf + '{}: {}\n'.format('version', self.version)
        sbuf = sbuf + '{}: {}\n'.format('instance_count', self.instance_count)
        sbuf = sbuf + '{}: {}\n'.format('instance_offset', self.instance_offset)
        sbuf = sbuf + '{}: {}\n'.format('typedef_count', self.typedef_count)
        sbuf = sbuf + '{}: {}\n'.format('typedef_offset', self.typedef_offset)
        sbuf = sbuf + '{}: {}\n'.format('stringhash_count', self.stringhash_count)
        sbuf = sbuf + '{}: {}\n'.format('stringhash_offset', self.stringhash_offset)
        sbuf = sbuf + '{}: {}\n'.format('nametable_count', self.nametable_count)
        sbuf = sbuf + '{}: {}\n'.format('nametable_offset', self.nametable_offset)
        sbuf = sbuf + '{}: {}\n'.format('total_size', self.total_size)
        for i in range(len(self.unknown)):
            sbuf = sbuf + 'Unknown[{0}]: {1} 0x{1:08x}\n'.format(i, self.unknown[i])

        sbuf = sbuf + '\n--------comment\n'
        sbuf = sbuf + self.comment.decode('utf-8')

        sbuf = sbuf + '\n\n--------name_table\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        for i in range(len(self.table_name)):
            sbuf = sbuf + 'name_table\t{}\t{}\n'.format(i, self.table_name[i][1].decode('utf-8'))

        sbuf = sbuf + '\n--------string_hash\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        v: StringHash
        for k, v in self.map_stringhash.items():
            sbuf = sbuf + 'string_hash\t{:016x}\t{}\n'.format(k, v.value)

        sbuf = sbuf + '\n--------typedefs\n'
        # sbuf = sbuf + '  NOT CURRENTLY SHOWN\n'
        vt: TypeDef
        for k, vt in self.map_typedef.items():
            sbuf = sbuf + 'typedefs\t{:08x}\t{} @ {} (0x{:08x})\n'.format(
                k, vt.name.decode('utf-8'), vt.META_position, vt.META_position)
            sbuf = sbuf + dump_type(k, self.extended_map_typedef, 2)

        sbuf = sbuf + '\n--------instances\n'
        for info, v, fv in zip(self.table_instance, self.table_instance_values, self.table_instance_full_values):
            end_str = '{:08x}-???'.format(info.offset)
            if info.size is not None:
                end_str = '{:08x}-{:08x}'.format(info.offset, info.offset + info.size)

            sbuf = sbuf + 'instances\t{:08x}\t{:08x}\t{}\t{}\t{}\t{}\n'.format(
                info.name_hash,
                info.type_hash,
                info.name.decode('utf-8'),
                info.offset, info.size,
                end_str)

            # sbuf = sbuf + pformat(v, width=1024) + '\n'
            sbuf = sbuf + adf_format(fv, vfs, self.extended_map_typedef) + '\n'

        return sbuf

    def deserialize(self, fp, map_typedef=None, process_instances=True):
        if map_typedef is None:
            map_typedef = {}

        header = fp.read(0x40)

        fh = ArchiveFile(io.BytesIO(header))

        if len(header) < 0x40:
            raise EDecaErrorParse('File Too Short')

        magic = fh.read_strl(4)

        if magic != b' FDA':
            raise EDecaErrorParse('Magic does not match')

        self.version = fh.read_u32()

        self.instance_count = fh.read_u32()
        self.instance_offset = fh.read_u32()

        self.typedef_count = fh.read_u32()
        self.typedef_offset = fh.read_u32()

        self.stringhash_count = fh.read_u32()
        self.stringhash_offset = fh.read_u32()

        self.nametable_count = fh.read_u32()
        self.nametable_offset = fh.read_u32()

        self.total_size = fh.read_u32()

        self.unknown = fh.read_u32(5)

        self.comment = fp.read_strz()

        # name table
        self.table_name = [[0, b''] for i in range(self.nametable_count)]
        fp.seek(self.nametable_offset)
        for i in range(self.nametable_count):
            self.table_name[i][0] = fp.read_u8()
        for i in range(self.nametable_count):
            self.table_name[i][1] = fp.read(self.table_name[i][0] + 1)[0:-1]

        # string hash
        self.table_stringhash = [StringHash() for i in range(self.stringhash_count)]
        self.map_stringhash = {}
        fp.seek(self.stringhash_offset)
        for i in range(self.stringhash_count):
            self.table_stringhash[i].deserialize(fp, self.table_name)
            self.map_stringhash[self.table_stringhash[i].value_hash] = self.table_stringhash[i]

        # typedef
        self.table_typedef = [TypeDef() for i in range(self.typedef_count)]

        self.extended_map_typedef = {}
        for k, v in map_typedef.items():
            self.extended_map_typedef[k] = v

        self.map_typedef = {}
        fp.seek(self.typedef_offset)
        for i in range(self.typedef_count):
            self.table_typedef[i].deserialize(fp, self.table_name)
            self.map_typedef[self.table_typedef[i].type_hash] = self.table_typedef[i]
            self.extended_map_typedef[self.table_typedef[i].type_hash] = self.table_typedef[i]

        # print(typedef_map)

        # instance
        self.table_instance = [InstanceEntry() for i in range(self.instance_count)]
        self.map_instance = {}
        fp.seek(self.instance_offset)
        for i in range(self.instance_count):
            self.table_instance[i].deserialize(fp, self.table_name)
            self.map_instance[self.table_instance[i].name_hash] = self.table_instance[i]

        self.found_strings = set()
        self.table_instance_values = [None] * len(self.table_instance)
        self.table_instance_full_values = [None] * len(self.table_instance)
        if process_instances:
            for i in range(len(self.table_instance)):
                ins = self.table_instance[i]
                fp.seek(ins.offset)
                buffer = fp.read(ins.size)
                n_buffer = len(buffer)
                buffer_pos = 0
                v, buffer_pos = read_instance(
                    buffer, n_buffer, buffer_pos,
                    ins.type_hash, self.extended_map_typedef, self.map_stringhash, ins.offset,
                    found_strings=self.found_strings)
                self.table_instance_full_values[i] = v
                self.table_instance_values[i] = adf_value_extract(v)
                # except EDecaMissingAdfType as ae:
                #     print('Missing HASHID {:08x}'.format(ae.hashid))
                # except Exception as exp:
                #     print(exp)


class AdfDatabase:
    def __init__(self, vfs=None):
        self.type_map_def = {}
        self.type_missing = set()
        self._type_map_updated = False

        if vfs is not None:
            self.load_from_database(vfs)

    def has_type_map_changed(self):
        return self._type_map_updated

    def load_from_database(self, vfs: VfsDatabase):
        self.type_map_def, self.type_missing = vfs.adf_type_map_load()

    def save_to_database(self, vfs: VfsDatabase):
        vfs.adf_type_map_save(self.type_map_def, self.type_missing)

    def typedefs_add(self, map_typedefs):
        for k, v in map_typedefs.items():
            if k not in self.type_map_def:
                self.type_map_def[k] = v
                self._type_map_updated = True

    def process_adf_in_exe(self, exepath, node_uid):
        self.type_map_def = {}

        adf_sub_files = []

        exe_stat = os.stat(exepath)

        with open(exepath, 'rb') as f:
            exe = f.read(exe_stat.st_size)

        poss = 0
        while True:
            poss = exe.find(b' FDA\x04\x00\x00\x00', poss + 1)
            if poss < 0:
                break

            exe_short = exe[poss:]
            with ArchiveFile(BytesIO(exe_short)) as f:
                try:
                    adf = Adf()
                    adf.deserialize(f, map_typedef=self.type_map_def)

                except EDecaMissingAdfType as ae:
                    self.type_missing.add((ae.type_id, node_uid))
                    self._type_map_updated = True

            adf_sub_files.append((poss, adf.total_size))

            self.typedefs_add(adf.map_typedef)
            # TODO also add field strings to adf_db/vfs, combine adf_db and vfs into GAME DATABASE?

        return adf_sub_files

    def _load_adf(self, buffer):
        with ArchiveFile(io.BytesIO(buffer)) as fp:
            obj = Adf()
            try:
                # import time
                # t0 = time.time()
                obj.deserialize(fp, self.type_map_def)
                # t1 = time.time()
                # print(f'Time ADF = {t1 - t0}')

                # get typedefs from regular load, to handle the case where types are in ADF, and ADFB but not EXE
                self.typedefs_add(obj.map_typedef)
                return obj
            except EDecaErrorParse:
                return None

    def _load_adf_bare(self, buffer, adf_type, offset, size):
        if adf_type not in self.type_map_def:
            raise EDecaMissingAdfType(adf_type)

        try:
            obj = Adf()

            # instance
            obj.table_instance = [InstanceEntry()]
            obj.map_instance = {}
            obj.instance_count = 1
            obj.instance_offset = None

            obj.extended_map_typedef = self.type_map_def

            obj.table_instance[0].name = b'instance'
            obj.table_instance[0].name_hash = hash32_func(obj.table_instance[0].name)
            obj.table_instance[0].type_hash = adf_type
            obj.table_instance[0].offset = offset
            obj.table_instance[0].size = size

            obj.map_instance[obj.table_instance[0].name_hash] = obj.table_instance[0]

            obj.found_strings = set()
            obj.table_instance_values = [None] * len(obj.table_instance)
            obj.table_instance_full_values = [None] * len(obj.table_instance)
            for i in range(len(obj.table_instance)):
                ins = obj.table_instance[i]
                n_buffer = len(buffer)
                buffer_pos = ins.offset
                v, buffer_pos = read_instance(
                    buffer, n_buffer, buffer_pos,
                    ins.type_hash, obj.extended_map_typedef, obj.map_stringhash, 0, found_strings=obj.found_strings)
                obj.table_instance_full_values[i] = v
                obj.table_instance_values[i] = adf_value_extract(v)

            return obj
        except EDecaErrorParse:
            return None

    def read_node(self, vfs: VfsDatabase, node: VfsNode):
        with vfs.file_obj_from(node) as f:
            buffer = f.read()

        try:
            if node.file_type == FTYPE_ADF_BARE:
                adf = self._load_adf_bare(buffer, node.file_sub_type, node.offset, node.size_u)
            elif node.file_type == FTYPE_ADF0:
                if node.file_sub_type is None:
                    adf_type = struct.unpack('I', buffer[4:8])[0]
                else:
                    adf_type = node.file_sub_type
                skip = 8  # skip magic and type id
                adf = self._load_adf_bare(buffer[skip:], adf_type, 0, node.size_u - skip)
            elif node.file_type == FTYPE_ADF5:
                skip = 5
                adf = self._load_adf(buffer[skip:])
            else:
                adf = self._load_adf(buffer)
        except EDecaMissingAdfType as ae:
            self.type_missing.add((ae.type_id, node.uid))
            self._type_map_updated = True
            raise

        return adf
