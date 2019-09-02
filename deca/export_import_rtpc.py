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


def rtpc_export_node_recurse(rtpc: RtpcNode, gltf: DecaGltf, vfs: VfsStructure, world_matrix=None, material_properties=None):
    rtpc_class = b''
    if PropName.CLASS_NAME.value in rtpc.prop_map:
        rtpc_class = rtpc.prop_map[PropName.CLASS_NAME.value].data

    rtpc_model_vpath = None

    if 0x6ca6d4b9 in rtpc.prop_map:
        ref_matrix = Deca3dMatrix(col_major=rtpc.prop_map[0x6ca6d4b9].data)
        world_matrix = Deca3dMatrix.matmul(world_matrix, ref_matrix)

    if rtpc_class == b'CRigidObject':
        rtpc_modelc_vhash = rtpc.prop_map[0x32b409e0].data
        rtpc_model_vpath = list(vfs.map_hash_to_vpath[rtpc_modelc_vhash])[0]
    elif rtpc_class == b'SCharacterPart':
        rtpc_model_vpath = rtpc.prop_map[0xb498c27d].data
    elif rtpc_class == b'CPartProp':
        rtpc_modelc_vhash = rtpc.prop_map[0xa74f2259].data
        rtpc_model_vpath = list(vfs.map_hash_to_vpath[rtpc_modelc_vhash])[0]
    elif rtpc_class in {b'CSkeletalAnimatedObject', b'CSecondaryMotionAttachment'}:
        rtpc_model_vpath = rtpc.prop_map[0x0f94740b].data
    elif rtpc_class in {b'CCharacter'}:
        if 0xe8129fe6 in rtpc.prop_map:
            rtpc_model_vpath = rtpc.prop_map[0xe8129fe6].data
    elif rtpc_class in {b'CBulletWeaponBase', b'CWeaponModItem', b'CModelAttachementWeaponComponent'}:
        entity_type = rtpc.prop_map[0xd31ab684].data
        if 0xf9dcf6ab in rtpc.prop_map:
            rtpc_model_vpath = rtpc.prop_map[0xf9dcf6ab].data
    elif rtpc_class in {b'CMotorBike'}:
        material_properties = {
            'color_mask_r': rtpc.prop_map[0x46afe5b4].data,
            'color_mask_g': rtpc.prop_map[0xb4331697].data,
            'color_mask_b': rtpc.prop_map[0x98796658].data,
        }

    if rtpc_model_vpath is not None:
        gltf.export_modelc(rtpc_model_vpath, world_matrix, material_properties=material_properties)

    for child in rtpc.child_table:
        rtpc_export_node_recurse(child, gltf, vfs, world_matrix=world_matrix, material_properties=material_properties)


def rtpc_export_node(vfs: VfsStructure, vnode: VfsNode, export_path, allow_overwrite=False, save_to_one_dir=True):
    rtpc = Rtpc()
    with vfs.file_obj_from(vnode) as f:
        rtpc.deserialize(f)

    vfs.logger.log('Exporting {}: Started'.format(vnode.vpath.decode('utf-8')))
    gltf = DecaGltf(vfs, export_path, vnode.vpath.decode('utf-8'), save_to_one_dir=save_to_one_dir)

    with gltf.scene():
        with DecaGltfNode(gltf, name=os.path.basename(vnode.vpath.decode('utf-8'))):
            rtpc_export_node_recurse(rtpc.root_node, gltf, vfs)

    gltf.gltf_save()
    vfs.logger.log('Exporting {}: Complete'.format(vnode.vpath.decode('utf-8')))


def rtpc_export(vfs: VfsStructure, vnodes: List[VfsNode], export_path, allow_overwrite=False, save_to_processed=False, save_to_text=False, save_to_one_dir=True):
    for vnode in vnodes:
        try:
            if save_to_processed:
                rtpc_export_node(vfs, vnode, export_path, allow_overwrite=allow_overwrite, save_to_one_dir=save_to_one_dir)

            if save_to_text:
                with vfs.file_obj_from(vnode) as fi:
                    rtpc = Rtpc().deserialize(fi)

                    fn = os.path.join(export_path, vnode.vpath.decode('utf-8')) + '.txt'

                    if not allow_overwrite and os.path.exists(fn):
                        raise EDecaFileExists(fn)

                    s = rtpc.dump_to_string()

                    with open(fn, 'wt') as fo:
                        fo.write(s)

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
