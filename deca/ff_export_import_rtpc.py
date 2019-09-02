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
            part_modelc_vhash = child.prop_map[0x32b409e0].data
            part_modelc_vpath = list(vfs.map_hash_to_vpath[part_modelc_vhash])[0]
            part_matrix = Deca3dMatrix(col_major=child.prop_map[0x6ca6d4b9].data)

            if part_modelc_vpath is not None:
                with DecaGltfNode(gltf, name=os.path.basename(part_modelc_vpath)):
                    gltf.export_modelc(part_modelc_vpath, part_matrix)
        elif child_class == b'CSecondaryMotionAttachment':
            part_modelc_vpath = child.prop_map[0x0f94740b].data
            part_matrix = Deca3dMatrix(col_major=child.prop_map[0x6ca6d4b9].data)

            if part_modelc_vpath is not None:
                with DecaGltfNode(gltf, name=os.path.basename(part_modelc_vpath)):
                    gltf.export_modelc(part_modelc_vpath, part_matrix)

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


def rtpc_export_node_cmotorbike_recurse(rtpc: RtpcNode, gltf: DecaGltf, vfs: VfsStructure, material_properties=None):
    for child in rtpc.child_table:
        child_class = b''
        if PropName.CLASS_NAME.value in child.prop_map:
            child_class = child.prop_map[PropName.CLASS_NAME.value].data

        if child_class == b'CPartProp':
            part_modelc_vhash = child.prop_map[0xa74f2259].data
            part_modelc_vpath = list(vfs.map_hash_to_vpath[part_modelc_vhash])[0]
            part_matrix = Deca3dMatrix(col_major=child.prop_map[0x6ca6d4b9].data)

            if part_modelc_vpath is not None:
                with DecaGltfNode(gltf, name=os.path.basename(part_modelc_vpath)):
                    gltf.export_modelc(part_modelc_vpath, part_matrix, material_properties=material_properties)

        elif child_class == b'CSkeletalAnimatedObject':
            part_modelc_vpath = child.prop_map[0x0f94740b].data
            part_matrix = Deca3dMatrix(col_major=child.prop_map[0x6ca6d4b9].data)

            if part_modelc_vpath is not None:
                with DecaGltfNode(gltf, name=os.path.basename(part_modelc_vpath)):
                    gltf.export_modelc(part_modelc_vpath, part_matrix, material_properties=material_properties)

        rtpc_export_node_cmotorbike_recurse(child, gltf, vfs)


def rtpc_export_node_cmotorbike(rtpc: RtpcNode, vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite=False, save_to_one_dir=True):
    vfs.logger.log('Exporting {}: Started'.format(vnode.vpath.decode('utf-8')))
    gltf = DecaGltf(vfs, export_path, vnode.vpath.decode('utf-8'), save_to_one_dir=save_to_one_dir)

    with gltf.scene():
        material_properties = {
            'color_mask_r': rtpc.prop_map[0x46afe5b4].data,
            'color_mask_g': rtpc.prop_map[0xb4331697].data,
            'color_mask_b': rtpc.prop_map[0x98796658].data,
        }

        with DecaGltfNode(gltf, name=os.path.basename(vnode.vpath.decode('utf-8'))):
            rtpc_export_node_cmotorbike_recurse(rtpc, gltf, vfs, material_properties=material_properties)

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
        elif child_class == b'CMotorBike':
            rtpc_export_node_cmotorbike(child, vfs, vnode, export_path, allow_overwrite, save_to_one_dir)


def rtpc_export(vfs: VfsStructure, vnodes: List[VfsNode], export_path, allow_overwrite=False, save_to_one_dir=True):
    for vnode in vnodes:
        try:
            rtpc_export_node(vfs, vnode, export_path, allow_overwrite=allow_overwrite, save_to_one_dir=save_to_one_dir)
        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
