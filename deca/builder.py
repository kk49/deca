from deca.ff_vfs import VfsStructure, VfsNode
from deca.ff_types import *
from deca.ff_sarc import FileSarc, EntrySarc
from deca.errors import *
from deca.file import ArchiveFile
import os
import shutil
from pprint import pprint, pformat
from copy import deepcopy


class Builder:
    def __init__(self):
        pass

    def build_node(self, dst_path: str, vnode: VfsNode, vfs: VfsStructure, src_map):
        if vnode.ftype == FTYPE_SARC:
            print('BUILD SARC {}'.format(vnode.vpath))

            # parse existing file
            sarc_old = FileSarc()
            f = vfs.file_obj_from(vnode)
            sarc_old.deserialize(f)

            sarc_new = deepcopy(sarc_old)

            data_write_pos = sarc_old.dir_block_len + 16  # 16 is the basic header length 4,b'SARC', 3, dir_block_len
            src_files = [None] * len(sarc_old.entries)
            for i in range(len(sarc_old.entries)):
                entry_old: EntrySarc = sarc_old.entries[i]
                entry_new: EntrySarc = sarc_new.entries[i]
                vpath = entry_old.vpath
                if entry_old.vpath in src_map:
                    src_files[i] = src_map[vpath]
                    sz = os.stat(src_files[i]).st_size
                else:
                    sz = entry_old.length

                entry_new.offset = data_write_pos
                entry_new.length = sz
                data_write_pos = data_write_pos + sz
                align = 4
                data_write_pos = (data_write_pos + align - 1) // align * align

            # extract existing file
            fn_dst = os.path.join(dst_path, vnode.vpath.decode('utf-8'))
            # fn = vfs.extract_node(vnode, dst_path, do_sha1sum=False, allow_overwrite=True)

            # modify extracted existing file by overwriting offset to file entry to zero, telling the engine that it is
            # a symbolic link, and should be loaded elsewhere, preferably directly
            pt, fn = os.path.split(fn_dst)
            os.makedirs(pt, exist_ok=True)
            with ArchiveFile(open(fn_dst, 'wb')) as fso:
                with ArchiveFile(vfs.file_obj_from(vnode, 'rb')) as fsi:
                    buf = fsi.read(sarc_old.dir_block_len + 16)
                    fso.write(buf)

                    for i in range(len(sarc_old.entries)):
                        entry_old: EntrySarc = sarc_old.entries[i]
                        entry_new: EntrySarc = sarc_new.entries[i]
                        if src_files[i] is None:
                            print('  COPYING {} from old file to new file'.format(entry_old.vpath))
                            fsi.seek(entry_old.offset)
                            buf = fsi.read(entry_old.length)
                        else:
                            print('  INSERTING {} src file to new file'.format(entry_old.vpath))
                            with open(src_files[i].decode('utf-8'), 'rb') as f:
                                buf = f.read(entry_new.length)

                        fso.seek(entry_new.META_entry_offset_ptr)
                        fso.write_u32(entry_new.offset)
                        fso.seek(entry_new.META_entry_size_ptr)
                        fso.write_u32(entry_new.length)
                        fso.seek(entry_new.offset)
                        fso.write(buf)

            return fn_dst.encode('ascii')
        else:
            raise EDecaBuildError('Cannot build {} : {}'.format(vnode.ftype, vnode.vpath))

    def build_dir(self, vfs: VfsStructure, src_path: str, dst_path: str):
        # find all changed src files
        src_files = []

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
                else:
                    src_files.append([cpath[len(src_path):], cpath])

        # copy src modified files to build directory
        vpaths_completed = {}
        pack_list = []
        for file in src_files:
            vpath = file[0]
            src = file[1]
            dst = os.path.join(dst_path, vpath)
            dstdir = os.path.dirname(dst)
            os.makedirs(dstdir, exist_ok=True)
            shutil.copy2(src, dst)
            pack_list.append([vpath.encode('ascii'), dst.encode('ascii')])
            vpaths_completed[vpath.encode('ascii')] = dst.encode('ascii')

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
                                pack_list.append([pnode.vpath, dst_path.encode('ascii') + pnode.vpath])

        # pprint(depends, width=128)

        any_changes = True
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
                print(v.decode('utf-8'))

    def build_src(self, vfs: VfsStructure, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
