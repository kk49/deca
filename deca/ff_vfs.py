import os
import datetime
import pandas as pd
from deca.util import *
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_txt import load_json
from deca.ff_adf import load_adf
from deca.ff_aaf import extract_aaf
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_sarc import FileSarc
from deca.ff_determine import determine_file_type_and_size
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

    def is_valid(self):
        return self.uid is not None and self.uid != 0

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
        self.table_vfsnode = [VfsNode()]
        self.map_uid_to_vfsnode = {}  # TODO currently redundant, may always be
        self.map_hash_to_vpath = {}
        self.map_vpath_to_hash = {}
        self.map_vpath_to_vfsnodes = {}
        self.hash_bad = {}
        self.hash_present = set()
        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.map_name_usage = {}
        self.map_shash_usage = {}

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
        if node.ftype == FTYPE_ARC:
            return open(node.p_path, mode)
        elif node.ftype == FTYPE_TAB:
            return self.file_obj_from(self.table_vfsnode[node.pid])
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
            pf = SubsetFile(pf, node.size_u)
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
                    node.ftype, node.size_u = determine_file_type_and_size(f, node.size_c)

        if node.ftype is FTYPE_AAF:
            node.is_compressed = True
            with self.file_obj_from(node) as f:
                node.ftype, node.size_u = determine_file_type_and_size(f, node.size_u)

    def propose_vpaths(self, strings, dump_found_paths=False):
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

                ss = [s, s.replace(b'/', b'\\')]

                for s in ss:
                    hid = hash_little(s)
                    if hid in self.hash_present:
                        if hid in self.map_hash_to_vpath:
                            if s != self.map_hash_to_vpath[hid]:
                                self.trace('HASH CONFLICT STRINGS: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], s))
                                self.hash_bad[hid] = (self.map_hash_to_vpath[hid], s)
                        else:
                            if dump_found_paths:
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
            file_arc = inpath + '.arc'
            self.node_add(VfsNode(ftype=FTYPE_ARC, p_path=file_arc))

        any_change = True
        n_nodes = 0
        phase_id = 0
        while any_change:
            phase_id = phase_id + 1
            self.log('Expand Archives Phase {}: Begin'.format(phase_id))

            any_change = False
            idx = n_nodes  # start after last processed node
            n_nodes = len(self.table_vfsnode)  # only process this level of nodes
            while idx < n_nodes:
                # if idx % 10000 == 0:
                #     self.log('Processing {} of {}'.format(idx, len(self.table_vfsnode)))
                node = self.table_vfsnode[idx]
                if node.is_valid() and not node.processed:
                    if node.ftype == FTYPE_ARC:
                        node.processed = True
                        any_change = True
                        tab_path = os.path.splitext(node.p_path)
                        tab_path = tab_path[0] + '.tab'
                        self.node_add(VfsNode(ftype=FTYPE_TAB, p_path=tab_path, pid=node.uid, level=node.level))
                    elif node.ftype == FTYPE_TAB:
                        node.processed = True
                        any_change = True
                        with ArchiveFile(open(node.p_path, 'rb'), debug=debug) as f:
                            if 3 == ver:
                                tab_file = TabFileV3()
                            elif 4 == ver:
                                tab_file = TabFileV4()

                            tab_file.deserialize(f)

                            for i in range(len(tab_file.file_table)):
                                te = tab_file.file_table[i]
                                self.node_add(VfsNode(
                                    hashid=te.hashname,
                                    pid=node.uid,
                                    level=node.level + 1,
                                    index=i,
                                    offset=te.offset,
                                    size_c=te.size_c,
                                    size_u=te.size_u))
                    elif node.ftype == FTYPE_SARC:
                        node.processed = True
                        any_change = True
                        sarc_file = FileSarc()
                        sarc_file.deserialize(self.file_obj_from(node))

                        for se in sarc_file.entries:
                            offset = se.offset
                            if offset == 0:
                                offset = None  # sarc files with zero offset are not in file, but reference hash value
                            self.node_add(VfsNode(
                                hashid=se.shash, pid=node.uid, level=node.level + 1, index=se.index,
                                offset=offset, size_c=se.length, size_u=se.length, v_path=se.v_path))

                idx = idx + 1
            self.log('Expand Archives Phase {}: End'.format(phase_id))

        self.log('HASH FROM ARC/TAB/SARC')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.hashid is not None:
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
            if node.is_valid() and node.ftype == FTYPE_ADF and node.hashid not in adf_done:
                adf_done.add(node.hashid)
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)
                adf = load_adf(buffer)
                for sh in adf.table_stringhash:
                    adf_strings.add(sh.value)
                    remove_prefix = b'intermediate/'
                    if sh.value.find(remove_prefix) == 0:
                        adf_strings.add(sh.value[len(remove_prefix):])

                for sh in adf.table_name:
                    s = sh[1]
                    st = self.map_name_usage.get(s, set())
                    st.add(node)
                    self.map_name_usage[s] = st

                for sh in adf.table_stringhash:
                    s = sh.value
                    st = self.map_shash_usage.get(s, set())
                    st.add(node)
                    self.map_shash_usage[s] = st

        adf_found = self.propose_vpaths(adf_strings)
        self.log('HASH FROM ADF: From {} found {} hash mappings. Total ADFs {}'.format(len(adf_strings), adf_found, len(adf_done)))

        self.log('HASH FROM JSON: look for hashable strings in json files')
        json_strings = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_TXT:
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

        self.log('HASH FROM MDIC FILE NAMES: add possible strings for all {fl,nl}.mdic -> {nl,fl}.mdic')
        mdic_strings = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_ADF and node.v_path is not None:
                file, ext = os.path.splitext(node.v_path)
                if ext == b'.mdic':
                    file2, ext2 = os.path.splitext(file)
                    if ext2 == b'.nl':
                        mdic_strings.add(file2 + b'.fl.mdic')
                        mdic_strings.add(file2 + b'.fl')
                        mdic_strings.add(file2 + b'.nl')
                    elif ext2 == b'.fl':
                        mdic_strings.add(file2 + b'.nl.mdic')
                        mdic_strings.add(file2 + b'.nl')
                        mdic_strings.add(file2 + b'.fl')
        mdic_found = self.propose_vpaths(mdic_strings)
        self.log('HASH FROM MDIC FILE NAMES: From {} found {} hash mappings'.format(len(mdic_strings), mdic_found))

        self.log('HASH FROM EXE: look for hashable strings in EXE strings from IDA')
        db = pd.read_csv('./resources/gz/all_strings.tsv', delimiter='\t')
        db_str = db['String']
        exe_found = self.propose_vpaths(db_str)
        self.log('HASH FROM EXE: From {} found {} hash mappings'.format(len(db_str), exe_found))

        self.log('HASH FROM CUSTOM: look for hashable strings in resources/gz/strings.txt')
        with open('./resources/gz/strings.txt') as f:
            custom_strings = f.readlines()
        custom_strings = [x.strip() for x in custom_strings]
        custom_found = self.propose_vpaths(custom_strings, dump_found_paths=True)
        self.log('HASH FROM CUSTOM: From {} found {} hash mappings'.format(len(custom_strings), custom_found))

        self.log('HASH FROM CUSTOM: look for hashable strings in resources/gz/strings.0.txt')
        with open('./resources/gz/strings.0.txt') as f:
            custom_strings = f.readlines()
        custom_strings = [x.strip() for x in custom_strings]
        custom_found = self.propose_vpaths(custom_strings, dump_found_paths=True)
        self.log('HASH FROM CUSTOM: From {} found {} hash mappings'.format(len(custom_strings), custom_found))

        self.log('HASH FROM ATX? FILE NAMES: add possible strings for all atx? -> ddsc')
        ddsc_strings = set()
        for k, v in self.map_vpath_to_hash.items():
            file, ext = os.path.splitext(k.decode('utf-8'))
            if ext[0:4] == '.atx':
                ddsc_strings.add(file + '.ddsc')
        ddsc_found = self.propose_vpaths(ddsc_strings)
        self.log('HASH FROM ATX? FILE NAMES: From {} found {} hash mappings'.format(len(ddsc_strings), ddsc_found))

        self.log('HASH FROM DDSC FILE NAMES: add possible strings for all ddsc -> atx?')
        avtx_strings = set()
        for k, v in self.map_vpath_to_hash.items():
            file, ext = os.path.splitext(k.decode('utf-8'))
            if ext == '.ddsc':
                for exti in range(16):
                    avtx_strings.add(file + '.atx{}'.format(exti))
        avtx_found = self.propose_vpaths(avtx_strings)
        self.log('HASH FROM DDSC FILE NAMES: From {} found {} hash mappings'.format(len(avtx_strings), avtx_found))

        self.log('HASH FROM PAIR FILE NAMES: add possible strings for all [(epe,ee),(blo,bl)]')
        pair_exts = {
            '.epe': ['.ee'],
            '.ee': ['.epe'],
            '.blo': ['.bl'],
            '.bl': ['.blo'],
        }
        pair_strings = set()
        for k, v in self.map_vpath_to_hash.items():
            file, ext = os.path.splitext(k.decode('utf-8'))
            for e2 in pair_exts.get(ext, []):
                pair_strings.add(file + e2)
        pair_found = self.propose_vpaths(pair_strings)
        self.log('HASH FROM PAIR FILE NAMES: From {} found {} hash mappings'.format(len(pair_strings), pair_found))

        self.log('fill in v_paths, mark extensions identified files as ftype')
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.hashid is not None and node.v_path is None:
                if node.hashid in self.map_hash_to_vpath:
                    node.v_path = self.map_hash_to_vpath[node.hashid]

            if node.is_valid() and node.hashid is not None:
                if node.ftype not in {FTYPE_ARC, FTYPE_TAB}:
                    if node.hashid in self.map_hash_to_vpath:
                        self.hash_map_present.add(node.hashid)
                    else:
                        self.hash_map_missing.add(node.hashid)

            if node.is_valid() and node.v_path is not None:
                if os.path.splitext(node.v_path)[1][0:4] == b'.atx':
                    if node.ftype is not None:
                        raise Exception('ATX marked as non ATX: {}'.format(node.v_path))
                    node.ftype = FTYPE_ATX

                lst = self.map_vpath_to_vfsnodes.get(node.v_path, [])
                if len(lst) > 0 and lst[0].offset is None:  # Do not let symlink be first is list # TODO Sort by accessibility
                    lst = [node] + lst
                else:
                    lst.append(node)
                self.map_vpath_to_vfsnodes[node.v_path] = lst

        self.log('hashes: {}, mappings missing: {}, mappings present {}'.format(len(self.hash_present), len(self.hash_map_missing), len(self.hash_map_present)))

    def extract_node(self, node):
        if node.is_valid():
            if node.offset is not None:
                with ArchiveFile(self.file_obj_from(node)) as f:
                    if node.v_path is None:
                        ofile = self.working_dir + 'exported/{:08X}.dat'.format(node.hashid)
                    else:
                        # ofile = self.working_dir + 'exported/{}.{:08X}'.format(node.v_path.decode('utf-8'), node.hashid)
                        ofile = self.working_dir + 'exported/{}'.format(node.v_path.decode('utf-8'))

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