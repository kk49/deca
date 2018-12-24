import os
import sys
from deca.util import *
from deca.file import ArchiveFile
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_determine import determine_file_type, FTYPE_TABARC, FTYPE_AAF, FTYPE_SARC
from deca.ff_vfs import VfsNode, file_obj_from
import pandas as pd
import copy

prefix_in = '/home/krys/prj/gz/archives_win64/'
prefix_out = './test/gz/'
ver = 3
debug = False

'''
--vfs-fs dropzone --vfs-archive patch_win64 --vfs-archive archives_win64 --vfs-fs .
'''

input_files = []
cats = os.listdir(prefix_in)
for cat in cats:
    fcat = prefix_in + cat
    print(fcat)
    if os.path.isdir(fcat):
        fcat = fcat + '/'
        files = os.listdir(fcat)
        for file in files:
            if 'tab' == file[-3:]:
                input_files.append((cat, file[0:-4]))

table_vfsnode = [None]
map_uid_vfsnode = {}
uid = 0

print('process all game tab / arc files')
for ta_file in input_files:
    inpath = prefix_in + ta_file[0] + '/' + ta_file[1]

    file_tab = inpath + '.tab'
    file_arc = inpath + '.arc'

    with ArchiveFile(open(file_tab, 'rb'), debug=debug) as f:
        if 3 == ver:
            tab_file = TabFileV3()
        elif 4 == ver:
            tab_file = TabFileV4()

        tab_file.deserialize(f)

        uid = uid + 1
        arc_node = VfsNode(uid=uid, ftype=FTYPE_TABARC, p_path=file_arc)
        table_vfsnode.append(arc_node)
        map_uid_vfsnode[uid] = arc_node

        for i in range(len(tab_file.file_table)):
            te = tab_file.file_table[i]
            uid = uid + 1
            node = VfsNode(uid=uid, hashid=te.hashname, pid=arc_node.uid, level=arc_node.level+1, index=i, offset=te.offset, size_c=te.size_c, size_u=te.size_u)
            table_vfsnode.append(node)
            map_uid_vfsnode[uid] = node

        arc_node.processed = True

print('determine first level file types, define nodes for AAF file contents')
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and not node.processed:
        with file_obj_from(table_vfsnode, node, prefix_out) as f:
            node.ftype = determine_file_type(f, node.size_c)
            if node.ftype == FTYPE_AAF:
                uid = uid + 1
                cnode = VfsNode(uid=uid, hashid=None, pid=node.uid, level=node.level+1, index=0, offset=0, size_c=node.size_u, size_u=node.size_u)
                table_vfsnode.append(cnode)
                map_uid_vfsnode[uid] = cnode
                node.processed = True

print('process first level compressed files, define nodes for SARC file contents')
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and not node.processed:
        with file_obj_from(table_vfsnode, node, prefix_out) as f:
            node.ftype = determine_file_type(f, node.size_c)
        if node.ftype == FTYPE_SARC:
            with ArchiveFile(file_obj_from(table_vfsnode, node, prefix_out)) as f:
                version = f.read_u32()
                magic = f.read(4)
                ver2 = f.read_u32()
                dir_block_len = f.read_u32()

                buf = f.read(dir_block_len)
                string_len = struct.unpack('I', buf[0:4])[0]
                strings = buf[4:(4 + string_len)]
                strings0 = copy.copy(strings)
                strings = strings.split(b'\00')
                if strings[-1] == '':
                    strings = strings[:-1]

                buf = buf[(4 + string_len):]

                fdir = []
                width = 20
                for i in range(len(strings)):
                    line = buf[(i * width):((i + 1) * width)]
                    if len(line) == width:
                        v = struct.unpack('IIIII', line)
                        v = [x for x in v]

                        string_offset = v[1]
                        offset = v[1]
                        length = v[2]
                        hashv = v[3]

                        if offset == 0:
                            offset = None  # sarc files with zero offset are not in file, but reference hash value

                        uid = uid + 1
                        cnode = VfsNode(uid=uid, hashid=hashv, pid=node.uid, level=node.level + 1, index=i, offset=offset, size_c=length, size_u=length, v_path=strings[i])
                        table_vfsnode.append(cnode)
                        map_uid_vfsnode[uid] = cnode

                        # print('str_off:{} offset:{} length:{} hash:{:08X} ?:{}'.format(*v), strings[i])

            node.processed = True

print('determine sarc contents file types, define nodes for sarc file contents')
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and not node.processed:
        if node.offset is None:
            # print('HASH REFERENCE ONLY: {:08X} : {}'.format(node.hashid, node.v_path))
            node.processed = True
            node.ftype = 'symlink'
        else:
            with file_obj_from(table_vfsnode, node, prefix_out) as f:
                node.ftype = determine_file_type(f, node.size_c)


print('determine hash to v_path')
map_hash_to_vpath = {}
map_vpath_to_hash = {}
hash_bad = {}
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and node.hashid is not None and node.v_path is not None:
        hid = node.hashid
        if hid in map_hash_to_vpath:
            if map_hash_to_vpath[hid] != node.v_path:
                print('HASH CONFLICT: {:08X}: {} != {}'.format(hid, map_hash_to_vpath[hid], node.v_path))
                hash_bad[hid] = (map_hash_to_vpath[hid], node.v_path)
        else:
            map_hash_to_vpath[hid] = node.v_path
            map_vpath_to_hash[node.v_path] = hid

print('fill in v_paths')
hash_missing = {}
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and node.hashid is not None and node.v_path is None:
        if node.hashid in map_hash_to_vpath:
            node.v_path = map_hash_to_vpath[node.hashid]
        else:
            hash_missing[node.hashid] = None

print('dump files that need more info')
for idx in range(len(table_vfsnode)):
    node = table_vfsnode[idx]
    if node is not None and node.ftype is None:
        with ArchiveFile(file_obj_from(table_vfsnode, node, prefix_out)) as f:
            if node.v_path is None:
                ofile = prefix_out + '__TEST__/{:08X}.dat'.format(node.hashid)
            else:
                ofile = prefix_out + '__TEST__/{}.{:08X}'.format(node.v_path.decode('utf-8'), node.hashid)

            ofiledir = os.path.dirname(ofile)
            os.makedirs(ofiledir, exist_ok=True)

            print('Unknown Type: {}'.format(ofile))
            with ArchiveFile(open(ofile, 'wb')) as fo:
                buf = f.read(node.size_c)
                fo.write(buf)


