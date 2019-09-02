import os
import re
from typing import List, TypeVar
from .errors import *
from .file import *
from .ff_types import *
from .vfs_db import VfsStructure, VfsNode
from .export_import_adf import adf_export
from .export_import_rtpc import rtpc_export
from .ff_avtx import Ddsc, image_export


NodeListElement = TypeVar('NodeListElement', str, bytes, VfsNode)


def expand_vpaths(vfs: VfsStructure, vs, mask):
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
        vfs: VfsStructure,
        node: VfsNode,
        extract_dir: str,
        do_sha1sum,
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

                # TODO
                # if do_sha1sum:
                #     # path, file = os.path.split(ofile)
                #     # sfile = os.path.join(path, '.' + file)
                #     sfile = ofile + '.deca_sha1sum'
                #     hsha = sha1(buf).hexdigest()
                #     vfs.logger.log('SHA1SUM {} {}'.format(hsha, sfile))
                #     with open(sfile, 'w') as fo:
                #         fo.write(hsha)
            return ofile

    return None


def extract_raw(
        vfs: VfsStructure,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        do_sha1sum=False,
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
                extract_node_raw(vfs, vnode, extract_dir, do_sha1sum, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))


def extract_processed(
        vfs: VfsStructure,
        vnodes: List[NodeListElement],
        mask: bytes,
        extract_dir: str,
        do_sha1sum=False,
        allow_overwrite=False,
        save_to_processed=False,
        save_to_text=False,
        save_to_one_dir=True):
    vs = expand_vpaths(vfs, vnodes, mask)

    vs_adf = []
    vs_rtpc = []
    vs_images = []
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
                else:
                    vs_other.append(vnode)

            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

    if save_to_processed:
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
