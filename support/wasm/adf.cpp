#include "deca.h"
#include <emscripten.h>
#include <vector>
#include <map>
#include <sstream>
#include <iostream>

// for PYTHON
// emcc adf.cpp -o deca_adf.wasm -O3 -v --js-library deca_adf_lib.js -s INITIAL_MEMORY=256MB -s MAXIMUM_MEMORY=1GB -s EXPORT_ALL=0 -s EXPORTED_FUNCTIONS="[]"

// for JavaScript
// emcc adf.cpp -o deca_adf.js -O3 -v --js-library deca_adf_lib.js -s INITIAL_MEMORY=256MB -s MAXIMUM_MEMORY=1GB -s EXPORT_ALL=0 -s EXPORTED_FUNCTIONS="[]"

extern "C"
{
    // external functions used to build adf structure in parent environment
    // file_begin ?
    // file_end ?
    // obj_begin ?

    extern void db_print(c8 const * ptr, u32 sz);
    extern void db_warn(c8 const * ptr, u32 sz);
    extern void db_error(c8 const * ptr, u32 sz);

    extern void dict_push();           // ... -> ... dict
    extern void dict_field_set();      // ... dict str value -> dict

    extern void list_push();
    extern void list_append();

    extern void hash_register(u64 const hash, char const *ptr, u32 sz);
    extern void hash32_push(u32 value);
    extern void hash48_push(u64 value);
    extern void hash64_push(u64 value);

    extern void bool_push(bool value);  // ... -> ... value
    extern void s8_push(s8 value);      // ... -> ... value
    extern void u8_push(u8 value);      // ... -> ... value
    extern void s16_push(s16 value);   // ... -> ... value
    extern void u16_push(u16 value);   // ... -> ... value
    extern void s32_push(s32 value);   // ... -> ... value
    extern void u32_push(u32 value);   // ... -> ... value
    extern void s64_push(s64 value);   // ... -> ... value
    extern void u64_push(u64 value);   // ... -> ... value
    extern void f32_push(f32 value);   // ... -> ... value
    extern void f64_push(f64 value);   // ... -> ... value

    extern void str_push(c8 const *ptr, u32 cnt);   // ... -> ... array[]

    extern void enum_push(u32 value, c8 const *ptr, u32 cnt);

    extern void s8s_push(s8 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void u8s_push(u8 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void s16s_push(s16 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void u16s_push(u16 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void s32s_push(s32 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void u32s_push(u32 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void s64s_push(s64 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void u64s_push(u64 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void f32s_push(f32 const * ptr, u32 cnt);   // ... -> ... array[]
    extern void f64s_push(f64 const * ptr, u32 cnt);   // ... -> ... array[]
}

void array_push(ArrayRef<s8> const & ref) { s8s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<u8> const & ref) { u8s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<s16> const & ref) { s16s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<u16> const & ref) { u16s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<s32> const & ref) { s32s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<u32> const & ref) { u32s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<s64> const & ref) { s64s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<u64> const & ref) { u64s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<f32> const & ref) { f32s_push(ref.ptr_, ref.cnt_); }
void array_push(ArrayRef<f64> const & ref) { f64s_push(ref.ptr_, ref.cnt_); }



void db_print(c8 const* str)
{
    db_print(str, strlen(str));
}

void db_print(StringRef const & str)
{
    db_print(str.ptr_, str.sz_);
}

void db_print(std::string const& str)
{
    db_print(str.data(), str.size());
}

void db_print(std::stringstream const& ss)
{
    db_print(ss.str());
}

void db_warn(std::string const& str)
{
    db_warn(str.data(), str.size());
}

void db_warn(std::stringstream const& ss)
{
    db_warn(ss.str());
}

void db_exception(std::string const& str)
{
    db_error(str.data(), str.size());
    throw DecaException(str);
}

void db_exception(std::stringstream const& ss)
{
    db_exception(ss.str());
}


void hash_register(u64 hash, StringRef const & ref)
{
    hash_register(hash, ref.ptr_, ref.sz_);
}

void str_push(c8 const * ptr)
{
    str_push(ptr, strlen(ptr));
}

void str_push(std::string const & str)
{
    str_push(str.data(), str.size());
}

void str_push(StringRef const & str)
{
    str_push(str.ptr_, str.sz_);
}

void enum_push(u64 value, StringRef const & str)
{
    enum_push(value, str.ptr_, str.sz_);
}

// input buffer management
std::vector<c8> buffer_in;


// adf functions
u32 const typedef_s8 = 0x580D0A62;
u32 const typedef_u8 = 0x0ca2821d;
u32 const typedef_s16 = 0xD13FCF93;
u32 const typedef_u16 = 0x86d152bd;
u32 const typedef_s32 = 0x192fe633;
u32 const typedef_u32 = 0x075e4e4f;
u32 const typedef_s64 = 0xAF41354F;
u32 const typedef_u64 = 0xA139E01F;
u32 const typedef_f32 = 0x7515a207;
u32 const typedef_f64 = 0xC609F663;
u32 const typedef_str = 0x8955583e;

enum MetaType : u32
{ Primitive = 0
, Structure = 1
, Pointer = 2
, Array = 3
, InlineArray = 4
, String = 5
, MetaType6 = 6
, BitField = 7
, Enumeration = 8
, StringHash = 9
};

class MemberDef
{
public:
    MemberDef()
    : name_()
    , type_hash_()
    , size_()
    , offset_()
    , bit_offset_()
    , default_type_()
    , default_value_()
    {}

    StringRef name_;
    u32 type_hash_;
    u32 size_;
    u32 offset_;
    u32 bit_offset_;
    u32 default_type_;
    u64 default_value_;

    void deserialize(DecaBufferFile & f, std::vector<StringRef> const & nt)
    {
        name_ = nt.at(f.read<u64>());
        type_hash_ = f.read<u32>();
        size_ = f.read<u32>();
        u32 const offset = f.read<u32>();
        bit_offset_ = (offset >> 24) & 0xff;
        offset_ = offset & 0x00ffffff;
        default_type_ = f.read<u32>();
        default_value_ = f.read<u64>();
    }

};


class EnumDef
{
public:
    EnumDef()
    : name_()
    , value_()
    {}

    StringRef name_;
    u32 value_;

    void deserialize(DecaBufferFile & f, std::vector<StringRef> const & nt)
    {
        name_ = nt.at(f.read<u64>());
        value_ = f.read<u32>();
    }
};


class TypeDef
{
public:
    TypeDef()
    : meta_type_()
    , size_()
    , alignment_()
    , type_hash_()
    , name_()
    , flags_()
    , element_type_hash_()
    , element_length_()
    , members_()
    , enums_()
    {}

    MetaType meta_type_;
    u32 size_;
    u32 alignment_;
    u32 type_hash_;
    StringRef name_;
    u32 flags_;
    u32 element_type_hash_;
    u32 element_length_;
    std::vector<MemberDef> members_;
    std::vector<EnumDef> enums_;

    void deserialize(DecaBufferFile & f, std::vector<StringRef> const & nt)
    {
        size_t const pos = f.pos_peek();
        meta_type_ = static_cast<MetaType>(f.read<u32>());
        size_ = f.read<u32>();
        alignment_ = f.read<u32>();
        type_hash_ = f.read<u32>();
        name_ = nt.at(f.read<u64>());
        flags_ = f.read<u32>();
        element_type_hash_ = f.read<u32>();
        element_length_ = f.read<u32>();

//        db_print(std::stringstream()
//            << "pos = " << pos
//            << ", meta_type_ = " << meta_type_
//            << ", size_ = " << size_
//            << ", alignment_ = " << alignment_
//            << ", type_hash_ = " << type_hash_
//            << ", name_ = " << to_string(name_)
//            << ", flags_ = " << flags_
//            << ", element_type_hash_ = " << element_type_hash_
//            << ", element_length_ = " << element_length_
//        );

        switch(meta_type_)
        {
        case Primitive:
            break;
        case Structure:
            {
                u32 count = f.read<u32>();
                members_.resize(count);
                for(auto && i : members_) i.deserialize(f, nt);
            }
            break;
        case Pointer:
            {
                u32 count = f.read<u32>();
                if(count != 0) db_warn((std::stringstream() << "Pointer: Not Implemented: count == " << count).str());
            }
            break;
        case Array:
            {
                u32 count = f.read<u32>();
                if(count != 0) db_warn((std::stringstream() << "Array: Not Implemented: count == " << count).str());
            }
            break;
        case InlineArray:
            {
                u32 count = f.read<u32>();
                if(count != 0) db_exception((std::stringstream() << "InlineArray: Not Implemented: count == " << count).str());
            }
            break;
        case BitField:
            {
                u32 count = f.read<u32>();
                if(count != 0) db_exception((std::stringstream() << "BitField: Not Implemented: count == " << count).str());
            }
            break;
        case Enumeration:
            {
                u32 count = f.read<u32>();
                enums_.resize(count);
                for(auto && i : enums_) i.deserialize(f, nt);
            }
            break;
        case StringHash:
            {
                u32 count = f.read<u32>();
                if(count != 0) db_exception((std::stringstream() << "StringHash: Not Implemented: count == " << count).str());
            }
            break;
        case String:
        case MetaType6:
        default:
            db_exception((std::stringstream() << "Unknown Typedef Type " << meta_type_).str());
        }
    }

    void read_instance(DecaBufferFile & f, std::map<u32, TypeDef> const & map_typedef)
    {
    }
};

void read_instance(DecaBufferFile & f, std::map<u32, TypeDef> const & map_typedef, u32 type_hash, s32 bit_offset = -1);


void read_instance_array(DecaBufferFile & f, std::map<u32, TypeDef> const & map_typedef, u32 type_hash, u32 length)
{
    switch(type_hash)
    {
        case typedef_s8: array_push(f.reads<s8>(length)); break;
        case typedef_u8: array_push(f.reads<u8>(length)); break;
        case typedef_s16: array_push(f.reads<s16>(length)); break;
        case typedef_u16: array_push(f.reads<u16>(length)); break;
        case typedef_s32: array_push(f.reads<s32>(length)); break;
        case typedef_u32: array_push(f.reads<u32>(length)); break;
        case typedef_s64: array_push(f.reads<s64>(length)); break;
        case typedef_u64: array_push(f.reads<u64>(length)); break;
        case typedef_f32: array_push(f.reads<f32>(length)); break;
        case typedef_f64: array_push(f.reads<f64>(length)); break;
        default:
            {
                list_push();
                for(size_t i = 0; i < length; ++i)
                {
                    read_instance(f, map_typedef, type_hash);
                    list_append();
                }
            }
            break;
    }
}

void read_instance(DecaBufferFile & f, std::map<u32, TypeDef> const & map_typedef, u32 type_hash, s32 bit_offset)
{
    switch(type_hash)
    {
        case typedef_s8: s8_push(f.read<s8>()); break;
        case typedef_u8: u8_push(f.read<u8>()); break;
        case typedef_s16: s16_push(f.read<s16>()); break;
        case typedef_u16: u16_push(f.read<u16>()); break;
        case typedef_s32: s32_push(f.read<s32>()); break;
        case typedef_u32: u32_push(f.read<u32>()); break;
        case typedef_s64: s64_push(f.read<s64>()); break;
        case typedef_u64: u64_push(f.read<u64>()); break;
        case typedef_f32: f32_push(f.read<f32>()); break;
        case typedef_f64: f64_push(f.read<f64>()); break;
        case typedef_str: str_push(f.read_strol<u32,u32>()); break;
        case 0xdefe88ed:
            {
                u32 offset = f.read<u32>();
                u32 v01 = f.read<u32>();
                u32 sub_type_hash = f.read<u32>();
                u32 v03 = f.read<u32>();

                if(offset == 0 || sub_type_hash == 0)
                {
                }
                else
                {
                    StorePos sp(f);
                    f.pos_seek(offset);
                    read_instance(f, map_typedef, sub_type_hash);
                }
            }
            break;
        default:
            {
                auto it = map_typedef.find(type_hash);
                if(it == map_typedef.end())
                {
                    db_exception(std::stringstream() << "ERROR: Unknown type_hash = 0x" << std::hex << type_hash);
                }
                else
                {
                    TypeDef const & type_def = it->second;

                    switch(type_def.meta_type_)
                    {
                    case Primitive:
                        db_exception(std::stringstream() << "ERROR: Encountered Primitive");
                        break;
                    case Structure:
                        {
                            dict_push();
                            size_t p0 = f.pos_peek();
                            for(auto && m : type_def.members_)
                            {
                                str_push(m.name_);

                                f.pos_seek(p0 + m.offset_);
                                read_instance(f, map_typedef, m.type_hash_, m.bit_offset_);

                                dict_field_set();
                            }
                            f.pos_seek(p0 + type_def.size_);
                        }
                        break;
                    case Pointer:
                        {
                            //TODO not sure how this is used yet, but it's used by effects so lower priority
                            u64 const pointer = f.read<u64>();
                            str_push(
                                (std::stringstream() << "NOTE: " << to_string(type_def.name_) << ": "
                                    << std::hex << pointer << " to " << type_def.element_type_hash_).str()
                            );
                        }
                        break;
                    case Array:
                        {
                            u32 const offset = f.read<u32>();
                            u32 const flags = f.read<u32>();
                            u32 const length = f.read<u32>();
                            StorePos sp(f);

                            f.pos_seek(offset);

                            read_instance_array(f, map_typedef, type_def.element_type_hash_, length);
                        }
                        break;
                    case String:
                        db_exception((std::stringstream() << "ERROR: Unhandled meta type String"));
                        break;
                    case MetaType6:
                        db_exception((std::stringstream() << "ERROR: Unhandled meta type MetaType6"));
                        break;
                    case InlineArray:
                        {
                            read_instance_array(f, map_typedef, type_def.element_type_hash_, type_def.element_length_);
                        }
                        break;
                    case BitField:
                        {
                            u64 v = 0;
                            switch(type_def.size_)
                            {
                                case 1: v = f.read<u8>(); break;
                                case 2: v = f.read<u16>(); break;
                                case 4: v = f.read<u32>(); break;
                                case 8: v = f.read<u64>(); break;
                                default: db_exception("Unknown bitfield size"); break;
                            }

                            if(bit_offset < 0)
                            {
                                bit_offset = 0;
                                db_print("Missing bit offset");
                            }

                            v = (v >> bit_offset) & 1;
                            bool_push(v != 0);
                        }
                        break;
                    case Enumeration:
                        {
                            if(type_def.size_ != 4)
                            {
                                db_exception("Unknown Enum Size");
                            }
                            else
                            {
                                u32 v = f.read<u32>();
                                StringRef vs;

                                if(v < type_def.enums_.size())
                                    vs = type_def.enums_[v].name_;

                                enum_push(v, vs);
                            }
                        }
                        break;
                    case StringHash:
                        {
                            switch(type_def.size_)
                            {
                            case 4: hash32_push(f.read<u32>()); break;
                            case 8: hash64_push(f.read<u64>()); break;
                            case 6:
                                {
                                    u64 const v0 = f.read<u16>();
                                    u64 const v1 = f.read<u16>();
                                    u64 const v2 = f.read<u16>();
                                    hash48_push(v0 << 32 | v1 << 16 | v2);
                                }
                                break;
                            default: db_exception(std::stringstream() << "Unknown hash size " << type_def.size_); break;
                            }
                        }
                        break;
                    default:
                        db_exception((std::stringstream() << "ERROR: Unhandled meta type = " << type_def.meta_type_));
                        break;

                    }
                }
            }
            break;

    }

    /*
    else:


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

    */
}


class InstanceEntry
{
public:
    InstanceEntry()
    : name_hash_()
    , type_hash_()
    , offset_()
    , size_()
    , name_()
    {
    }

    u32 name_hash_;
    u32 type_hash_;
    u32 offset_;
    u32 size_;
    StringRef name_;

    void deserialize(DecaBufferFile & f, std::vector<StringRef> const & nt)
    {
        name_hash_ = f.read<u32>();
        type_hash_ = f.read<u32>();
        offset_ = f.read<u32>();
        size_ = f.read<u32>();
        name_ = nt.at(f.read<u64>());
    }

    void read_instance(DecaBufferFile & f, std::map<u32, TypeDef> const & map_typedef)
    {
        f.pos_seek(offset_);
        DecaBufferFile f_instance(f.beg_ + offset_, f.beg_ + offset_ + size_);
        ::read_instance(f_instance, map_typedef, type_hash_);
    }

};




bool read_file(DecaBufferFile & f)
{
    if(f.size() < 0x40)
    {
        db_print("Error: FileTooShort");
        return false; // raise FileTooShort
    }

    u32 const magic = f.read<u32>();

    if (magic != 'ADF ')
    {
        db_print("Error: Magic does not match");
        return false;
    }

    u32 const version = f.read<u32>();

    u32 const instance_count = f.read<u32>();
    u32 const instance_offset = f.read<u32>();

    u32 const typedef_count = f.read<u32>();
    u32 const typedef_offset = f.read<u32>();

    u32 const stringhash_count = f.read<u32>();
    u32 const stringhash_offset = f.read<u32>();

    u32 const nametable_count = f.read<u32>();
    u32 const nametable_offset = f.read<u32>();

    u32 const total_size = f.read<u32>();

    u32 const unknown_000 = f.read<u32>();
    u32 const unknown_001 = f.read<u32>();
    u32 const unknown_002 = f.read<u32>();
    u32 const unknown_003 = f.read<u32>();
    u32 const unknown_004 = f.read<u32>();


    StringRef comment = f.read_strz();  // comment is a zero delimited string

//    db_print("Comment: " + to_string(comment));


    // name table
    f.pos_seek(nametable_offset);

    std::vector<u8> name_table_sz(nametable_count);
    for(size_t i = 0; i < nametable_count; ++i)
    {
        name_table_sz[i] = f.read<u8>();
    }

    std::vector<StringRef> name_table(nametable_count);
    for(size_t i = 0; i < nametable_count; ++i)
    {
        name_table[i] = f.read_strn(name_table_sz[i] + 1, true);
    }


    // string hash
    f.pos_seek(stringhash_offset);

    std::map<u64, StringRef> map_string_hash;
    for(size_t i = 0; i < stringhash_count; ++i)
    {
        StringRef const s{f.read_strz()};
        u64 const h = f.read<u64>();
        map_string_hash[h] = s;
    }


    // typedef
    f.pos_seek(typedef_offset);

    std::map<u32, TypeDef> map_typedef;

    for(size_t i = 0; i < typedef_count; ++i)
    {
        TypeDef td;
        td.deserialize(f, name_table);
        map_typedef[td.type_hash_] = td;
    }

    // instance
    f.pos_seek(instance_offset);

    std::vector<InstanceEntry> table_instance(instance_count);

    for(auto && i : table_instance) i.deserialize(f, name_table);

    for(auto && i : table_instance) i.read_instance(f, map_typedef);

    return true;
}

extern "C" {
    EMSCRIPTEN_KEEPALIVE
    c8 * alloc_bin(u64 sz)
    {
        if(sz > buffer_in.size())
        {
            buffer_in.resize(sz);
        }
        return buffer_in.data();
    }

    EMSCRIPTEN_KEEPALIVE
    bool process_adf(c8 const* buffer, u64 buffer_sz)
    {
        DecaBufferFile f(buffer, buffer + buffer_sz);
        return read_file(f);
    }

}
