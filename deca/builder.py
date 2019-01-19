from deca.ff_vfs import VfsStructure, VfsNode
from deca.ff_types import *
import os
import shutil
from pprint import pprint


class Builder:
    def __init__(self):
        pass

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

        # calculate dependcies
        depends = {}
        while len(pack_list) > 0:
            file = pack_list.pop(0)
            # print(file)
            vpath = file[0]
            dst = file[1]

            vnodes = vfs.map_vpath_to_vfsnodes[vpath]
            for vnode in vnodes:
                vnode: VfsNode = vnode
                pid = vnode.pid
                if pid is not None:
                    pnode = vfs.table_vfsnode[pid]
                    if pnode.ftype != FTYPE_ARC and pnode.ftype != FTYPE_TAB:
                        depends[pnode.v_path] = depends.get(pnode.v_path, set()).union({vnode.v_path})
                        pack_list.append([pnode.v_path, dst_path.encode('ascii') + pnode.v_path])

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
                        dst = os.path.join(dst_path, dep.decode('utf-8')).encode('ascii')
                        print('BUILD {}'.format(dep))
                        any_changes = True
                        vpaths_completed[dep] = dst
                    else:
                        vpaths_todo.add(dep)

        if len(vpaths_todo):
            print('BUILD FAILED: Not Completed:')
            pprint(vpaths_todo)
        else:
            print('BUILD SUCCESS: vpaths changed')
            for k, v in vpaths_completed.items():
                print(k,v)

    def build_src(self, vfs: VfsStructure, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
