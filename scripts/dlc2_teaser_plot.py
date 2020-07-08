import re
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import numpy as np
from deca.db_core import VfsDatabase
from deca.db_processor import vfs_structure_open
from deca.ff_adf import AdfDatabase
from deca.digest import process_translation_adf, process_codex_adf
from deca.ff_adf_amf_gltf import Deca3dMatrix
import deca.ff_rtpc as rtpc
from deca.ff_rtpc import parse_prop_data

from matplotlib._png import read_png
from matplotlib.cbook import get_sample_data

vfs: VfsDatabase = vfs_structure_open('/home/krys/prj/work/gz/project.json')
adf_db = AdfDatabase(vfs)


class RtpcVisitorDlc2Teaser(rtpc.RtpcVisitor):
    def __init__(self):
        super(RtpcVisitorDlc2Teaser, self).__init__()
        self.splines = []

        self.node_stack = []
        self.node_stack_index = -1

        self.rtpc_class_name = None  # PropName.CLASS_NAME
        self.rtpc_class_comment = None  # PropName.CLASS_COMMENT
        self.rtpc_world = None  # rtpc_prop_world
        self.rtpc_spline = None

    def node_start(self, bufn, pos, index, node_info):
        self.node_stack_index += 1
        if len(self.node_stack) <= self.node_stack_index:
            self.node_stack.append([None, None, None])
        self.node_stack[self.node_stack_index][0] = index
        self.node_stack[self.node_stack_index][1] = None
        self.node_stack[self.node_stack_index][2] = None

    def node_end(self, bufn, pos, index, node_info):
        self.node_stack_index -= 1

    def props_start(self, bufn, pos, count):
        self.rtpc_class_name = None  # PropName.CLASS_NAME
        self.rtpc_class_comment = None  # PropName.CLASS_COMMENT
        self.rtpc_world = None  # rtpc_prop_world
        self.rtpc_spline = None

    def props_end(self, bufn, pos, count):
        if self.rtpc_class_name == 'CAnimSpline':
            self.splines.append((self.rtpc_world, self.rtpc_spline))

    def prop_start(self, bufn, pos, index, prop_info):
        prop_pos, prop_name_hash, prop_data_pos, prop_data_raw, prop_type = prop_info
        if rtpc.h_prop_class == prop_name_hash:
            self.rtpc_class_name = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
            self.node_stack[self.node_stack_index][1] = self.rtpc_class_name
        elif rtpc.h_prop_name == prop_name_hash:
            self.rtpc_class_comment = parse_prop_data(bufn, prop_info)[0].decode('utf-8')
        elif rtpc.h_prop_world == prop_name_hash:
            self.rtpc_world = parse_prop_data(bufn, prop_info)[0]
            self.node_stack[self.node_stack_index][2] = self.rtpc_world
        elif rtpc.h_prop_spline == prop_name_hash:
            self.rtpc_spline = parse_prop_data(bufn, prop_info)[0]


print('PROCESSING: blo(s)')
visitor = RtpcVisitorDlc2Teaser()
vnodes = vfs.nodes_where_match(v_path='locations/world/archipelago_dlc02_may_teaser.blo')
vnode = vnodes[0]
with vfs.file_obj_from(vnode) as f:
    buffer = f.read()

visitor.visit(buffer)

splines = []
bb_min = None
bb_max = None
for spline in visitor.splines:
    world = spline[0]
    x0 = world[12]
    y0 = world[13]
    z0 = world[14]
    w0 = 0.0
    offset = np.asarray([x0, y0, z0, w0])

    points = np.asarray(spline[1]).reshape((-1, 4))
    points = points + offset

    print(points)
    splines.append(points)

    mnp = np.min(points, axis=0)
    if bb_min is None:
        bb_min = mnp
    else:
        bb_min = np.minimum(bb_min, mnp)

    mxp = np.max(points, axis=0)
    if bb_max is None:
        bb_max = mxp
    else:
        bb_max = np.maximum(bb_max, mxp)


plt.figure()
ax = plt.axes(projection='3d')
ax.set_aspect('equal')


# #
# # 10 is equal length of x and y axises of your surface
# step_x = 1.0
# step_y = 1.0
#
# x1 = np.arange(-(2**13) + 0.5, (2**13) + 0.5, step_x)
# y1 = np.arange(-(2**13) + 0.5, (2**13) + 0.5, step_y)
#
# x_mask = np.logical_not(np.logical_or(x1 < bb_min[0], x1 > bb_max[0]))
# y_mask = np.logical_not(np.logical_or(y1 < bb_min[2], y1 > bb_max[2]))
#
# x1 = x1[x_mask]
# y1 = y1[y_mask]
#
# x1, y1 = np.meshgrid(x1, y1)
#
#
# arr = read_png('/home/krys/prj/deca/scripts/dlc2_teaser/full.png')
#
# arr = arr[y_mask, :, :][:, x_mask, :]
#
# # stride args allows to determine image quality
# # stride = 1 work slow
# ax.plot_surface(x1, y1, np.zeros_like(x1) + bb_min[1], rstride=1, cstride=1, facecolors=arr)

#
for points in splines:
    ax.plot3D(*points.transpose()[[0, 2, 1], :])

plt.show()
print(points)
