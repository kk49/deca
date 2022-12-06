import sys
import mmh3
import numpy as np
from numba import njit

# Need to constrain U32 to only 32 bits using the & 0xffffffff
# since Python has no native notion of integers limited to 32 bit
# http://docs.python.org/library/stdtypes.html#numeric-types-int-float-long-complex

'''
KK FOUND HERE: https://stackoverflow.com/questions/3279615/python-implementation-of-jenkins-hash
'''

'''
Original copyright notice:
    By Bob Jenkins, 1996.  bob_jenkins@burtleburtle.net.  You may use this
    code any way you wish, private, educational, or commercial.  Its free.
'''


class CostModel(object):
    def __init__(self, max_inlines):
        self._count = 0
        self._max_inlines = max_inlines

    def __call__(self, *args, **kwargs):
        ret = self._count < self._max_inlines
        self._count += 1
        return ret


cost_model_params = 0


@njit(inline=CostModel(cost_model_params))
def rot(x, k):
    return (x << k) | (x >> (32 - k))


@njit(inline=CostModel(cost_model_params))
def mix(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= rot(c,4);  a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= rot(a,6);  b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= rot(b,8);  c &= 0xffffffff; b += a; b &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= rot(c,16); a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= rot(a,19); b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= rot(b,4);  c &= 0xffffffff; b += a; b &= 0xffffffff
    return a, b, c


@njit(inline=CostModel(cost_model_params))
def final(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,14); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= rot(c,11); a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= rot(a,25); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,16); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= rot(c,4);  a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= rot(a,14); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,24); c &= 0xffffffff
    return a, b, c


@njit(inline=CostModel(cost_model_params))
def hashlittle2(data, initval=0, initval2=0):
    length = lenpos = len(data)

    a = b = c = (0xdeadbeef + length + initval)

    c += initval2
    c &= 0xffffffff

    p = 0  # string offset
    while lenpos > 12:
        a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24)); a &= 0xffffffff
        b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); b &= 0xffffffff
        c += ((data[p+8]) + ((data[p+9])<<8) + ((data[p+10])<<16) + ((data[p+11])<<24)); c &= 0xffffffff
        a, b, c = mix(a, b, c)
        p += 12
        lenpos -= 12

    if lenpos == 12: c += ((data[p+8]) + ((data[p+9])<<8) + ((data[p+10])<<16) + ((data[p+11])<<24)); b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 11: c += ((data[p+8]) + ((data[p+9])<<8) + ((data[p+10])<<16)); b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 10: c += ((data[p+8]) + ((data[p+9])<<8)); b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 9:  c += ((data[p+8])); b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 8:  b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16) + ((data[p+7])<<24)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 7:  b += ((data[p+4]) + ((data[p+5])<<8) + ((data[p+6])<<16)); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 6:  b += (((data[p+5])<<8) + (data[p+4])); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24))
    if lenpos == 5:  b += ((data[p+4])); a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24));
    if lenpos == 4:  a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16) + ((data[p+3])<<24))
    if lenpos == 3:  a += ((data[p+0]) + ((data[p+1])<<8) + ((data[p+2])<<16))
    if lenpos == 2:  a += ((data[p+0]) + ((data[p+1])<<8))
    if lenpos == 1:  a += (data[p+0])
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    if lenpos == 0: return c, b

    a, b, c = final(a, b, c)

    return c, b


@njit(inline=CostModel(cost_model_params))
def hash32_func_bytes(data, init_val=0):
    c, b = hashlittle2(data, init_val, 0)
    return c


def hash32_func(data, init_val=0):
    if isinstance(data, str):
        data = data.encode('ascii')
    return hash32_func_bytes(data, init_val)


def hash48_func(data):
    if isinstance(data, str):
        data = data.encode('ascii')

    v = mmh3.hash128(key=data, x64arch=True)
    return (v >> 16) & 0x0000FFFFFFFFFFFF


def hash64_func(data):
    if isinstance(data, str):
        data = data.encode('ascii')

    v = mmh3.hash128(key=data, x64arch=True)
    return int(np.int64(np.uint64(v & 0xFFFFFFFFFFFFFFFF)))


def hash_all_func(data):
    if isinstance(data, str):
        data = data.encode('ascii')

    c, b = hashlittle2(data, 0, 0)

    v = mmh3.hash128(key=data, x64arch=True)

    return c, (v >> 16) & 0x0000FFFFFFFFFFFF, int(np.int64(np.uint64(v & 0xFFFFFFFFFFFFFFFF)))


def main():
    data = sys.argv[1]

    hv = hash32_func(data)
    print('hash4 "{}" = {:12} , 0x{:08x}'.format(data, hv, hv))

    hv = hash48_func(data)
    print('hash6 "{}" = {:24} , 0x{:012x}'.format(data, hv, hv))

    hv = hash64_func(data)
    print('hash8 "{}" = {:24}, {:24}, 0x{:016x}'.format(data,  hv, np.uint64(hv), np.uint64(hv)))


if __name__ == "__main__":
    main()


'''
JENKINS HASH code from 
https://github.com/gibbed/Gibbed.JustCause3/blob/master/projects/Gibbed.JustCause3.FileFormats/StringHelpers.cs
'''

'''
        private static uint HashJenkins(byte[] data, int index, int length, uint seed)
        {
            // ReSharper disable JoinDeclarationAndInitializer
            uint a, b, c;
            // ReSharper restore JoinDeclarationAndInitializer

            a = b = c = 0xDEADBEEF + (uint)length + seed;

            int i = index;
            while (i + 12 < length)
            {
                // ReSharper disable RedundantCast
                a += (uint)data[i++] |
                     ((uint)data[i++] << 8) |
                     ((uint)data[i++] << 16) |
                     ((uint)data[i++] << 24);
                b += (uint)data[i++] |
                     ((uint)data[i++] << 8) |
                     ((uint)data[i++] << 16) |
                     ((uint)data[i++] << 24);
                c += (uint)data[i++] |
                     ((uint)data[i++] << 8) |
                     ((uint)data[i++] << 16) |
                     ((uint)data[i++] << 24);
                // ReSharper restore RedundantCast
                a -= c;
                a ^= (c << 4) | (c >> (32 - 4));
                c += b;
                b -= a;
                b ^= (a << 6) | (a >> (32 - 6));
                a += c;
                c -= b;
                c ^= (b << 8) | (b >> (32 - 8));
                b += a;
                a -= c;
                a ^= (c << 16) | (c >> (32 - 16));
                c += b;
                b -= a;
                b ^= (a << 19) | (a >> (32 - 19));
                a += c;
                c -= b;
                c ^= (b << 4) | (b >> (32 - 4));
                b += a;
            }

            if (i < length)
            {
                a += data[i++];
            }

            if (i < length)
            {
                a += (uint)data[i++] << 8;
            }

            if (i < length)
            {
                a += (uint)data[i++] << 16;
            }

            if (i < length)
            {
                a += (uint)data[i++] << 24;
            }

            if (i < length)
            {
                // ReSharper disable RedundantCast
                b += (uint)data[i++];
                // ReSharper restore RedundantCast
            }

            if (i < length)
            {
                b += (uint)data[i++] << 8;
            }

            if (i < length)
            {
                b += (uint)data[i++] << 16;
            }

            if (i < length)
            {
                b += (uint)data[i++] << 24;
            }

            if (i < length)
            {
                // ReSharper disable RedundantCast
                c += (uint)data[i++];
                // ReSharper restore RedundantCast
            }

            if (i < length)
            {
                c += (uint)data[i++] << 8;
            }

            if (i < length)
            {
                c += (uint)data[i++] << 16;
            }

            if (i < length)
            {
                c += (uint)data[i /*++*/] << 24;
            }

            c ^= b;
            c -= (b << 14) | (b >> (32 - 14));
            a ^= c;
            a -= (c << 11) | (c >> (32 - 11));
            b ^= a;
            b -= (a << 25) | (a >> (32 - 25));
            c ^= b;
            c -= (b << 16) | (b >> (32 - 16));
            a ^= c;
            a -= (c << 4) | (c >> (32 - 4));
            b ^= a;
            b -= (a << 14) | (a >> (32 - 14));
            c ^= b;
            c -= (b << 24) | (b >> (32 - 24));

            return c;
        }
        #endregion

        public static uint HashJenkins(this string input)
        {
            byte[] data = Encoding.ASCII.GetBytes(input);
            return HashJenkins(data, 0, data.Length, 0);
        }

'''
