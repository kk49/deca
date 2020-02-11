import os
from typing import List, TypeVar
from .errors import *
from .file import *
from .ff_types import *
from .vfs_db import VfsDatabase, VfsNode
from .export_import_adf import adf_export
from .export_import_rtpc import rtpc_export
from .ff_avtx import image_export
from .ff_sarc import FileSarc
from .util import make_dir_for_file


NodeListElement = TypeVar('NodeListElement', str, bytes, VfsNode)


def fsb5c_export_processed(vfs: VfsDatabase, node, extract_dir, allow_overwrite=False):
    with vfs.file_obj_from(node) as f:
        buffer = f.read(node.size_u)

    # TODO hack just trim 16 byte header
    buffer = buffer[16:]

    if node.v_path is None:
        ofile = extract_dir + '{:08X}.dat.DECA.fsb'.format(node.v_hash)
    else:
        ofile = extract_dir + '{}.DECA.fsb'.format(node.v_path.decode('utf-8'))

    vfs.logger.log('Exporting {}'.format(ofile))

    make_dir_for_file(ofile)

    if allow_overwrite or not os.path.isfile(ofile):
        with open(ofile, 'wb') as fo:
            fo.write(buffer)


def expand_vpaths(vfs: VfsDatabase, vs, mask):
    vos = []

    for v in vs:
        id_pat = v
        if isinstance(id_pat, str):
            id_pat = v.encode('ascii')

        if isinstance(id_pat, bytes):
            nodes_all = vfs.nodes_where_match(v_path_like=id_pat, v_path_regexp=mask)
            nodes = []
            for node in nodes_all:
                if node.file_type != FTYPE_SYMLINK and node.offset is not None:
                    nodes.append(node)
            nodes = dict([(n.v_path, n) for n in nodes])
            nodes = list(nodes.values())
            vos += nodes
        else:
            vos.append(v)

    return vos


def extract_node_raw(
        vfs: VfsDatabase,
        node: VfsNode,
        extract_dir: str,
        allow_overwrite):
    if node.is_valid():
        if node.offset is not None:
            with ArchiveFile(vfs.file_obj_from(node)) as f:
                if node.v_path is None:
                    ofile = extract_dir + node.v_hash_to_str() + '.dat'
                else:
                    ofile = extract_dir + '{}'.format(node.v_path.decode('utf-8'))

                vfs.logger.log('Exporting {}'.format(ofile))

                make_dir_for_file(ofile)

                if node.file_type == FTYPE_ADF_BARE:
                    do_export_raw = False
                    vfs.logger.log(
                        'WARNING: Extracting raw ADFB file {} not supported, extract gdc/global.gdcc instead.'.format(
                            ofile))

                if not allow_overwrite and os.path.isfile(ofile):
                    vfs.logger.log(
                        'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(ofile))
                    # raise DecaFileExists(ofile)
                else:
                    buf = f.read(node.size_u)
                    with ArchiveFile(open(ofile, 'wb')) as fo:
                        fo.write(buf)

            return ofile

    return None


def find_vnode(vfs: VfsDatabase, v):
    vnode = None
    v_path = None
    if isinstance(v, bytes):
        v_path = v
    elif isinstance(v, VfsNode):
        vnode = v
    else:
        raise NotImplementedError('find_vnode: Could not extract {}'.format(v))

    if v_path is not None:
        nodes = vfs.nodes_where_match(v_path=v_path)
        vnode = None
        for node in nodes:
            if node.offset is not None:
                vnode = node
                break
        if vnode is None:
            raise EDecaFileMissing('find_vnode: Missing {}'.format(v_path.decode('utf-8')))

    return vnode


def extract_raw(
        vfs: VfsDatabase,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        allow_overwrite=False):
    vs = expand_vpaths(vfs, vnodes, mask)
    for i, v in enumerate(vs):
        vnode = find_vnode(vfs, v)

        if vnode is not None:
            try:
                extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def extract_contents(
        vfs: VfsDatabase,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        allow_overwrite=False):
    vs = expand_vpaths(vfs, vnodes, mask)
    for i, v in enumerate(vs):
        vnode = find_vnode(vfs, v)

        if vnode is not None:
            try:
                if vnode.file_type == FTYPE_SARC:
                    sarc = FileSarc()
                    with vfs.file_obj_from(vnode) as f:
                        sarc.header_deserialize(f)
                        # extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
                    entry_vpaths = [v.v_path for v in sarc.entries]
                    entry_is_symlinks = [v.offset == 0 for v in sarc.entries]

                    extract_raw(vfs, entry_vpaths, b'^.*$', extract_dir, allow_overwrite)

                    file_list_name = os.path.join(extract_dir, vnode.v_path.decode('utf-8') + '.DECA.FILE_LIST.txt')

                    with open(file_list_name, 'w') as f:
                        f.write('sarc.clear();')
                        for vp, isym in zip(entry_vpaths, entry_is_symlinks):
                            op = 'sarc.add'
                            if isym:
                                op = 'sarc.symlink'
                            f.write('{}("{}");\n'.format(op, vp.decode('utf-8')))

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def extract_processed(
        vfs: VfsDatabase,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        allow_overwrite=False,
        save_to_processed=False,
        save_to_text=False,
        save_to_one_dir=True):
    vs = expand_vpaths(vfs, vnodes, mask)

    vs_adf = []
    vs_rtpc = []
    vs_images = []
    vs_fsb5cs = []
    vs_other = []
    for i, v in enumerate(vs):
        vnode = find_vnode(vfs, v)

        if vnode is not None and vnode.is_valid() and vnode.offset is not None:
            try:
                if vnode.file_type in {FTYPE_ADF, FTYPE_ADF_BARE}:
                    vs_adf.append(vnode)
                elif vnode.file_type in {FTYPE_RTPC}:
                    vs_rtpc.append(vnode)
                elif vnode.file_type in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                    vs_images.append(vnode)
                elif vnode.file_type in {FTYPE_FSB5C}:
                    vs_fsb5cs.append(vnode)
                else:
                    vs_other.append(vnode)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    if save_to_processed:
        for vnode in vs_fsb5cs:
            if vnode.v_path is None:
                ofile = extract_dir + '{:08X}.dat'.format(vnode.v_hash)
            else:
                ofile = extract_dir + '{}'.format(vnode.v_path.decode('utf-8'))

            vfs.logger.log('Exporting {}'.format(ofile))

            make_dir_for_file(ofile)

            try:
                fsb5c_export_processed(vfs, vnode, extract_dir, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

        for vnode in vs_images:
            if vnode.v_path is None:
                ofile = extract_dir + '{:08X}.dat'.format(vnode.v_hash)
            else:
                ofile = extract_dir + '{}'.format(vnode.v_path.decode('utf-8'))

            vfs.logger.log('Exporting {}'.format(ofile))

            make_dir_for_file(ofile)

            try:
                image_export(vfs, vnode, extract_dir, False, True, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    adf_export(
        vfs, vs_adf, extract_dir,
        allow_overwrite=allow_overwrite,
        save_to_processed=save_to_processed,
        save_to_text=save_to_text,
        save_to_one_dir=save_to_one_dir)

    rtpc_export(
        vfs, vs_rtpc, extract_dir,
        allow_overwrite=allow_overwrite,
        save_to_processed=save_to_processed,
        save_to_text=save_to_text,
        save_to_one_dir=save_to_one_dir)
