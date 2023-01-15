import os
import re
from .errors import *
from .file import *
from .ff_types import *
from .ff_adf import AdfDatabase, EDecaMissingAdfType
from .db_core import VfsDatabase, VfsNode
from .db_view import VfsView
from .ff_avtx import image_export
from .ff_sarc import FileSarc
from .util import make_dir_for_file
from .export_import_adf import node_export_adf_processed, node_export_adf_gltf, node_export_adf_text
from .export_import_rtpc import node_export_rtpc_gltf, node_export_rtpc_text
from .export_import_audio import node_export_fsb5c_processed
from .export_map import export_map


def extract_node_raw(
        vfs: VfsDatabase,
        node: VfsNode,
        extract_dir: str,
        allow_overwrite):
    if node.is_valid():
        if node.offset is not None:
            with ArchiveFile(vfs.file_obj_from(node)) as f:
                if node.v_path is None:
                    out_file = extract_dir + node.v_hash_to_str() + '.dat'
                else:
                    out_file = extract_dir + '{}'.format(node.v_path.decode('utf-8'))

                vfs.logger.log('Exporting Raw: {}'.format(out_file))

                make_dir_for_file(out_file)

                if node.file_type == FTYPE_ADF_BARE:
                    vfs.logger.log(
                        'WARNING: Extracting raw ADFB file {} not supported, extract gdc/global.gdcc instead.'.format(
                            out_file))

                if not allow_overwrite and os.path.isfile(out_file):
                    vfs.logger.log(
                        'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(out_file))
                    # raise DecaFileExists(out_file)
                else:
                    buf = f.read(node.size_u)
                    with ArchiveFile(open(out_file, 'wb')) as fo:
                        fo.write(buf)

            return out_file

    return None


def nodes_export_raw(
        vfs: VfsDatabase,
        vfs_view: VfsView,
        extract_dir: str,
        allow_overwrite=False):
    node_map = vfs_view.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            uid = nodes_real[0]
            node = vfs_view.node_where_uid(uid)
            try:
                extract_node_raw(vfs, node, extract_dir, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def nodes_export_map(
        vfs: VfsDatabase,
        vfs_view: VfsView,
        extract_dir: str,
        export_map_full,
        export_map_tiles):
    node_map = vfs_view.nodes_selected_get()

    prefixes = set()
    pat = re.compile(r'^(.*zoom).*$')
    for k in node_map.keys():
        mr = pat.match(k)
        if mr:
            prefixes.add(mr.group(1))

    for prefix in prefixes:
        d, f = os.path.split(prefix)
        export_path = os.path.join(extract_dir, d, 'deca.map')
        export_map(vfs, prefix, export_path, export_map_full, export_map_tiles)


def nodes_export_contents(
        vfs: VfsDatabase,
        vfs_view: VfsView,
        extract_dir: str,
        allow_overwrite=False):
    node_map = vfs_view.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            uid = nodes_real[0]
            node = vfs_view.node_where_uid(uid)
            try:
                if node.file_type == FTYPE_SARC:
                    sarc = FileSarc()
                    with vfs.file_obj_from(node) as f:
                        sarc.header_deserialize(f)
                        # extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
                    entry_v_paths = [v.v_path for v in sarc.entries]
                    entry_is_symlinks = [v.offset == 0 for v in sarc.entries]

                    nodes_export_raw(vfs, vfs_view, extract_dir, allow_overwrite)

                    file_list_name = os.path.join(extract_dir, node.v_path.decode('utf-8') + '.DECA.FILE_LIST.txt')

                    with open(file_list_name, 'w') as f:
                        f.write('sarc.clear();\n')
                        for vp, is_sym in zip(entry_v_paths, entry_is_symlinks):
                            op = 'sarc.add'
                            if is_sym:
                                op = 'sarc.symlink'
                            f.write('{}("{}");\n'.format(op, vp.decode('utf-8')))

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def nodes_export_gltf(
        vfs: VfsDatabase,
        vfs_view: VfsView,
        extract_dir: str,
        allow_overwrite,
        save_to_one_dir,
        include_skeleton,
        texture_format,
):
    vs_adf = []
    vs_rtpc = []

    node_map = vfs_view.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            uid = nodes_real[0]
            node = vfs_view.node_where_uid(uid)
            if node.is_valid() and node.offset is not None:
                try:
                    if node.file_type in ftype_adf_family:
                        vs_adf.append(node)
                    elif node.file_type in {FTYPE_RTPC}:
                        vs_rtpc.append(node)

                except EDecaFileExists as e:
                    vfs.logger.log(
                        'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
                except EDecaFileMissing as e:
                    vfs.logger.log(
                        'ERROR: Extracting {} Failed: {}  '.format(node.v_path, e.args[0]))

    adf_db = AdfDatabase(vfs)
    for node in vs_adf:
        try:
            node_export_adf_gltf(
                vfs,
                adf_db,
                node,
                extract_dir,
                allow_overwrite=allow_overwrite,
                save_to_one_dir=save_to_one_dir,
                include_skeleton=include_skeleton,
                texture_format=texture_format,
            )

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extracting {} Failed: overwrite disabled and {} exists, skipping'.format(node.v_path, e.args[0]))
        except EDecaMissingAdfType as e:
            vfs.logger.log(
                'ERROR: Extracting {} Failed: Missing ADF Type 0x{:08x}  '.format(node.v_path, e.type_id))
        except EDecaFileMissing as e:
            vfs.logger.log(
                'ERROR: Extracting {} Failed: {}  '.format(node.v_path, e.args[0]))

    for node in vs_rtpc:
        try:
            node_export_rtpc_gltf(
                vfs,
                node,
                extract_dir,
                allow_overwrite=allow_overwrite,
                save_to_one_dir=save_to_one_dir,
                include_skeleton=include_skeleton,
                texture_format=texture_format,
            )
        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def nodes_export_processed(
        vfs: VfsDatabase,
        vfs_view: VfsView,
        extract_dir: str,
        allow_overwrite=False,
        save_to_processed=False,
        save_to_text=False):
    vs_adf = []
    vs_rtpc = []
    vs_images = []
    vs_fsb5cs = []
    vs_other = []
    node_map = vfs_view.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            nodes = [vfs_view.node_where_uid(uid) for uid in nodes_real]
            node = nodes[0]
            if node.is_valid() and node.offset is not None:
                try:
                    if node.file_type in ftype_adf_family:
                        # handle the case for GenZero where ADF files can be in the
                        nodes_adf = []
                        nodes_adfb = []

                        for vnode in nodes:
                            if vnode.file_type == FTYPE_ADF_BARE:
                                nodes_adfb.append(vnode)
                            else:
                                nodes_adf.append(vnode)

                        if len(nodes_adf) > 0:
                            vs_adf.append(nodes_adf[0])
                        if len(nodes_adfb) > 0:
                            vs_adf.append(nodes_adfb[0])
                    elif node.file_type in {FTYPE_RTPC}:
                        vs_rtpc.append(node)
                    elif node.file_type in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                        vs_images.append(node)
                    elif node.file_type in {FTYPE_FSB5C}:
                        vs_fsb5cs.append(node)
                    elif isinstance(node.v_path, bytes) and (node.v_path.endswith(b'.csvc') or node.v_path.endswith(b'.bmpc')):
                        vs_rename.append(node)
                    else:
                        vs_other.append(node)

                except EDecaFileExists as e:
                    vfs.logger.log(
                        'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    if save_to_processed:
        for node in vs_fsb5cs:
            try:
                node_export_fsb5c_processed(vfs, node, extract_dir, allow_overwrite=allow_overwrite)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

        for node in vs_images:
            try:
                image_export(vfs, node, extract_dir, False, True, allow_overwrite=allow_overwrite)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    adf_db = AdfDatabase(vfs)
    for node in vs_adf:
        if save_to_processed:
            try:
                node_export_adf_processed(vfs, adf_db, node, extract_dir, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
            except EDecaMissingAdfType as e:
                vfs.logger.log(
                    'WARNING: Extracting {} Failed: Missing ADF Type 0x{:08x}  '.format(node.v_path, e.type_id))

        if save_to_text:
            try:
                node_export_adf_text(vfs, adf_db, node, extract_dir, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
            except EDecaMissingAdfType as e:
                vfs.logger.log(
                    'WARNING: Extracting {} Failed: Missing ADF Type 0x{:08x}  '.format(node.v_path, e.type_id))

    for node in vs_rtpc:
        try:
            if save_to_text:
                node_export_rtpc_text(vfs, node, extract_dir, allow_overwrite=allow_overwrite)

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
