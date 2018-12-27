import os
import datetime
import pandas as pd
from deca.util import *
from deca.file import ArchiveFile
from deca.ff_types import *
from deca.ff_txt import load_json
from deca.ff_adf import load_adf
from deca.ff_aaf import extract_aaf
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_determine import determine_file_type
from deca.hash_jenkins import hash_little


class VfsNode:
    def __init__(self, uid=None, ftype=None, compressed = False, hashid=None, p_path=None, v_path=None, pid=None, level=0, index=None, offset=None, size_c=None, size_u=None, processed=False):
        self.uid = uid
        self.ftype = ftype
        self.is_compressed = compressed
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

    def file_type(self):
        if self.is_compressed:
            return self.ftype + '.z'
        else:
            return self.ftype

    def __str__(self):
        info = []
        if self.ftype is not None:
            info.append('ft:{}'.format(self.file_type()))
        if self.hashid is not None:
            info.append('h:{:08X}'.format(self.hashid))
        if self.v_path is not None:
            info.append('v:{}'.format(self.v_path))
        if self.p_path is not None:
            info.append('p:{}'.format(self.p_path))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)


def game_file_to_sortable_string(v):
    if v[0:4] == 'game':
        return 'game{:08}'.format(int(v[4:]))
    else:
        return v


class VfsStructure:
    def __init__(self, working_dir):
        self.working_dir = working_dir
        self.uid = 0
        self.table_vfsnode = [None]
        self.map_uid_to_vfsnode = {}  # TODO currently redundant, may always be
        self.map_hash_to_vpath = {}
        self.map_vpath_to_hash = {}
        self.hash_bad = {}
        self.hash_present = set()
        self.hash_missing = set()

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
        self.map_uid_to_vfsnode[node.uid] = node
        self.determine_ftype(node)
        return node

    def file_obj_from(self, node: VfsNode, mode='rb'):
        if node.ftype == FTYPE_TABARC:
            return open(node.p_path, mode)
        elif node.is_compressed:
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

    def determine_ftype(self, node: VfsNode):
        if node.ftype is None:
            node.is_compressed = False
            if node.offset is None:
                node.ftype = 'symlink'
            else:
                with self.file_obj_from(node) as f:
                    node.ftype = determine_file_type(f, node.size_c)

        if node.ftype is FTYPE_AAF:
            node.is_compressed = True
            with self.file_obj_from(node) as f:
                node.ftype = determine_file_type(f, node.size_u)

    def propose_vpaths(self, strings):
        found = 0
        with open(self.working_dir + 'found_vpaths.txt', 'a') as f:
            for s in strings:
                if isinstance(s, str):
                    s = s.encode('ascii', 'ignore')
                elif isinstance(s, bytes):
                    pass
                else:
                    self.trace('BAD STRING {}'.format(s))
                    continue
                hid = hash_little(s)
                if hid in self.hash_present:
                    if hid in self.map_hash_to_vpath:
                        if s != self.map_hash_to_vpath[hid]:
                            self.trace('HASH CONFLICT STRINGS: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], s))
                            self.hash_bad[hid] = (self.map_hash_to_vpath[hid], s)
                    else:
                        f.write('{:08X}\t{}\n'.format(hid, s))
                        self.map_hash_to_vpath[hid] = s
                        self.map_vpath_to_hash[s] = hid
                        found = found + 1
        return found

    def load_from_archives(self, archive_path, ver=3, debug=False):
        find_all_tab_arcs = False
        self.log('find all tab/arc files')
        input_files = []
        if find_all_tab_arcs:
            cats = os.listdir(archive_path)
        else:
            cats = ['initial', 'supplemental', 'optional']
        for cat in cats:
            fcat = archive_path + cat
            print(fcat)
            if os.path.isdir(fcat):
                fcat = fcat + '/'
                files = os.listdir(fcat)
                ifns = []
                for file in files:
                    if 'tab' == file[-3:]:
                        ifns.append(file[0:-4])
                ifns.sort(key=game_file_to_sortable_string)
                for ifn in ifns:
                    input_files.append((cat, ifn))

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

        self.log('Expand Archives')
        idx = 0
        while idx < len(self.table_vfsnode):
            # if idx % 10000 == 0:
            #     self.log('Processing {} of {}'.format(idx, len(self.table_vfsnode)))
            node = self.table_vfsnode[idx]
            if node is not None and not node.processed:
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
            idx = idx + 1

        self.log('HASH FROM ARC/TAB/SARC')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.hashid is not None:
                hid = node.hashid
                self.hash_present.add(hid)
                if node.v_path is not None:
                    if hid in self.map_hash_to_vpath:
                        if self.map_hash_to_vpath[hid] != node.v_path:
                            self.trace('HASH CONFLICT ARCHIVE: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.v_path))
                            self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.v_path)
                    else:
                        self.map_hash_to_vpath[hid] = node.v_path
                        self.map_vpath_to_hash[node.v_path] = hid
        self.log('HASH FROM ARC/TAB/SARC: found {} hashes, {} mapped'.format(len(self.hash_present), len(self.map_hash_to_vpath)))

        self.log('HASH FROM ADF: look for hashable strings in ADF files')
        adf_strings = set()
        adf_done = set()
        for idx in range(len(self.table_vfsnode)):
            # if idx % 10000 == 0:
            #     self.log('HASH FROM ADF: {} of {}'.format(idx, len(self.table_vfsnode)))
            node = self.table_vfsnode[idx]
            if node is not None and node.ftype == FTYPE_ADF and node.hashid not in adf_done:
                adf_done.add(node.hashid)
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)
                adf = load_adf(buffer)
                for sh in adf.table_stringhash:
                    adf_strings.add(sh.value)
                    remove_prefix = b'intermediate/'
                    if sh.value.find(remove_prefix) == 0:
                        adf_strings.add(sh.value[len(remove_prefix):])
        adf_found = self.propose_vpaths(adf_strings)
        self.log('HASH FROM ADF: From {} found {} hash mappings. Total ADFs {}'.format(len(adf_strings), adf_found, len(adf_done)))

        self.log('HASH FROM JSON: look for hashable strings in json files')
        json_strings = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.ftype == FTYPE_TXT:
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)
                json = load_json(buffer)
                # Parse {"0":[]. "1":[]}
                if isinstance(json, dict) and '0' in json and '1' in json:
                    for k, v in json.items():
                        for l in v:
                            json_strings.add(l)
        json_found = self.propose_vpaths(json_strings)
        self.log('HASH FROM JSON: From {} found {} hash mappings'.format(len(json_strings), json_found))

        self.log('HASH FROM TEXTURE FILE NAMES: add possible strings for all ddsc -> atx?')
        avtx_strings = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.ftype == FTYPE_AVTX and node.v_path is not None:
                file, ext = os.path.splitext(node.v_path)
                for exti in range(16):
                    avtx_strings.add(file + '.atx{}'.format(exti).encode('ascii'))
        avtx_found = self.propose_vpaths(avtx_strings)
        self.log('HASH FROM TEXTURE FILE NAMES: From {} found {} hash mappings'.format(len(avtx_strings), avtx_found))

        self.log('HASH FROM EXE: look for hashable strings in EXE strings from IDA')
        db = pd.read_csv('./resources/gz/all_strings.tsv', delimiter='\t')
        db_str = db['String']
        exe_found = self.propose_vpaths(db_str)
        self.log('HASH FROM EXE: From {} found {} hash mappings'.format(len(db_str), exe_found))

        # self.log('HASH FROM CUSTOM: look for hashable strings in resources/gz/strings.txt')
        # db = pd.read_csv('./resources/gz/strings.txt', delimiter='\t')
        # db_str = db['String']
        # custom_found = self.propose_vpaths(db_str)
        # self.log('HASH FROM CUSTOM: From {} found {} hash mappings'.format(len(db_str), custom_found))

        self.log('fill in v_paths')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None and node.hashid is not None and node.v_path is None:
                if node.hashid in self.map_hash_to_vpath:
                    node.v_path = self.map_hash_to_vpath[node.hashid]
                elif node.ftype == FTYPE_AAF:
                    pass  # AAF files are containers
                elif node.ftype == FTYPE_SARC:
                    pass  # SARC files are containers
                else:
                    self.hash_missing.add(node.hashid)

        self.log('hash_missing: {}'.format(len(self.hash_missing)))

        self.log('Extracting files of unknown type')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node is not None:
                dump = False
                dump = dump or node.ftype is None
                # dump = dump or (node.v_path is not None and node.v_path.find(b'characters/machines/dreadnought') >= 0)
                if dump and node.offset is not None:
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