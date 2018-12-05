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



