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


class Builder:
    def __init__(self):
        pass

    def build_node(self, dst_path: str, vnode: VfsNode, vfs: VfsBase, src_map):
        if vnode.ftype == FTYPE_SARC:
            print('BUILD SARC {}'.format(vnode.vpath))

            # parse existing file
            sarc_file = FileSarc()
            with vfs.file_obj_from(vnode) as f:
                sarc_file.header_deserialize(f)

            src_files = [None] * len(sarc_file.entries)
            entry: EntrySarc
            for i, entry in enumerate(sarc_file.entries):
                if entry.vpath in src_map:
                    src_files[i] = src_map[entry.vpath]
                    entry.length = os.stat(src_files[i]).st_size

            # extract existing file
            fn_dst = os.path.join(dst_path, vnode.vpath.decode('utf-8'))
            pt, fn = os.path.split(fn_dst)
            os.makedirs(pt, exist_ok=True)

            with ArchiveFile(open(fn_dst, 'wb')) as fso:
                sarc_file.header_serialize(fso)

                for i, entry in enumerate(sarc_file.entries):
                    buf = None
                    if entry.is_symlink:
                        print('  SYMLINK {}'.format(entry.vpath))
                    elif src_files[i] is not None:
                        print('  INSERTING {} src file to new file'.format(entry.vpath))
                        with open(src_files[i], 'rb') as f:
                            buf = f.read(entry.length)
                    else:
                        print('  COPYING {} from old file to new file'.format(entry.vpath))
                        vn = vfs.map_vpath_to_vfsnodes[entry.vpath][0]
                        with vfs.file_obj_from(vn) as fsi:
                            buf = fsi.read(entry.length)

                    if buf is not None:
                        fso.seek(entry.offset)
                        fso.write(buf)

            return fn_dst
        else:
            raise EDecaBuildError('Cannot build {} : {}'.format(vnode.ftype, vnode.vpath))

    def build_dir(self, vfs: VfsBase, src_path: str, dst_path: str):
        # find all changed src files
        src_files = []

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
                if cpath.endswith('.DECA.FILE_LIST.txt'):
                    vpath = cpath[len(src_path):-len('.DECA.FILE_LIST.txt')].encode('ascii')
                    vpath = vpath.replace(b'\\', b'/')
                    src_files.append([vpath, cpath])
                else:
                    vpath = cpath[len(src_path):].encode('ascii')
                    vpath = vpath.replace(b'\\', b'/')
                    src_files.append([vpath, cpath])

        # copy src modified files to build directory
        vpaths_completed = {}
        pack_list = []
        for file in src_files:
            vpath: bytes = file[0]
            fpath: str = file[1]
            # print('vpath: {}, src: {}'.format(vpath, fpath))
            dst = os.path.join(dst_path, vpath.decode('utf-8'))
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)

            if fpath.find('REFERENCE_ONLY') >= 0:
                pass  # DO NOT USE THESE FILES
            elif fpath.find('DECA') >= 0:
                pass  # BUILD instruction file do not copy
            elif re.match(r'^.*\.ddsc$', fpath) or re.match(r'^.*\.hmddsc$', fpath) or re.match(r'^.*\.atx?$', fpath):
                pass  # DO NOT USE THESE FILES image builder should use .ddsc.dds
            elif fpath.endswith('.ddsc.dds'):
                vpath = vpath[0:-4]
                vnode = vfs.map_vpath_to_vfsnodes[vpath][0]

                # make ddsc.dds into ddsc and avtxs
                compiled_files = image_import(vfs, vnode, fpath, dst_path)
                for cfile in compiled_files:
                    vpath = cfile[0]
                    dst = cfile[1]
                    pack_list.append([vpath, dst])
                    vpaths_completed[vpath] = dst
            else:
                shutil.copy2(fpath, dst)
                pack_list.append([vpath, dst])
                vpaths_completed[vpath] = dst

        # calculate dependencies
        depends = {}
        while len(pack_list) > 0:
            file = pack_list.pop(0)
            # print(file)
            vpath = file[0]
            dst = file[1]

            if vpath not in vfs.map_vpath_to_vfsnodes:
                print('TODO: WARNING: FILE {} NOT HANDLED'.format(vpath))
            else:
                vnodes = vfs.map_vpath_to_vfsnodes[vpath]
                for vnode in vnodes:
                    vnode: VfsNode = vnode
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
                                pack_list.append([pnode.vpath, os.path.join(dst_path, pnode.vpath.decode('utf-8'))])

        # pprint(depends, width=128)

        any_changes = True
        vpaths_todo = set()

        while any_changes:
            any_changes = False
            vpaths_todo = set()

            for dep, srcs in depends.items():
                if dep in vpaths_completed:
                    pass  # this file is done
                else:
                    all_src_ready = True
                    for src in srcs:
                        if src not in vpaths_completed:
                            all_src_ready = False
                            break
                    if all_src_ready:
                        vnodes = vfs.map_vpath_to_vfsnodes[dep]
                        dst = self.build_node(dst_path, vnodes[0], vfs, vpaths_completed)
                        any_changes = True
                        vpaths_completed[dep] = dst
                    else:
                        vpaths_todo.add(dep)

        if len(vpaths_todo):
            print('BUILD FAILED: Not Completed:')
            pprint(vpaths_todo)
            raise EDecaBuildError('BUILD FAILED\n' + pformat(vpaths_todo))
        else:
            print('BUILD SUCCESS:')
            for k, v in vpaths_completed.items():
                print(v)

    def build_src(self, vfs: VfsBase, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
