from deca.db_core import VfsDatabase, VfsNode
from deca.ff_types import *
from deca.ff_sarc import FileSarc, EntrySarc
from deca.ff_avtx import image_import
from deca.errors import *
from deca.file import ArchiveFile
import os
import shutil
import re
from pprint import pprint, pformat
from typing import Union, List


class Builder:
    def __init__(self):
        pass

    def build_node_sarc(
            self,
            dst_path: str,
            src_path: Union[None, str],
            vnode: VfsNode,
            vfs: VfsDatabase,
            vpath_complete_map,
            symlink_changed_file,
    ):
        assert(vnode.file_type == FTYPE_SARC)

        v_path = vnode.v_path
        print('BUILD SARC {}'.format(vnode.v_path))

        # parse existing file
        sarc_file = FileSarc()
        with vfs.file_obj_from(vnode) as f:
            sarc_file.header_deserialize(f)

        if src_path is not None:
            if src_path.find('DECA.FILE_LIST') >= 0:
                with open(src_path, 'r') as f:
                    src_lines = f.readlines()
                callex = re.compile(r'^([A-Za-z]*[.A-Za-z]*)\(([^)]*)\);$')
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
                    v_path = None
                    if mr is not None:
                        v_path = mr.group(1).encode('ascii')

                    if cmd == 'sarc.clear':
                        sarc_file.entries.clear()
                    elif cmd in {'sarc.add', 'sarc.symlink'}:
                        # Check to make sure entry does not exist
                        for entry in sarc_file.entries:
                            if entry.v_path == v_path:
                                # raise EDecaBuildError(
                                #     'BUILD ERROR: {}: Tried to re-add v_path: {}'.format(
                                #         src_context, v_path.decode('UTF-8')))
                                print('BUILD WARNING: Do not do this unless you are Ciprianno: {}: Tried to re-add v_path: {}'.format(src_context, v_path.decode('UTF-8')))

                        # Add to end
                        entry = EntrySarc(v_path=v_path)
                        entry.is_symlink = cmd == 'sarc.symlink'
                        src_node = vfs.nodes_where_match(v_path=v_path)
                        if not src_node:
                            raise EDecaBuildError(
                                'BUILD ERROR: {}: v_path does not exist in database: {}'.format(
                                    src_context, v_path.decode('UTF-8')))
                        src_node = src_node[0]
                        entry.length = src_node.size_u
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
            if entry.v_path in vpath_complete_map:
                src_file = vpath_complete_map[entry.v_path]
                src_files[i] = src_file
                entry.length = os.stat(src_file).st_size
                if symlink_changed_file:
                    entry.offset = 0
                    entry.is_symlink = True

        # extract existing file
        fn_dst = os.path.join(dst_path, vnode.v_path.decode('utf-8'))
        pt, fn = os.path.split(fn_dst)
        os.makedirs(pt, exist_ok=True)

        with ArchiveFile(open(fn_dst, 'wb')) as fso:
            sarc_file.header_serialize(fso)

            for i, entry in enumerate(sarc_file.entries):
                buf = None
                src_file = src_files[i]
                if entry.is_symlink:
                    print('  SYMLINK {}'.format(entry.v_path))
                    pass
                elif src_file is not None:
                    print('  INSERTING {} src file to new file'.format(entry.v_path))
                    with open(src_file, 'rb') as f:
                        buf = f.read(entry.length)
                else:
                    print('  COPYING {} from old file to new file'.format(entry.v_path))
                    vn = vfs.nodes_where_match(v_path=entry.v_path)[0]
                    with vfs.file_obj_from(vn) as fsi:
                        buf = fsi.read(entry.length)

                if buf is not None:
                    fso.seek(entry.offset)
                    fso.write(buf)

        vpath_complete_map[v_path] = fn_dst

    def build_node(
            self,
            dst_path: str,
            src_path: Union[None, str],
            vnode: VfsNode,
            vfs: VfsDatabase,
            vpath_complete_map,
            symlink_changed_file,
            do_not_build_archive,
    ):
        print(f'build_node: {dst_path} | {src_path} | {vnode.file_type} | {vnode.v_path}')

        v_path = vnode.v_path

        if src_path is None:
            src_file = None
        else:
            _, src_file = os.path.split(src_path)

        if vnode.file_type == FTYPE_SARC:
            if not do_not_build_archive:
                self.build_node_sarc(dst_path, src_path, vnode, vfs, vpath_complete_map, symlink_changed_file)
        elif src_path is None:
            pass  # no source path,
        elif src_file.find('DECA') >= 0:
            pass  # BUILD file(s) do not copy
        # elif re.match(r'^.*\.ddsc$', src_path) or \
        #         re.match(r'^.*\.hmddsc$', src_path) or \
        #         re.match(r'^.*\.atx?$', src_path):
        #     pass  # DO NOT USE THESE FILES image builder should use .ddsc.dds
        elif src_file.endswith('.ddsc.dds'):
            # Build texture
            vnode = vfs.nodes_where_match(v_path=v_path)[0]

            # make ddsc.dds into ddsc and avtxs
            compiled_files = image_import(vfs, vnode, src_path, dst_path)
            for cfile in compiled_files:
                v_path = cfile[0]
                dst = cfile[1]
                vpath_complete_map[v_path] = dst
        else:
            # copy from source
            dst = os.path.join(dst_path, v_path.decode('utf-8'))
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src_path, dst)
            vpath_complete_map[v_path] = dst

    def build_dir(
            self,
            vfs: VfsDatabase,
            src_path: str,
            dst_path: str,
            subset=None,
            symlink_changed_file=False,
            do_not_build_archive=False,
    ):
        print(f'build_node: {dst_path} | {src_path}')

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
                _, file = os.path.split(cpath)
                _, ext = os.path.splitext(file)
                if ext == '.deca_sha1sum':
                    pass
                elif file.endswith('.DECA.FILE_LIST.txt'):
                    v_path = cpath[len(src_path):-len('.DECA.FILE_LIST.txt')].encode('ascii')
                    v_path = v_path.replace(b'\\', b'/')
                    src_files[v_path] = cpath
                    print('DEPEND: DECA.FILE_LIST.txt: {} = {}'.format(v_path, cpath))
                elif file.endswith('.ddsc.dds'):
                    v_path = cpath[len(src_path):-len('.dds')].encode('ascii')
                    v_path = v_path.replace(b'\\', b'/')
                    src_files[v_path] = cpath
                    print('DEPEND: ddsc.dds: {} = {}'.format(v_path, cpath))
                elif file.find('DECA') >= 0:  # ignore other deca files
                    pass
                else:
                    v_path = cpath[len(src_path):].encode('ascii')
                    v_path = v_path.replace(b'\\', b'/')
                    src_files[v_path] = cpath
                    print('DEPEND: default: {} = {}'.format(v_path, cpath))

        # calculate dependencies
        pack_list = list(src_files.keys())
        depends = {}
        completed = set()
        while len(pack_list) > 0:
            v_path = pack_list.pop(0)
            print(f'PACKING: {v_path}')

            if v_path not in completed:
                print(f'COMPLETING: {v_path}')

                completed.add(v_path)
                depends[v_path] = depends.get(v_path, set())

                vnodes = vfs.nodes_where_match(v_path=v_path)

                if len(vnodes) == 0:
                    print('TODO: WARNING: FILE {} NOT HANDLED'.format(v_path))
                else:
                    vnode: VfsNode
                    for vnode in vnodes:
                        pid = vnode.pid
                        if pid is not None:
                            pnode: VfsNode = vfs.node_where_uid(pid)

                            if pnode.file_type == FTYPE_GDCBODY:
                                # handle case of gdcc files
                                pid = pnode.pid
                                pnode = vfs.node_where_uid(pid)

                            if pnode.file_type != FTYPE_ARC and pnode.file_type != FTYPE_TAB:
                                if pnode.file_type is None:
                                    raise EDecaBuildError(
                                        'MISSING VPATH FOR uid:{} hash:{:08X}, when packing {}'.format(
                                            pnode.uid, pnode.v_hash, vnode.v_path))
                                else:
                                    depends[pnode.v_path] = depends.get(pnode.v_path, set()).union({vnode.v_path})
                                    pack_list.append(pnode.v_path)

        # pprint(depends, width=128)

        if subset is not None:
            print('CALCULATING SUBSET')
            subset_vpaths = set()
            for uid in subset:
                vnode: VfsNode = vfs.node_where_uid(uid)
                subset_vpaths.add(vnode.v_path)

            depends_keep = set()
            for vpath in subset_vpaths:
                deps = depends.get(vpath, None)
                if deps is not None:
                    depends_keep.add(vpath)
                    depends_keep = depends_keep.union(deps)

            depends_remove = [k for k in depends.keys() if k not in depends_keep]

            for k in depends_remove:
                depends.pop(k, None)
        else:
            print('SKIPPING SUBSET')

        # copy src modified files to build directory
        vpaths_completed = {}
        while len(depends) > 0:
            any_change = False
            depends_keys = list(depends.keys())
            for v_path in depends_keys:
                print(f'check depends: {v_path} | {depends[v_path]}')
                if len(depends[v_path]) == 0:  # all sources ready?
                    any_change = True
                    depends.pop(v_path)
                    v: set
                    for k, v in depends.items():
                        v.discard(v_path)

                    fpath = src_files.get(v_path, None)
                    vnodes = vfs.nodes_where_match(v_path=v_path)

                    if len(vnodes) == 0:
                        raise EDecaBuildError('MISSING VPATH when building v_path={} using fpath={}'.format(
                            v_path, fpath))
                    else:
                        self.build_node(
                            dst_path=dst_path,
                            src_path=fpath,
                            vnode=vnodes[0],
                            vfs=vfs,
                            vpath_complete_map=vpaths_completed,
                            symlink_changed_file=symlink_changed_file,
                            do_not_build_archive=do_not_build_archive,
                        )

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

    def build_src(self, vfs: VfsDatabase, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
