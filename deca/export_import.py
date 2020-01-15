import os
import re
from typing import List, TypeVar
from .errors import *
from .file import *
from .ff_types import *
from .vfs_processor import VfsProcessor, VfsNode
from .export_import_adf import adf_export
from .export_import_rtpc import rtpc_export
from .ff_avtx import Ddsc, image_export
from .ff_sarc import FileSarc


NodeListElement = TypeVar('NodeListElement', str, bytes, VfsNode)


def fsb5c_export_processed(vfs, node, extract_dir, allow_overwrite=False):
    with vfs.file_obj_from(node, 'rb') as f:
        buffer = f.read(node.size_u)

    # TODO hack just trim 16 byte header
    buffer = buffer[16:]

    if node.vpath is None:
        ofile = extract_dir + '{:08X}.dat.DECA.fsb'.format(node.vhash)
    else:
        ofile = extract_dir + '{}.DECA.fsb'.format(node.vpath.decode('utf-8'))

    vfs.logger.log('Exporting {}'.format(ofile))

    ofiledir = os.path.dirname(ofile)
    os.makedirs(ofiledir, exist_ok=True)

    if allow_overwrite or not os.path.isfile(ofile):
        with open(ofile, 'wb') as fo:
            fo.write(buffer)


def expand_vpaths(vfs: VfsProcessor, vs, mask):
    vos = []

    expr_mask = re.compile(mask)
    for v in vs:
        id = v
        if isinstance(v, str):
            id = v.encode('ascii')

        if isinstance(id, bytes):
            expr = re.compile(id)
            for k in vfs.map_vpath_to_vfsnodes:
                if expr.match(k) and expr_mask.match(k):
                    vos.append(k)
        else:
            vos.append(v)

    return vos


def extract_node_raw(
        vfs: VfsProcessor,
        node: VfsNode,
        extract_dir: str,
        allow_overwrite):
    if node.is_valid():
        if node.offset is not None:
            with ArchiveFile(vfs.file_obj_from(node)) as f:
                if node.vpath is None:
                    ofile = extract_dir + '{:08X}.dat'.format(node.vhash)
                else:
                    ofile = extract_dir + '{}'.format(node.vpath.decode('utf-8'))

                vfs.logger.log('Exporting {}'.format(ofile))

                ofiledir = os.path.dirname(ofile)
                os.makedirs(ofiledir, exist_ok=True)

                if node.ftype == FTYPE_ADF_BARE:
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


def extract_raw(
        vfs: VfsProcessor,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        allow_overwrite=False):
    vs = expand_vpaths(vfs, vnodes, mask)
    for i, v in enumerate(vs):
        vnode = None
        id = None
        if isinstance(v, bytes):
            id = v
        elif isinstance(v, VfsNode):
            vnode = v
        else:
            raise NotImplementedError('extract_raw: Could not extract {}'.format(v))

        if id is not None:
            if id in vfs.map_vpath_to_vfsnodes:
                vnode = vfs.map_vpath_to_vfsnodes[id][0]
            else:
                raise EDecaFileMissing('extract_raw: Missing {}'.format(id.decode('utf-8')))

        if vnode is not None:
            try:
                extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def extract_contents(
        vfs: VfsProcessor,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        allow_overwrite=False):
    vs = expand_vpaths(vfs, vnodes, mask)
    for i, v in enumerate(vs):
        vnode = None
        id = None
        if isinstance(v, bytes):
            id = v
        elif isinstance(v, VfsNode):
            vnode = v
        else:
            raise NotImplementedError('extract_raw: Could not extract {}'.format(v))

        if id is not None:
            if id in vfs.map_vpath_to_vfsnodes:
                vnode = vfs.map_vpath_to_vfsnodes[id][0]
            else:
                raise EDecaFileMissing('extract_raw: Missing {}'.format(id.decode('utf-8')))

        if vnode is not None:
            try:
                if vnode.ftype == FTYPE_SARC:
                    sarc = FileSarc()
                    with vfs.file_obj_from(vnode) as f:
                        sarc.header_deserialize(f)
                        # extract_node_raw(vfs, vnode, extract_dir, allow_overwrite)
                    entry_vpaths = [v.vpath for v in sarc.entries]
                    entry_is_symlinks = [v.offset == 0 for v in sarc.entries]

                    extract_raw(vfs, entry_vpaths, b'^.*$', extract_dir, allow_overwrite)

                    file_list_name = os.path.join(extract_dir, vnode.vpath.decode('utf-8') + '.DECA.FILE_LIST.txt')

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
        vfs: VfsProcessor,
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
        vnode = None
        id = None
        if isinstance(v, bytes):
            id = v
        elif isinstance(v, VfsNode):
            vnode = v
        else:
            raise NotImplementedError('extract_raw: Could not extract {}'.format(v))

        if id is not None:
            if id in vfs.map_vpath_to_vfsnodes:
                vnode = vfs.map_vpath_to_vfsnodes[id][0]
            else:
                raise EDecaFileMissing('extract_raw: Missing {}'.format(id.decode('utf-8')))

        if vnode is not None and vnode.is_valid() and vnode.offset is not None:
            try:
                if vnode.ftype in {FTYPE_ADF, FTYPE_ADF_BARE}:
                    vs_adf.append(vnode)
                elif vnode.ftype in {FTYPE_RTPC}:
                    vs_rtpc.append(vnode)
                elif vnode.ftype in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                    vs_images.append(vnode)
                elif vnode.ftype in {FTYPE_FSB5C}:
                    vs_fsb5cs.append(vnode)
                else:
                    vs_other.append(vnode)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    if save_to_processed:
        for vnode in vs_fsb5cs:
            if vnode.vpath is None:
                ofile = extract_dir + '{:08X}.dat'.format(vnode.vhash)
            else:
                ofile = extract_dir + '{}'.format(vnode.vpath.decode('utf-8'))

            vfs.logger.log('Exporting {}'.format(ofile))

            ofiledir = os.path.dirname(ofile)
            os.makedirs(ofiledir, exist_ok=True)

            try:
                fsb5c_export_processed(vfs, vnode, extract_dir, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

        for vnode in vs_images:
            if vnode.vpath is None:
                ofile = extract_dir + '{:08X}.dat'.format(vnode.vhash)
            else:
                ofile = extract_dir + '{}'.format(vnode.vpath.decode('utf-8'))

            vfs.logger.log('Exporting {}'.format(ofile))

            ofiledir = os.path.dirname(ofile)
            os.makedirs(ofiledir, exist_ok=True)

            try:
                image_export(vfs, vnode, extract_dir, False, True, allow_overwrite=allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    adf_export(vfs, vs_adf, extract_dir, allow_overwrite=allow_overwrite, save_to_processed=save_to_processed, save_to_text=save_to_text, save_to_one_dir=save_to_one_dir)

    rtpc_export(vfs, vs_rtpc, extract_dir, allow_overwrite=allow_overwrite, save_to_processed=save_to_processed, save_to_text=save_to_text, save_to_one_dir=save_to_one_dir)
