import os
from .db_core import VfsDatabase, VfsNode
from .errors import EDecaFileExists
from .ff_rtpc import Rtpc, RtpcNode, RtpcVisitorDumpToString, rtpc_from_binary, \
    h_prop_skeleton, h_prop_model_skeleton, h_prop_class, h_prop_class_hash
from .ff_adf_amf_gltf import DecaGltf, DecaGltfNode, Deca3dMatrix

'''
0xd31ab684 part name

b'CRigidObject' 
'''


def rtpc_export_node_recurse(
        rtpc: RtpcNode,
        gltf: DecaGltf,
        vfs: VfsDatabase,
        world_matrix=None,
        material_properties=None,
        skeleton_raw_path=None):
    rtpc_class = b''
    if h_prop_class in rtpc.prop_map:
        rtpc_class = rtpc.prop_map[h_prop_class].data
    elif h_prop_class_hash in rtpc.prop_map:
        rtpc_class_hash = rtpc.prop_map[h_prop_class_hash].data
        rtpc_class_hash = vfs.hash_string_match(hash32=rtpc_class_hash)
        if len(rtpc_class_hash) > 0:
            rtpc_class = rtpc_class_hash[0][1]

    rtpc_model_vpath = None

    if 0x6ca6d4b9 in rtpc.prop_map:
        ref_matrix = Deca3dMatrix(col_major=rtpc.prop_map[0x6ca6d4b9].data)
        world_matrix = Deca3dMatrix.matmul(world_matrix, ref_matrix)

    if material_properties is None:
        material_properties = {}
    else:
        material_properties = material_properties.copy()

    if 0x46afe5b4 in rtpc.prop_map:
        material_properties['color_mask_r'] = rtpc.prop_map[0x46afe5b4].data

    if 0xb4331697 in rtpc.prop_map:
        material_properties['color_mask_g'] = rtpc.prop_map[0xb4331697].data

    if 0x98796658 in rtpc.prop_map:
        material_properties['color_mask_b'] = rtpc.prop_map[0x98796658].data

    # skeleton lookup
    if h_prop_model_skeleton in rtpc.prop_map:
        skeleton_raw_path = rtpc.prop_map[h_prop_model_skeleton].data
    elif h_prop_skeleton in rtpc.prop_map:
        skeleton_raw_path = rtpc.prop_map[h_prop_skeleton].data

    if isinstance(skeleton_raw_path, int):
        skeleton_raw_path = vfs.hash_string_match(hash32=skeleton_raw_path)
        if len(skeleton_raw_path) > 0:
            skeleton_raw_path = skeleton_raw_path[0][1]
        else:
            skeleton_raw_path = None

    # model lookup
    if rtpc_class == b'CRigidObject':
        rtpc_model_vpath = rtpc.prop_map[0x32b409e0].data
    elif rtpc_class == b'SCharacterPart':
        rtpc_model_vpath = rtpc.prop_map[0xb498c27d].data
    elif rtpc_class == b'CPartProp':
        rtpc_model_vpath = rtpc.prop_map[0xa74f2259].data
    elif rtpc_class in {b'CSkeletalAnimatedObject', b'CSecondaryMotionAttachment'}:
        if 0x0f94740b in rtpc.prop_map:
            rtpc_model_vpath = rtpc.prop_map[0x0f94740b].data
    elif rtpc_class in {b'CCharacter'}:
        if 0xe8129fe6 in rtpc.prop_map:
            rtpc_model_vpath = rtpc.prop_map[0xe8129fe6].data
    elif rtpc_class in {b'CBulletWeaponBase', b'CWeaponModItem', b'CModelAttachementWeaponComponent'}:
        # TODO entity_type = rtpc.prop_map[0xd31ab684].data
        if 0xf9dcf6ab in rtpc.prop_map:
            rtpc_model_vpath = rtpc.prop_map[0xf9dcf6ab].data

    if isinstance(rtpc_model_vpath, int):
        rtpc_model_vpath = vfs.hash_string_match(hash32=rtpc_model_vpath)
        if len(rtpc_model_vpath) > 0:
            rtpc_model_vpath = rtpc_model_vpath[0][1]
        else:
            rtpc_model_vpath = None

    if rtpc_model_vpath is not None and len(rtpc_model_vpath) > 0:
        gltf.export_modelc(
            rtpc_model_vpath, world_matrix,
            material_properties=material_properties,
            skeleton_raw_path=skeleton_raw_path)

    for child in rtpc.child_table:
        rtpc_export_node_recurse(
            child, gltf, vfs,
            world_matrix=world_matrix, material_properties=material_properties, skeleton_raw_path=skeleton_raw_path)


def node_export_rtpc_gltf(
        vfs: VfsDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    vfs.logger.log('Exporting {}: Started'.format(vnode.v_path.decode('utf-8')))

    rtpc = Rtpc()
    with vfs.file_obj_from(vnode) as f:
        rtpc_from_binary(f, rtpc)

    gltf = DecaGltf(
        vfs, export_path, vnode.v_path.decode('utf-8'),
        save_to_one_dir=save_to_one_dir, include_skeleton=include_skeleton, texture_format=texture_format)

    with gltf.scene():
        with DecaGltfNode(gltf, name=os.path.basename(vnode.v_path.decode('utf-8'))):
            rtpc_export_node_recurse(rtpc.root_node, gltf, vfs)

    gltf.gltf_save()

    vfs.logger.log('Exporting {}: Complete'.format(vnode.v_path.decode('utf-8')))


def node_export_rtpc_text(
        vfs: VfsDatabase,
        vnode: VfsNode,
        export_path,
        allow_overwrite=False
):
    with vfs.file_obj_from(vnode) as f:
        buffer = f.read(vnode.size_u)

    fn = os.path.join(export_path, vnode.v_path.decode('utf-8')) + '.txt'

    vfs.logger.log('Exporting as Text: {}'.format(fn))

    if not allow_overwrite and os.path.exists(fn):
        raise EDecaFileExists(fn)

    dump = RtpcVisitorDumpToString(vfs)
    dump.visit(buffer)
    s = dump.result()

    ofiledir = os.path.dirname(fn)
    os.makedirs(ofiledir, exist_ok=True)

    with open(fn, 'wt') as f:
        f.write(s)
