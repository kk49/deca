import os
from .errors import *
from .file import *
from .ff_types import *
from .ff_adf import AdfDatabase
from .db_core import VfsDatabase, VfsNode, VfsSelection
from .ff_avtx import image_export
from .ff_sarc import FileSarc
from .util import make_dir_for_file
from .export_import_adf import node_export_adf_processed, node_export_adf_gltf, node_export_adf_text
from .export_import_rtpc import node_export_rtpc_gltf, node_export_rtpc_text
from .export_import_audio import node_export_fsb5c_processed


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

                vfs.logger.log('Exporting {}'.format(out_file))

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
        vfs_selection: VfsSelection,
        extract_dir: str,
        allow_overwrite=False):
    node_map = vfs_selection.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            node = nodes_real[0]
            try:
                extract_node_raw(vfs, node, extract_dir, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def nodes_export_contents(
        vfs: VfsDatabase,
        vfs_selection: VfsSelection,
        extract_dir: str,
        allow_overwrite=False):
    node_map = vfs_selection.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None:
            node = nodes_real[0]
            try:
                if node.file_type == FTYPE_SARC:
                    sarc = FileSarc()
                    with vfs.file_obj_from(node) as f:
                        sarc.header_deserialize(f)
                        # extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
                    entry_v_paths = [v.v_path for v in sarc.entries]
                    entry_is_symlinks = [v.offset == 0 for v in sarc.entries]

                    nodes_export_raw(vfs, vfs_selection, extract_dir, allow_overwrite)

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
        vfs_selection: VfsSelection,
        extract_dir: str,
        allow_overwrite=False,
        save_to_one_dir=True
):
    vs_adf = []
    vs_rtpc = []

    node_map = vfs_selection.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None and nodes_real[0] .is_valid() and nodes_real[0] .offset is not None:
            node = nodes_real[0]
            try:
                if node.file_type in {FTYPE_ADF, FTYPE_ADF_BARE}:
                    vs_adf.append(node)
                elif node.file_type in {FTYPE_RTPC}:
                    vs_rtpc.append(node)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    adf_db = AdfDatabase(vfs)
    for node in vs_adf:
        try:
            node_export_adf_gltf(
                vfs,
                adf_db,
                node,
                extract_dir,
                allow_overwrite=allow_overwrite,
                save_to_one_dir=save_to_one_dir)

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    for node in vs_rtpc:
        try:
            node_export_rtpc_gltf(
                vfs,
                node,
                extract_dir,
                allow_overwrite=allow_overwrite,
                save_to_one_dir=save_to_one_dir
            )
        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def nodes_export_processed(
        vfs: VfsDatabase,
        vfs_selection: VfsSelection,
        extract_dir: str,
        allow_overwrite=False,
        save_to_processed=False,
        save_to_text=False):
    vs_adf = []
    vs_rtpc = []
    vs_images = []
    vs_fsb5cs = []
    vs_other = []
    node_map = vfs_selection.nodes_selected_get()
    for k, (nodes_real, nodes_sym) in node_map.items():
        if nodes_real and nodes_real[0] is not None and nodes_real[0] .is_valid() and nodes_real[0] .offset is not None:
            node = nodes_real[0]
            try:
                if node.file_type in {FTYPE_ADF, FTYPE_ADF_BARE}:
                    vs_adf.append(node)
                elif node.file_type in {FTYPE_RTPC}:
                    vs_rtpc.append(node)
                elif node.file_type in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                    vs_images.append(node)
                elif node.file_type in {FTYPE_FSB5C}:
                    vs_fsb5cs.append(node)
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
        try:
            if save_to_processed:
                node_export_adf_processed(vfs, adf_db, node, extract_dir, allow_overwrite=allow_overwrite)

            if save_to_text:
                node_export_adf_text(vfs, adf_db, node, extract_dir, allow_overwrite=allow_overwrite)

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    for node in vs_rtpc:
        try:
            if save_to_text:
                node_export_rtpc_text(vfs, node, extract_dir, allow_overwrite=allow_overwrite)

        except EDecaFileExists as e:
            vfs.logger.log(
                'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
