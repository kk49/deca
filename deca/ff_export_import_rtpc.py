import os
import re
from typing import List
from .vfs_db import VfsStructure, VfsNode
from .errors import EDecaFileExists
from .ff_rtpc import Rtpc, PropName, RtpcNode
from .ff_adf_amg_gltf import DecaGltf, DecaGltfNode, Deca3dMatrix

'''
0xd31ab684 part name

b'CRigidObject' 
'''


def rtpc_export_node_ccharacter_recurse(rtpc: RtpcNode, gltf: DecaGltf, vfs: VfsStructure):
    for child in rtpc.child_table:
        child_class = b''
        if PropName.CLASS_NAME.value in child.prop_map:
            child_class = child.prop_map[PropName.CLASS_NAME.value].data

        if child_class == b'CRigidObject':
            part_name = child.prop_map[0xd31ab684].data
            part_expr = re.compile(b'.*' + part_name + b'.*modelc')
            part_matrix = Deca3dMatrix(col_major=child.prop_map[0x6ca6d4b9].data)
            # find the part
            part_path = None
            for fn in vfs.map_vpath_to_vfsnodes.keys():
                if part_expr.match(fn):
                    part_path = fn
                    break

            if part_path is not None:
                with DecaGltfNode(gltf, name=os.path.basename(part_path)):
                    gltf.export_modelc(part_path, part_matrix)

        rtpc_export_node_ccharacter_recurse(child, gltf, vfs)


def rtpc_export_node_ccharacter(rtpc: RtpcNode, vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite=False, save_to_one_dir=True):
    vfs.logger.log('Exporting {}: Started'.format(vnode.vpath.decode('utf-8')))
    gltf = DecaGltf(vfs, export_path, vnode.vpath.decode('utf-8'), save_to_one_dir=save_to_one_dir)

    with gltf.scene():
        with DecaGltfNode(gltf, name=os.path.basename(vnode.vpath.decode('utf-8'))):
            base_model = rtpc.prop_map[0xe8129fe6].data
            with DecaGltfNode(gltf, name=os.path.basename(base_model)):
                gltf.export_modelc(base_model, None)

            rtpc_export_node_ccharacter_recurse(rtpc, gltf, vfs)

    gltf.gltf_save()
    vfs.logger.log('Exporting {}: Complete'.format(vnode.vpath.decode('utf-8')))


def rtpc_export_node(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite=False, save_to_one_dir=True):
    rtpc = Rtpc()
    with vfs.file_obj_from(vnode) as f:
        rtpc.deserialize(f)

    for child in rtpc.root_node.child_table:
        child_class = b''
        if PropName.CLASS_NAME.value in child.prop_map:
            child_class = child.prop_map[PropName.CLASS_NAME.value].data

        if child_class == b'CCharacter':
            rtpc_export_node_ccharacter(child, vfs, vnode, export_path, allow_overwrite, save_to_one_dir)


def rtpc_export(vfs: VfsStructure, vnodes: List[VfsNode], export_path, allow_overwrite=False, save_to_one_dir=True):
    for vnode in vnodes:
        try:
            rtpc_export_node(vfs, vnode, export_path, allow_overwrite=allow_overwrite, save_to_one_dir=save_to_one_dir)
        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
