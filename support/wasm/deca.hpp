#pragma once
#include <cstdint>
#include <string>
#include <exception>

typedef char c8;

typedef int8_t s8;
typedef uint8_t u8;
typedef int16_t s16;
typedef uint16_t u16;
typedef int32_t s32;
typedef uint32_t u32;
typedef int64_t s64;
typedef uint64_t u64;

typedef float f32;
typedef double f64;

class DecaException
: public std::exception
{
public:
    DecaException(std::string const& s = std::string())
    : std::exception()
    , msg_(s)
    {
    }

    std::string msg_;
};

struct StringRef
{
    StringRef()
    : ptr_(nullptr)
    , sz_(0)
    {
    }

    StringRef(c8 const* ptr, size_t sz)
    : ptr_(ptr)
    , sz_(sz)
    {
    }

    c8 const * ptr_;
    size_t sz_;
};

template<typename T_>
class ArrayRef
{
public:
    ArrayRef()
    : ptr_(nullptr)
    , cnt_(0)
    {
    }

    ArrayRef(T_ const* ptr, size_t cnt)
    : ptr_(ptr)
    , cnt_(cnt)
    {
    }

    T_ const * ptr_;
    size_t cnt_;
};

std::string to_string(StringRef const & ref)
{
    return std::string(ref.ptr_, ref.ptr_ + ref.sz_);
}



class DecaBufferFile
{
public:
    DecaBufferFile(c8 const* buffer_beg, c8 const* buffer_end)
    : beg_(buffer_beg)
    , end_(buffer_end)
    , ptr_(buffer_beg)
    {
    }

    c8 const * beg_;
    c8 const * end_;
    c8 const * ptr_;

    size_t size() const { return end_ - beg_; }

    void pos_reset()
    {
        ptr_ = beg_;
    }

    size_t pos_peek() const
    {
        return ptr_ - beg_;
    }

    void pos_seek(size_t offset)
    {
        ptr_ = beg_ + offset;
    }

    template<typename T_>
    T_ read()
    {
        if(ptr_ + sizeof(T_) > end_)
            throw DecaException("EOL REACHED");

        T_ const value = *((T_ *)ptr_);
        ptr_ += sizeof(T_);
        return value;
    }



    template<typename T_>
    ArrayRef<T_> reads(size_t count)
    {
        if(ptr_ + sizeof(T_) * count > end_)
            throw DecaException("EOL REACHED");

        T_ * const ptr = ((T_ *)ptr_);
        ptr_ += sizeof(T_) * count;

        return ArrayRef<T_>(ptr, count);
    }

    StringRef read_strz()
    {
        c8 const* start = ptr_;

        for(;(ptr_ < end_) && (*ptr_ != 0); ++ptr_);

        StringRef result(start, ptr_ - start);

        if(ptr_ < end_)
            ++ptr_;  //consume 0 at end of string

        return result;
    }

    StringRef read_strn(u32 size, bool const trim_last = false)
    {
        c8 const * start = ptr_;
        ptr_ += size;
        if(trim_last) --size;

        return StringRef(start, size);
    }

    template<typename OFFSET_, typename LENGTH_>
    StringRef read_strol()
    {
        //TODO Add buffer end check
        u32 const offset = read<OFFSET_>();
        u32 const length = read<LENGTH_>();  // TODO Size may be needed for byte codes?
        return StringRef(beg_ + offset, length);
    }

};

class StorePos
{
public:
    StorePos(DecaBufferFile & f)
    : f_(f)
    , offset_(f.pos_peek())
    {}

    DecaBufferFile & f_;
    size_t offset_;

    ~StorePos()
    {
        f_.pos_seek(offset_);
    }
};


