import os
import re
from typing import List, TypeVar
from .errors import *
from .file import *
from .ff_types import *
from .vfs_db import VfsStructure, VfsNode
from .ff_export_import_adf import adf_export
from .ff_avtx import Ddsc, image_export


StrBytes = TypeVar('StrBytes', str, bytes, VfsNode)


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


def extract_raw(vfs: VfsStructure, vnodes: List[StrBytes], extract_dir: str, do_sha1sum, allow_overwrite=False):
    vs = vnodes.copy()
    for i, v in enumerate(vs):
        vnode = None
        id = None
        if isinstance(v, str):
            id = str.encode('ascii')
        elif isinstance(v, bytes):
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


def extract_node_processed(
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

                try:
                    if node.ftype in {FTYPE_ADF, FTYPE_ADF_BARE}:
                        adf_export(vfs, node, ofile, allow_overwrite=allow_overwrite)
                    elif node.ftype in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                        image_export(vfs, node, extract_dir, False, True, allow_overwrite=allow_overwrite)
                except EDecaFileExists as e:
                    vfs.logger.log(
                        'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))

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


def extract_processed(vfs: VfsStructure, vnodes: List[StrBytes], extract_dir: str, do_sha1sum, allow_overwrite=False):
    vs = vnodes.copy()
    for i, v in enumerate(vs):
        vnode = None
        id = None
        if isinstance(v, str):
            id = str.encode('ascii')
        elif isinstance(v, bytes):
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
                extract_node_processed(vfs, vnode, extract_dir, do_sha1sum, allow_overwrite)
            except EDecaFileExists as e:
                vfs.logger.log(
                    'WARNING: Extraction failed overwrite disabled and {} exists, skipping'.format(e.args[0]))
