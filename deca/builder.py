from deca.vfs_base import VfsBase, VfsNode
from deca.ff_types import *
from deca.ff_sarc import FileSarc, EntrySarc
from deca.ff_avtx import image_import
from deca.errors import *
from deca.file import ArchiveFile
from deca.util import align_to
import os
import shutil
import re
import numpy as np
from pprint import pprint, pformat
from copy import deepcopy
from typing import Union, List


class Builder:
    def __init__(self):
        pass

    def build_node_sarc(self, dst_path: str, src_path: Union[None, str], vnode: VfsNode, vfs: VfsBase, vpath_complete_map):
        assert(vnode.ftype == FTYPE_SARC)

        vpath = vnode.vpath
        print('BUILD SARC {}'.format(vnode.vpath))

        # parse existing file
        sarc_file = FileSarc()
        with vfs.file_obj_from(vnode) as f:
            sarc_file.header_deserialize(f)

        if src_path is not None:
            if src_path.find('DECA.FILE_LIST') >= 0:
                with open(src_path, 'r') as f:
                    src_lines = f.readlines()
                callex = re.compile(r'^([A-Za-z]*[.A-Za-z]*)\(([^\)]*)\);$')
                for src_idx, src_line in enumerate(src_lines):
                    src_context = f'{src_path}:{src_idx + 1}'
                    mr = callex.match(src_line)
                    if mr is not None:
                        cmd = mr.group(1)
                        param = mr.group(2)
                    else:
                        raise EDecaBuildError(
                            'BUILD ERROR: {}: Parser error in command "{}"'.format(src_context, src_line))

                    mr = re.match(r'^"([^"]*)"$', param)
                    vpath = None
                    if mr is not None:
                        vpath = mr.group(1).encode('ascii')

                    if cmd == 'sarc.clear':
                        sarc_file.entries.clear()
                    elif cmd in {'sarc.add', 'sarc.symlink'}:
                        # Check to make sure entry does not exist
                        for entry in sarc_file.entries:
                            if entry.vpath == vpath:
                                raise EDecaBuildError(
                                    'BUILD ERROR: {}: Tried to re-add vpath'.format(src_context, vpath.decode('UTF-8')))

                        # Add to end
                        entry = EntrySarc(vpath=vpath)
                        entry.is_symlink = cmd == 'sarc.symlink'
                        entry.length = vfs.map_vpath_to_vfsnodes[vpath][0].size_u
                        sarc_file.entries.append(entry)
                    # elif cmd == 'sarc.remove':
                    #     pass
                    else:
                        raise EDecaBuildError('BUILD ERROR: {}: Unhandled command: {}'.format(src_context, cmd))

            else:
                raise EDecaBuildError('BUILD ERROR: Unhandled src file for SARC file: {}'.format(src_path))

        src_files: List[Union[None, str]] = [None] * len(sarc_file.entries)
        entry: EntrySarc
        for i, entry in enumerate(sarc_file.entries):
            if entry.vpath in vpath_complete_map:
                src_file = vpath_complete_map[entry.vpath]
                src_files[i] = src_file
                entry.length = os.stat(src_file).st_size

        # extract existing file
        fn_dst = os.path.join(dst_path, vnode.vpath.decode('utf-8'))
        pt, fn = os.path.split(fn_dst)
        os.makedirs(pt, exist_ok=True)

        with ArchiveFile(open(fn_dst, 'wb')) as fso:
            sarc_file.header_serialize(fso)

            for i, entry in enumerate(sarc_file.entries):
                buf = None
                src_file = src_files[i]
                if entry.is_symlink:
                    print('  SYMLINK {}'.format(entry.vpath))
                elif src_file is not None:
                    print('  INSERTING {} src file to new file'.format(entry.vpath))
                    with open(src_file, 'rb') as f:
                        buf = f.read(entry.length)
                else:
                    print('  COPYING {} from old file to new file'.format(entry.vpath))
                    vn = vfs.map_vpath_to_vfsnodes[entry.vpath][0]
                    with vfs.file_obj_from(vn) as fsi:
                        buf = fsi.read(entry.length)

                if buf is not None:
                    fso.seek(entry.offset)
                    fso.write(buf)

        vpath_complete_map[vpath] = fn_dst

    def build_node(self, dst_path: str, src_path: Union[None, str], vnode: VfsNode, vfs: VfsBase, vpath_complete_map):
        vpath = vnode.vpath

        if vnode.ftype == FTYPE_SARC:
            self.build_node_sarc(dst_path, src_path, vnode, vfs, vpath_complete_map)
        elif src_path is None:
            pass  # no source path,
        elif src_path.find('DECA') >= 0:
            pass  # BUILD file(s) do not copy
        elif re.match(r'^.*\.ddsc$', src_path) or re.match(r'^.*\.hmddsc$', src_path) or re.match(r'^.*\.atx?$', src_path):
            pass  # DO NOT USE THESE FILES image builder should use .ddsc.dds
        elif src_path.endswith('.ddsc.dds'):
            # Build texture
            vnode = vfs.map_vpath_to_vfsnodes[vpath][0]

            # make ddsc.dds into ddsc and avtxs
            compiled_files = image_import(vfs, vnode, src_path, dst_path)
            for cfile in compiled_files:
                vpath = cfile[0]
                dst = cfile[1]
                vpath_complete_map[vpath] = dst
        else:
            # copy from source
            dst = os.path.join(dst_path, vpath.decode('utf-8'))
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src_path, dst)
            vpath_complete_map[vpath] = dst

    def build_dir(self, vfs: VfsBase, src_path: str, dst_path: str):
        # find all changed src files
        src_files = {}

        if isinstance(src_path, bytes):
            src_path = src_path.decode('utf-8')
        if isinstance(dst_path, bytes):
            dst_path = dst_path.decode('utf-8')

        wl = [src_path]
        while len(wl) > 0:
            cpath = wl.pop(0)
            print('Process: {}'.format(cpath))
            if os.path.isdir(cpath):
                cdir = os.listdir(cpath)
                for entry in cdir:
                    wl.append(os.path.join(cpath, entry))
            elif os.path.isfile(cpath):
                file, ext = os.path.splitext(cpath)
                if ext == '.deca_sha1sum':
                    pass
                elif cpath.endswith('.DECA.FILE_LIST.txt'):
                    vpath = cpath[len(src_path):-len('.DECA.FILE_LIST.txt')].encode('ascii')
                    vpath = vpath.replace(b'\\', b'/')
                    src_files[vpath] = cpath
                elif cpath.endswith('.ddsc.dds'):
                    vpath = cpath[len(src_path):-len('.dds')].encode('ascii')
                    vpath = vpath.replace(b'\\', b'/')
                    src_files[vpath] = cpath
                elif cpath.find('DECA') >= 0:  # ignore other deca files
                    pass
                else:
                    vpath = cpath[len(src_path):].encode('ascii')
                    vpath = vpath.replace(b'\\', b'/')
                    src_files[vpath] = cpath

        # calculate dependencies
        pack_list = list(src_files.keys())
        depends = {}
        completed = set()
        while len(pack_list) > 0:
            vpath = pack_list.pop(0)
            if vpath not in completed:
                completed.add(vpath)
                depends[vpath] = depends.get(vpath, set())

                if vpath not in vfs.map_vpath_to_vfsnodes:
                    print('TODO: WARNING: FILE {} NOT HANDLED'.format(vpath))
                else:
                    vnodes = vfs.map_vpath_to_vfsnodes[vpath]
                    vnode: VfsNode
                    for vnode in vnodes:
                        pid = vnode.pid
                        if pid is not None:
                            pnode = vfs.table_vfsnode[pid]

                            if pnode.ftype == FTYPE_GDCBODY:
                                # handle case of gdcc files
                                pid = pnode.pid
                                pnode = vfs.table_vfsnode[pid]

                            if pnode.ftype != FTYPE_ARC and pnode.ftype != FTYPE_TAB:
                                if pnode.vpath is None:
                                    raise EDecaBuildError('MISSING VPATH FOR uid:{} hash:{:08X}, when packing {}'.format(
                                        pnode.uid, pnode.vhash, vnode.vpath))
                                else:
                                    depends[pnode.vpath] = depends.get(pnode.vpath, set()).union({vnode.vpath})
                                    pack_list.append(pnode.vpath)

        # pprint(depends, width=128)

        # copy src modified files to build directory
        vpaths_completed = {}
        while len(depends) > 0:
            any_change = False
            depends_keys = list(depends.keys())
            for vpath in depends_keys:
                if len(depends[vpath]) == 0:  # all sources ready?
                    any_change = True
                    depends.pop(vpath)
                    v: set
                    for k, v in depends.items():
                        v.discard(vpath)

                    fpath = src_files.get(vpath, None)

                    vnodes = vfs.map_vpath_to_vfsnodes[vpath]
                    self.build_node(
                        dst_path=dst_path,
                        src_path=fpath,
                        vnode=vnodes[0],
                        vfs=vfs,
                        vpath_complete_map=vpaths_completed)


            if not any_change and len(depends) > 0:
                print('BUILD FAILED: Infinite loop:')
                print('depends')
                pprint(depends)
                print('vpaths_completed')
                pprint(vpaths_completed)
                raise EDecaBuildError('BUILD FAILED\n' + pformat(depends_keys))

        print('BUILD SUCCESS:')
        for k, v in vpaths_completed.items():
            print(v)

    def build_src(self, vfs: VfsBase, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
