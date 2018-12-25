import os
import datetime
from deca.util import *
from deca.file import ArchiveFile
from deca.ff_types import *
from deca.ff_aaf import extract_aaf
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_determine import determine_file_type


class VfsNode:
    def __init__(self, uid=None, ftype=None, hashid=None, p_path=None, v_path=None, pid=None, level=0, index=None, offset=None, size_c=None, size_u=None, processed=False):
        self.uid = uid
        self.ftype = ftype
        self.hashid = hashid
        self.p_path = p_path
        self.v_path = v_path
        self.pid = pid
        self.level = level
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size
        self.processed = processed

    def __str__(self):
        info = []
        if self.ftype is not None:
            info.append('ft:{}'.format(self.ftype))
        if self.hashid is not None:
            info.append('h:{:08X}'.format(self.hashid))
        if self.v_path is not None:
            info.append('v:{}'.format(self.v_path))
        if self.p_path is not None:
            info.append('p:{}'.format(self.p_path))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)


class VfsStructure:
    def __init__(self, working_dir):
        self.uid = 0
        self.table_vfsnode = [None]
        self.map_uid_vfsnode = {}
        self.working_dir = working_dir
        self.map_hash_to_vpath = {}
        self.map_vpath_to_hash = {}
        self.hash_bad = {}
        self.hashs = set()

    def log_base(self, level, s):
        with open(self.working_dir + 'log.txt', 'a') as f:
            msg = '{}: {}'.format(datetime.datetime.now(), s)
            f.write(msg + '\n')
            if level <= 0:
                print(msg)

    def log(self, s):
        self.log_base(0, s)

    def trace(self, s):
        self.log_base(1, s)

    def node_add(self, node: VfsNode):
        self.uid = self.uid + 1
        node.uid = self.uid
        self.table_vfsnode.append(node)
        self.map_uid_vfsnode[node.uid] = node
        return node

    def file_obj_from(self, node: VfsNode, mode='rb'):
        if node.ftype == FTYPE_TABARC:
            return open(node.p_path, mode)
        elif node.ftype == FTYPE_AAF:
            cache_dir = self.working_dir + '__CACHE__/'
            os.makedirs(cache_dir, exist_ok=True)
            file_name = cache_dir + '{:08X}.dat'.format(node.hashid)
            if not os.path.isfile(file_name):
                pnode = self.table_vfsnode[node.pid]
                with ArchiveFile(self.file_obj_from(pnode, mode)) as pf:
                    pf.seek(node.offset)
                    extract_aaf(pf, file_name)
            return open(file_name, mode)
        elif node.pid is not None:
            pnode = self.table_vfsnode[node.pid]
            pf = self.file_obj_from(pnode, mode)
            pf.seek(node.offset)
            return pf
        else:
            raise Exception('NOT IMPLEMENTED: DEFAULT')

    def load_from_archives(self, archive_path, ver=3, debug=False):
        self.log('find all tab/arc files')
        input_files = []
        cats = os.listdir(archive_path)
        for cat in cats:
            fcat = archive_path + cat
            print(fcat)
            if os.path.isdir(fcat):
                fcat = fcat + '/'
                files = os.listdir(fcat)
                for file in files:
                    if 'tab' == file[-3:]:
                        input_files.append((cat, file[0:-4]))

        self.log('process all game tab / arc files')
        for ta_file in input_files:
            inpath = archive_path + ta_file[0] + '/' + ta_file[1]

            file_tab = inpath + '.tab'
            file_arc = inpath + '.arc'

            with ArchiveFile(open(file_tab, 'rb'), debug=debug) as f:
                if 3 == ver:
                    tab_file = TabFileV3()
                elif 4 == ver:
                    tab_file = TabFileV4()

                tab_file.deserialize(f)

                arc_node = self.node_add(VfsNode(ftype=FTYPE_TABARC, p_path=file_arc))

                for i in range(len(tab_file.file_table)):
                    te = tab_file.file_table[i]
                    node = self.node_add(VfsNode(
                        hashid=te.hashname,
                        pid=arc_node.uid,
                        level=arc_node.level + 1,
                        index=i,
                        offset=te.offset,
                        size_c=te.size_c,
                        size_u=te.size_u))

                arc_node.processed = True

        self.log('determine first level file types, define nodes for AAF file contents')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and not node.processed:
                with self.file_obj_from(node) as f:
                    node.ftype = determine_file_type(f, node.size_c)
                    if node.ftype == FTYPE_AAF:
                        cnode = self.node_add(VfsNode(
                            hashid=None,
                            pid=node.uid,
                            level=node.level + 1,
                            index=0,
                            offset=0,
                            size_c=node.size_u,
                            size_u=node.size_u))
                        node.processed = True

        self.log('process first level compressed files, define nodes for SARC file contents')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and not node.processed:
                with self.file_obj_from(node) as f:
                    node.ftype = determine_file_type(f, node.size_c)
                if node.ftype == FTYPE_SARC:
                    with ArchiveFile(self.file_obj_from(node)) as f:
                        version = f.read_u32()
                        magic = f.read(4)
                        ver2 = f.read_u32()
                        dir_block_len = f.read_u32()

                        buf = f.read(dir_block_len)
                        string_len = struct.unpack('I', buf[0:4])[0]
                        strings = buf[4:(4 + string_len)]
                        strings0 = strings
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

                                cnode = self.node_add(VfsNode(
                                    hashid=hashv, pid=node.uid, level=node.level + 1, index=i,
                                    offset=offset, size_c=length, size_u=length, v_path=strings[i]))

                                # print('str_off:{} offset:{} length:{} hash:{:08X} ?:{}'.format(*v), strings[i])

                    node.processed = True

        self.log('determine sarc contents file types, define nodes for sarc file contents')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and not node.processed:
                if node.offset is None:
                    # print('HASH REFERENCE ONLY: {:08X} : {}'.format(node.hashid, node.v_path))
                    node.processed = True
                    node.ftype = 'symlink'
                else:
                    with self.file_obj_from(node) as f:
                        node.ftype = determine_file_type(f, node.size_c)

        self.log('determine hash to v_path')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.hashid is not None:
                hid = node.hashid
                self.hashs.add(hid)
                if node.v_path is not None:
                    if hid in self.map_hash_to_vpath:
                        if self.map_hash_to_vpath[hid] != node.v_path:
                            self.trace('HASH CONFLICT: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.v_path))
                            self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.v_path)
                    else:
                        self.map_hash_to_vpath[hid] = node.v_path
                        self.map_vpath_to_hash[node.v_path] = hid

        self.log('fill in v_paths')
        hash_missing = {}
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.hashid is not None and node.v_path is None:
                if node.hashid in self.map_hash_to_vpath:
                    node.v_path = self.map_hash_to_vpath[node.hashid]
                else:
                    hash_missing[node.hashid] = None

        self.log('dump files that need more info')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.ftype is None:
                with ArchiveFile(self.file_obj_from(node)) as f:
                    if node.v_path is None:
                        ofile = self.working_dir + '__TEST__/{:08X}.dat'.format(node.hashid)
                    else:
                        ofile = self.working_dir + '__TEST__/{}.{:08X}'.format(node.v_path.decode('utf-8'), node.hashid)

                    ofiledir = os.path.dirname(ofile)
                    os.makedirs(ofiledir, exist_ok=True)

                    self.trace('Unknown Type: {}'.format(ofile))
                    with ArchiveFile(open(ofile, 'wb')) as fo:
                        buf = f.read(node.size_c)
                        fo.write(buf)



'''
--vfs-fs dropzone --vfs-archive patch_win64 --vfs-archive archives_win64 --vfs-fs .
'''

'''
tab/arc - file archive {hash, file}
aaf - compressed single file
sarc - file archive: {filename, hash, file}
avtx - directx image archives can contain multiple MIP levels
headerless-avtx - directx image archives with no header probably connected to avtx files can contain multiple MIP levels
adf - typed files with objects/type/...
'''

'''
VfsTable

uid : u64
ftype : u32
hashid : u32
p_path : str
v_path : str
pid : u64
index : u64  # index in parent
offset : u64 # offset in parent
size_c : u64 # compressed size in client
size_u : u64 # extracted size

VfsHashToNameMap
VfsNameToHashMap
'''