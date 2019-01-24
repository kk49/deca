from deca.file import ArchiveFile
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# fn = './test/gz/__TEST__/locations/world/ostervik_neighborhood_04_housing.obc.B00C511A'
fn = './test/gz/__TEST__/locations/world/archipelago_iboholmen_yttervik_house.obc.16F90A59'

rs = []
with ArchiveFile(open(fn, 'rb'), debug=True) as f:
    ver = f.read_u32()
    count = f.read_u32()
    for i in range(count):
        r = f.read_f32(20)
        rs.append(r)

d = np.array(rs)

np.savetxt('./test/gz/test.tsv', d, delimiter='\t')
# fig = plt.figure()
# ax = Axes3D(fig)
# ax.scatter(d[:,4],d[:,5],d[:,6])
# plt.show()