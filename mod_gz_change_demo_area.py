from deca.file import ArchiveFile
import numpy as np
import os
from deca.hash_jenkins import hash_little

# fn = '/home/krys/prj/deca/work/gz/extracted/global/global.blo'
#
# sz = os.stat(fn).st_size
#
# with open(fn, 'rb') as f:
#     buf = f.read(sz)
#     print('{}'.format(buf[0:16]))
#     h = hash_little(buf, 0xdeadbeef)
#     print('{} {:0x}'.format(h, h))
#     h = hash_little(buf, 0x0)
#     print('{} {:0x}'.format(h, h))
#
#
# exit(0)

fn = '/home/krys/prj/work/gzb/mod/global/global.blo'
with ArchiveFile(open(fn, 'r+b')) as f:
    f.seek(0x00021020)
    mat4 = list(f.read_f32(16))
    mat4 = np.transpose(np.array(mat4).reshape((4, 4)))

    f.seek(0x00026a58)
    sz = f.read_u32()
    vals = list(f.read_f32(sz))
    print(vals)

    vals = np.asarray(np.array(vals).reshape(sz//4, 4))
    for i in range(sz//4):
        vals[i, 0] += mat4[0, 3]
        vals[i, 1] += mat4[1, 3]
        vals[i, 2] += mat4[2, 3]

    vals2 = np.zeros((4, 4), dtype=np.float32)
    vals2[:, 0] = vals[0, 0]
    vals2[:, 1] = vals[0, 1]
    vals2[:, 2] = vals[0, 2]
    vals2[:, 3] = 0.0

    xo = 4100.0
    zo = 2200.0
    v = (2**13) - 1.0
    y = 4096.0

    vals2[:, 0] = [-v, v, v, -v]
    vals2[:, 1] = [y-1, y-1, y+1, y+1]
    vals2[:, 2] = [-v, -v, v, v]

    vals2[:, 0] += xo
    vals2[:, 2] += zo

    vals = vals2

    for i in range(vals.shape[0]):
        vals[i, 0] -= mat4[0, 3]
        vals[i, 1] -= mat4[1, 3]
        vals[i, 2] -= mat4[2, 3]

    vals = vals[::-1, :]

    vals = list(np.asarray(np.array(vals).reshape(-1, )))

    # vals = [
    #     9760.970703125, -83.1153564453125, 5258.8818359375, 0.0,
    #     9910.8505859375, -83.3109130859375, 5120.349609375, 0.0,
    #     11903.990234375, -71.6529541015625, 3738.245849609375, 0.0,
    #     11880.802734375, -71.6527099609375, 3150.407958984375, 0.0,
    # ]

    f.seek(0x00026a58)
    nsz = min(sz, len(vals))
    f.write_u32(nsz)
    f.write_f32(vals[:nsz])

    print(vals)


print(mat4)
