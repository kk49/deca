import struct


def dump_line(line, width, format='hex'):
    if format is 'hex' or len(line) != width:
        line = ''.join(['{:02x}'.format(v) for v in bytearray(line)])
    elif format is 'char' :
        line = ['{}'.format(chr(v)) for v in bytearray(line)]
    else:
        line = struct.unpack(format, line)
    return '{}'.format(line)


def dump_block(blk, width, format='hex'):
    for i in range((len(blk) + width - 1) // width):
        line = blk[(i*width):((i+1)*width)]
        line = dump_line(line, width, format)
        print(line)

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


