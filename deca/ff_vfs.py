import os
import io
import datetime
import pandas as pd
from hashlib import sha1
from pprint import pprint
import multiprocessing

import deca.ff_rtpc
from deca.file import ArchiveFile, SubsetFile
from deca.ff_types import *
from deca.ff_txt import load_json
from deca.ff_adf import load_adf, AdfTypeMissing, GdcArchiveEntry
from deca.ff_rtpc import Rtpc
from deca.ff_aaf import extract_aaf
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_sarc import FileSarc
from deca.ff_determine import determine_file_type_and_size
from deca.hash_jenkins import hash_little


class VfsPathNode:
    def __init__(self, vpath):
        self.vpath = vpath
        self.vphash = None
        self.vfsnodes = []
        self.src = []  # [[SARC, vfsnode], [RTPC, vfsnode], [ADF, vfsnode], [GUESS], ]
        self.used_at_runtime = False
        self.possible_ftypes = set()


class VfsPathMap:
    def __init__(self, logger):
        self.nodes = {}
        self.logger = logger

    def log(self, s):
        if self.logger is not None:
            self.logger.log(s)

    def merge(self, other):
        for k, v in other.nodes.items():
            v2 = self.nodes.get(k, VfsPathNode(k))

            if v2.vphash is None:
                v2.vphash = v.vphash
            elif v.vphash is not None:
                if v.vphash != v2.vphash:
                    raise Exception('merge: {}: hash mismatch {} != {}'.format(k, v.vphash, v2.vphash))

            v2.vfsnodes = v2.vfsnodes + v.vfsnodes
            v2.src = v2.src + v.src
            v2.used_at_runtime = v2.used_at_runtime or v.used_at_runtime
            for kf in v.possible_ftypes:
                v2.possible_ftypes.add(kf)

            self.nodes[k] = v2

    def propose(self, vpath, src, used_at_runtime=False, vnode=None, possible_ftypes=None):
        '''
        Add proposed vpath to map
        :param vpath: string representing vpath
        :param src: currently a vaguely formated list of information about where the vpath came from # TODO
        :param used_at_runtime: bool that indicates if this usage is known to be used by the executable gotten from procmon
        :param vnode: include vnode if the vnode was explicitly labeled, like in a sarc
        :param possible_ftypes: None, Value, or [Value] of file types that are expect to be connected to vpath
        :return: VpatjInference object
        '''

        if isinstance(vpath, str):
            vpath = vpath.encode('ascii', 'ignore')
        elif isinstance(vpath, bytes):
            pass
        else:
            self.log('propose: BAD STRING {}'.format(vpath))
            return None

        vpath = vpath.replace(b'\\\\', b'/').replace(b'\\', b'/')

        if vpath in self.nodes:
            iv = self.nodes[vpath]
        else:
            iv = VfsPathNode(vpath)
            iv.vphash = hash_little(vpath)

        iv.used_at_runtime = iv.used_at_runtime or used_at_runtime

        if vnode is not None:
            if vnode.offset is None:
                iv.vfsnodes.append(vnode)
            else:
                iv.vfsnodes = [vnode] + iv.vfsnodes

        if src is not None:
            iv.src.append(src)

        if isinstance(possible_ftypes, list):
            for pf in possible_ftypes:
                iv.possible_ftypes.add(pf)
        elif possible_ftypes is not None:
            iv.possible_ftypes.add(possible_ftypes)

        self.nodes[vpath] = iv

        return iv


class VfsNode:
    def __init__(
            self, uid=None, ftype=None, compressed=False,
            hashid=None, p_path=None, v_path=None, pid=None, level=0, index=None, offset=None,
            size_c=None, size_u=None, processed=False, used_at_runtime=False, content_hash=None):
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
        self.used_at_runtime = used_at_runtime
        self.content_hash = content_hash

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

        # basic node tracking
        self.uid = 0
        self.table_vfsnode = [VfsNode()]
        self.map_uid_to_vfsnode = {}  # TODO currently redundant, may always be

        # tracking node hashs
        self.map_hash_to_vnodes = {}
        self.hash_present = set()

        # track info from ADFs
        self.map_name_usage = {}
        self.map_shash_usage = {}
        self.adf_missing_types = {}

        # track possible vpaths
        self.possible_vpath_map = VfsPathMap(self)

        # results from connecting vpaths to vfsnodes
        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

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

    def node_add(self, node: VfsNode):
        self.uid = self.uid + 1
        node.uid = self.uid

        self.table_vfsnode.append(node)
        self.map_uid_to_vfsnode[node.uid] = node
        self.determine_ftype(node)

        if node.is_valid():
            if node.hashid is not None:
                self.hash_present.add(node.hashid)
                vl = self.map_hash_to_vnodes.get(node.hashid, [])
                if node.offset is None:
                    vl.append(node)  # put symlinks at end
                else:
                    vl = [node] + vl  # put real files up front
                self.map_hash_to_vnodes[node.hashid] = vl

        return node

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
                        # here we add the tab file as a child of the ARC, a trick to make it work with our data model
                        node.processed = True
                        any_change = True
                        tab_path = os.path.splitext(node.p_path)
                        tab_path = tab_path[0] + '.tab'
                        cnode = VfsNode(ftype=FTYPE_TAB, p_path=tab_path, pid=node.uid, level=node.level)
                        self.node_add(cnode)
                    elif node.ftype == FTYPE_TAB:
                        node.processed = True
                        any_change = True
                        with ArchiveFile(open(node.p_path, 'rb'), debug=debug) as f:
                            if 3 == ver:
                                tab_file = TabFileV3()
                            elif 4 == ver:
                                tab_file = TabFileV4()
                            else:
                                raise NotImplementedError('Unknown TAB file version {}'.format(ver))

                            tab_file.deserialize(f)

                            for i in range(len(tab_file.file_table)):
                                te = tab_file.file_table[i]
                                cnode = VfsNode(
                                    hashid=te.hashname, pid=node.uid, level=node.level + 1, index=i,
                                    offset=te.offset, size_c=te.size_c, size_u=te.size_u)
                                self.node_add(cnode)

                    elif node.ftype == FTYPE_SARC:
                        node.processed = True
                        any_change = True
                        sarc_file = FileSarc()
                        sarc_file.deserialize(self.file_obj_from(node))

                        for se in sarc_file.entries:
                            offset = se.offset
                            if offset == 0:
                                offset = None  # sarc files with zero offset are not in file, but reference hash value
                            cnode = VfsNode(
                                hashid=se.shash, pid=node.uid, level=node.level + 1, index=se.index,
                                offset=offset, size_c=se.length, size_u=se.length, v_path=se.v_path)

                            self.node_add(cnode)
                            self.possible_vpath_map.propose(cnode.v_path, [FTYPE_SARC, node], vnode=cnode)

                    elif node.hashid == deca.hash_jenkins.hash_little(b'gdc/global.gdcc'):  # special case starting point for runtime
                        node.processed = True
                        any_change = True
                        with self.file_obj_from(node) as f:
                            buffer = f.read(node.size_u)
                        adf = load_adf(buffer)
                        for entry in adf.table_instance_values[0]:
                            if isinstance(entry, GdcArchiveEntry):
                                # self.log('GDCC: {:08X} {}'.format(entry.vpath_hash, entry.vpath))
                                cnode = VfsNode(
                                    hashid=entry.vpath_hash, pid=node.uid, level=node.level + 1, index=entry.index,
                                    offset=entry.offset, size_c=entry.size, size_u=entry.size, v_path=entry.vpath)
                                self.node_add(cnode)
                                self.possible_vpath_map.propose(cnode.v_path, [FTYPE_ADF, node], vnode=cnode)

                idx = idx + 1
            self.log('Expand Archives Phase {}: End'.format(phase_id))

        self.find_vpath_adf(self.possible_vpath_map)
        self.find_vpath_rtpc(self.possible_vpath_map)
        self.find_vpath_json(self.possible_vpath_map)
        self.find_vpath_exe(self.possible_vpath_map)
        self.find_vpath_procmon(self.possible_vpath_map)
        self.find_vpath_custom(self.possible_vpath_map)
        self.find_vpath_guess(self.possible_vpath_map)
        self.find_vpath_by_assoc(self.possible_vpath_map)

        self.process_vpaths()

        self.log('hashes: {}, mappings missing: {}, mappings present {}, mapping conflict {}'.format(
            len(self.hash_present),
            len(self.hash_map_missing),
            len(self.hash_map_present),
            len(self.hash_map_conflict)))

        for k, vs in self.adf_missing_types.items():
            for v in vs:
                vp = self.map_hash_to_vpath.get(v, b'')
                self.log('Missing Type {:08x} in {:08X} {}'.format(k, v, vp.decode('utf-8')))

    def process_vpaths(self):
        self.log('process_vpaths: Input count {}'.format(len(self.possible_vpath_map.nodes)))

        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

        found_vpaths = set()
        for vp in self.possible_vpath_map.nodes.values():
            vp: VfsPathNode = vp
            vpid = vp.vphash
            if vpid in self.map_hash_to_vnodes:
                vnodes = self.map_hash_to_vnodes[vpid]
                for vnode in vnodes:
                    vnode: VfsNode = vnode
                    if vnode.is_valid():
                        if vnode.v_path is None:
                            if len(vp.possible_ftypes) == 0 or vnode.ftype in vp.possible_ftypes:
                                self.log('vpath:add  {} {:08X} {} {} {}'.format(vp.vpath, vp.vphash, len(vp.src), vp.possible_ftypes, vnode.ftype))
                                vnode.v_path = vp.vpath
                                found_vpaths.add(vp.vpath)
                            else:
                                self.log('vpath:skip {} {:08X} {} {} {}'.format(vp.vpath, vp.vphash, len(vp.src), vp.possible_ftypes, vnode.ftype))

                        if vnode.v_path == vp.vpath and vp.used_at_runtime and not vnode.used_at_runtime:
                            # print('rnt', vp.vpath)
                            vnode.used_at_runtime = True
            else:
                self.log('vpath:miss {} {:08X} {} {}'.format(vp.vpath, vp.vphash, len(vp.src), vp.possible_ftypes))

        for vnode in self.table_vfsnode:
            vnode: VfsNode = vnode
            if vnode.is_valid():
                if vnode.hashid is not None:
                    vid = vnode.hashid
                    if vnode.v_path is None:
                        self.hash_map_missing.add(vid)
                    else:
                        self.hash_map_present.add(vid)
                        vpath = vnode.v_path
                        if vid in self.map_hash_to_vpath:
                            self.map_hash_to_vpath[vid].add(vpath)
                            if len(self.map_hash_to_vpath[vid]) > 1:
                                self.hash_map_conflict.add(vid)
                        else:
                            self.map_hash_to_vpath[vid] = {vpath}

                        vl = self.map_vpath_to_vfsnodes.get(vpath, [])
                        if vnode.offset is None:
                            vl = vl + [vnode]
                        else:
                            vl = [vnode] + vl
                        self.map_vpath_to_vfsnodes[vpath] = vl

        with open(self.working_dir + 'found_vpaths.txt', 'a') as f:
            for vp in found_vpaths:
                f.write('{}\n'.format(vp))

    #         for s in ss:
        #             hid = hash_little(s)
        #             if hid in self.hash_present:
        #                 if hid in self.map_hash_to_vpath:
        #                     if s != self.map_hash_to_vpath[hid]:
        #                         self.trace('HASH CONFLICT STRINGS: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], s))
        #                         self.hash_bad[hid] = (self.map_hash_to_vpath[hid], s)
        #                 else:
        #                     if dump_found_paths:
        #                         f.write('{:08X}\t{}\n'.format(hid, s))
        #                     self.map_hash_to_vpath[hid] = s
        #                     self.map_vpath_to_hash[s] = hid
        #                     found = found + 1
        #
        # self.log('fill in v_paths, mark extensions identified files as ftype')
        #
        # self.log('PROCESS BASELINE VNODE INFORMATION')
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.hashid is not None:
        #         hid = node.hashid
        #         if node.v_path is not None:
        #             if hid in self.map_hash_to_vpath:
        #                 if self.map_hash_to_vpath[hid] != node.v_path:
        #                     self.trace('HASH CONFLICT ARCHIVE: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.v_path))
        #                     self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.v_path)
        #             else:
        #                 self.map_hash_to_vpath[hid] = node.v_path
        #                 self.map_vpath_to_hash[node.v_path] = hid
        # self.log('PROCESS BASELINE VNODE INFORMATION: found {} hashes, {} mapped'.format(len(self.hash_present), len(self.map_hash_to_vpath)))
        #
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.hashid is not None and node.v_path is None:
        #         if node.hashid in self.map_hash_to_vpath:
        #             node.v_path = self.map_hash_to_vpath[node.hashid]
        #
        #     if node.is_valid() and node.hashid is not None:
        #         if node.ftype not in {FTYPE_ARC, FTYPE_TAB}:
        #             if node.hashid in self.map_hash_to_vpath:
        #                 self.hash_map_present.add(node.hashid)
        #             else:
        #                 self.hash_map_missing.add(node.hashid)
        #
        #     if node.is_valid() and node.v_path is not None:
        #         if os.path.splitext(node.v_path)[1][0:4] == b'.atx':
        #             if node.ftype is not None:
        #                 raise Exception('ATX marked as non ATX: {}'.format(node.v_path))
        #             node.ftype = FTYPE_ATX
        #
        #         lst = self.map_vpath_to_vfsnodes.get(node.v_path, [])
        #         if len(lst) > 0 and lst[0].offset is None:  # Do not let symlink be first is list # TODO Sort by accessibility
        #             lst = [node] + lst
        #         else:
        #             lst.append(node)
        #         self.map_vpath_to_vfsnodes[node.v_path] = lst

    def find_vpath_adf(self, vpath_map):
        self.log('PROCESS ADFs: find strings, propose terrain patches')
        indexes = []
        adf_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_ADF and node.hashid not in adf_done:
                adf_done.add(node.hashid)
                indexes.append(idx)

        nprocs = max(1, multiprocessing.cpu_count() // 2)  # assuming hyperthreading exists and slows down processing

        indexes2 = [indexes[v::nprocs] for v in range(0, nprocs)]

        q = multiprocessing.Queue()

        procs = []
        for idxs in indexes2:
            self.log('Create Process: ({},{},{}'.format(min(idxs), max(idxs), idxs[:8]))
            p = multiprocessing.Process(target=self.find_vpath_adf_core, args=(q, idxs,))
            self.log('Process: {}: Start'.format(p))
            p.start()
            procs.append(p)

        scount = 0
        for i in range(len(procs)):
            self.log('Waiting {} of {}'.format(i+1, len(procs)))
            vpath_map_work, adf_missing_types, map_name_usage, map_shash_usage = q.get()
            scount += len(vpath_map_work.nodes)

            vpath_map.merge(vpath_map_work)

            for k, v in adf_missing_types.items():
                self.adf_missing_types[k] = self.adf_missing_types.get(k, []) + v

            for k, v in map_name_usage.items():
                self.map_name_usage[k] = self.map_name_usage.get(k, set()).union(v)

            for k, v in map_shash_usage.items():
                self.map_shash_usage[k] = self.map_shash_usage.get(k, set()).union(v)

            self.log('Process Done {} of {}'.format(i + 1, len(procs)))

        for p in procs:
            self.log('Process: {}: Joining'.format(p))
            p.join()
            self.log('Process: {}: Joined'.format(p))

        self.log('PROCESS ADFs: Total ADFs: {}, Total Strings: {}'.format(len(adf_done), scount))

    def find_vpath_adf_core(self, q, indexs):
        vpath_map = VfsPathMap(self)
        adf_missing_types = {}
        map_name_usage = {}
        map_shash_usage = {}

        for idx in indexs:
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_ADF:
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)
                try:
                    adf = load_adf(buffer)
                    for sh in adf.table_stringhash:
                        vpath_map.propose(sh.value, [FTYPE_ADF, node])
                        remove_prefix = b'intermediate/'
                        if sh.value.find(remove_prefix) == 0:
                            vpath_map.propose(sh.value[len(remove_prefix):], [FTYPE_ADF, node])

                    for sh in adf.found_strings:
                        vpath_map.propose(sh, [FTYPE_ADF, node], False, None)
                        remove_prefix = b'intermediate/'
                        if sh.find(remove_prefix) == 0:
                            vpath_map.propose(sh[len(remove_prefix):], [FTYPE_ADF, node])

                    for sh in adf.table_name:
                        s = sh[1]
                        st = map_name_usage.get(s, set())
                        st.add(node)
                        map_name_usage[s] = st

                    for sh in adf.table_stringhash:
                        s = sh.value
                        st = map_shash_usage.get(s, set())
                        st.add(node)
                        map_shash_usage[s] = st

                    if len(adf.table_instance_values) > 0 and adf.table_instance_values[0] is not None and isinstance(
                            adf.table_instance_values[0], dict):
                        obj0 = adf.table_instance_values[0]

                        fns = []
                        # self name patch files
                        if 'PatchLod' in obj0 and 'PatchPositionX' in obj0 and 'PatchPositionZ' in obj0:
                            fn = 'terrain/hp/patches/patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                                obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                            fns.append(fn)

                        if adf.table_instance[0].name == b'environ':
                            fn = 'environment/weather/{}.environc'.format(obj0['Name'].decode('utf-8'))
                            fns.append(fn)
                            fn = 'environment/{}.environc'.format(obj0['Name'].decode('utf-8'))
                            fns.append(fn)

                        found_any = False
                        for fn in fns:
                            if node.hashid == hash_little(fn):
                                vpath_map.propose(fn, [FTYPE_ADF, node], possible_ftypes=FTYPE_ADF)
                                found_any = True

                        if len(fns) > 0 and not found_any:
                            self.log('COULD NOT MATCH GENERATED FILE NAME {:08X} {}'.format(node.hashid, fns[0]))

                except AdfTypeMissing as ae:
                    adf_missing_types[ae.hashid] = adf_missing_types.get(ae.hashid, []) + [node.hashid]
                    print('Missing Type {:08x} in {:08X} {} {}'.format(
                        ae.hashid, node.hashid, node.v_path, node.p_path))

        q.put([vpath_map, adf_missing_types, map_name_usage, map_shash_usage])

    def find_vpath_rtpc(self, vpath_map):
        self.log('PROCESS RTPCs: look for hashable strings in RTPC files')
        indexes = []
        rtpc_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_RTPC and node.hashid not in rtpc_done:
                rtpc_done.add(node.hashid)
                indexes.append(idx)

        nprocs = max(1, multiprocessing.cpu_count() // 2)  # assuming hyperthreading exists and slows down processing

        indexes2 = [indexes[v::nprocs] for v in range(0, nprocs)]

        q = multiprocessing.Queue()

        procs = []
        for idxs in indexes2:
            self.log('Create Process: ({},{},{}'.format(min(idxs), max(idxs), idxs[:8]))
            p = multiprocessing.Process(target=self.find_vpath_rtpc_core, args=(q, idxs,))
            self.log('Process: {}: Start'.format(p))
            p.start()
            procs.append(p)

        scount = 0
        for i in range(len(procs)):
            self.log('Waiting {} of {}'.format(i+1, len(procs)))
            vpath_map_work = q.get()
            scount += len(vpath_map_work.nodes)
            vpath_map.merge(vpath_map_work)
            self.log('Process Done {} of {}'.format(i+1, len(procs)))

        for p in procs:
            self.log('Process: {}: Joining'.format(p))
            p.join()
            self.log('Process: {}: Joined'.format(p))

        self.log('PROCESS RTPCs: Total RTPCs: {}, Total Strings: {}'.format(len(rtpc_done), scount))

    def find_vpath_rtpc_core(self, q, indexs):
        vpath_map = VfsPathMap(self)
        for idx in indexs:
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_RTPC:
                # try:
                with self.file_obj_from(node) as f:
                    buf = f.read(node.size_u)

                # with open('dump.dat', 'wb') as fo:
                #     fo.write(buf)

                rtpc = Rtpc()
                with io.BytesIO(buf) as f:
                    rtpc.deserialize(f)

                rnodelist = [rtpc.root_node]

                while len(rnodelist) > 0:
                    rnode = rnodelist.pop(0)

                    for c in rnode.child_table:
                        rnodelist.append(c)

                    for p in rnode.prop_table:
                        if p.type == deca.ff_rtpc.PropType.type_str.value:
                            s = p.data
                            vpath_map.propose(s, [FTYPE_RTPC, node])
                            fn, ext = os.path.splitext(s)
                            if ext == b'.tga':
                                vpath_map.propose(fn + b'.ddsc', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])
        q.put(vpath_map)

    def find_vpath_json(self, vpath_map):
        self.log('PROCESS JSONs: look for hashable strings in json files')
        json_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_TXT and node.hashid not in json_done:
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)

                json = load_json(buffer)
                if json is not None:
                    json_done.add(node.hashid)

                # Parse {"0":[]. "1":[]}
                if isinstance(json, dict) and '0' in json and '1' in json:
                    for k, v in json.items():
                        for l in v:
                            vpath_map.propose(l, [FTYPE_TXT, node])
        self.log('PROCESS JSONs: Total JSON files {}'.format(len(json_done)))

    def find_vpath_exe(self, vpath_map):
        self.log('STRINGS FROM EXE: look for hashable strings in EXE strings from IDA in ./resources/gz/all_strings.tsv')
        db = pd.read_csv('./resources/gz/all_strings.tsv', delimiter='\t')
        db_str = db['String']
        db_str = set(db_str)
        for s in db_str:
            vpath_map.propose(s, ['EXE', None])
        self.log('STRINGS FROM EXE: Found {} strings'.format(len(db_str)))

    def find_vpath_procmon(self, vpath_map):
        self.log('STRINGS FROM PROCMON: look for hashable strings in resources/gz/strings_procmon.txt')
        with open('./resources/gz/strings_procmon.txt') as f:
            custom_strings = f.readlines()
            custom_strings = set(custom_strings)
            for s in custom_strings:
                vpath_map.propose(s.strip(), ['PROCMON', None], used_at_runtime=True)
        self.log('STRINGS FROM HASH FROM PROCMON: Total {} strings'.format(len(custom_strings)))

    def find_vpath_custom(self, vpath_map):
        self.log('STRINGS FROM CUSTOM: look for hashable strings in resources/gz/strings.txt')
        with open('./resources/gz/strings.txt') as f:
            custom_strings = f.readlines()
            custom_strings = set(custom_strings)
            for s in custom_strings:
                vpath_map.propose(s.strip(), ['CUSTOM', None])
        self.log('STRINGS FROM CUSTOM: Total {} strings'.format(len(custom_strings)))

    def find_vpath_guess(self, vpath_map):
        self.log('STRINGS BY GUESSING: ...')
        guess_strings = {}
        guess_strings['textures/ui/map_reserve_0/world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
        guess_strings['textures/ui/map_reserve_1/world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
        guess_strings['settings/hp_settings/reserve_0.bin'] = FTYPE_RTPC
        guess_strings['settings/hp_settings/reserve_0.bl'] = FTYPE_SARC
        guess_strings['settings/hp_settings/reserve_1.bin'] = FTYPE_RTPC
        guess_strings['settings/hp_settings/reserve_1.bl'] = FTYPE_SARC
        for res_i in [0, 1]:
            for zoom_i in [1, 2, 3]:
                for index in range(500):
                    fn = 'textures/ui/map_reserve_{}/zoom{}/{}.ddsc'.format(res_i, zoom_i, index)
                    guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for i in range(64):
            fn = 'terrain/hp/horizonmap/horizon_{}.ddsc'.format(i)
            guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for i in range(64):
            for j in range(64):
                fn = 'ai/tiles/{:02d}_{:02d}.navmeshc'.format(i, j)
                guess_strings[fn] = FTYPE_TAG0

        prefixs = [
            'ui/character_creation_i',
            'ui/cutscene_ui_i',
            'ui/hud_i',
            'ui/intro_i',
            'ui/in_game_menu_background_i',
            'ui/in_game_menu_overlay_i',
            'ui/intro_i',
            'ui/inventory_screen_i',
            'ui/load_i',
            'ui/main_menu_i',
            'ui/overlay_i',
            'ui/player_downed_screen_i',
            'ui/profile_picker_i',
            'ui/reward_sequence_i',
            'ui/settings_i',
            'ui/skills_screen_i',
            'ui/team_screen_i',
            'ui/title_i',
        ]
        for prefix in prefixs:
            for i in range(255):
                fn = '{}{:x}.ddsc'.format(prefix, i)
                guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for i in range(255):
            fn = 'textures/ui/load/{}.ddsc'.format(i)
            guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for k, v in guess_strings.items():
            fn = k
            fn = fn.encode('ascii')
            vpath_map.propose(fn, ['GUESS', None], possible_ftypes=v)

        self.log('STRINGS BY GUESSING: Total {} guesses'.format(len(guess_strings)))

    def find_vpath_by_assoc(self, vpath_map):
        self.log('STRINGS BY FILE NAME ASSOCIATION: epe/ee, blo/bl/nl/fl/nl.mdic/fl.mdic, mesh*/model*, avtx/atx?]')
        pair_exts = [
            {
                '.ee': FTYPE_SARC,
                '.epe': FTYPE_RTPC,
            },
            {
                '.bl': FTYPE_SARC,
                '.nl': FTYPE_SARC,
                '.fl': FTYPE_SARC,
                '.blo': FTYPE_RTPC,
                '.nl.mdic': FTYPE_ADF,
                '.fl.mdic': FTYPE_ADF,
                '.pfs': FTYPE_TAG0,
                '.obc': FTYPE_OBC,
            },
            {
                '.meshc': FTYPE_ADF,
                '.hrmeshc': FTYPE_ADF,
                '.modelc': FTYPE_ADF,
                '.model_deps': FTYPE_TXT,
                '.pfxc': FTYPE_TAG0,
            },
            {
                '.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                '.atx0': None,
                '.atx1': None,
                '.atx2': None,
                '.atx3': None,
                '.atx4': None,
                '.atx5': None,
                '.atx6': None,
                '.atx7': None,
                '.atx8': None,
                '.atx9': None,
            },
        ]

        assoc_strings = {}
        for k, v in vpath_map.nodes.items():
            file_ext = k.decode('utf-8').split('.', 1)
            if len(file_ext) == 2:
                file = file_ext[0]
                ext = '.' + file_ext[1]
                for pe in pair_exts:
                    if ext in pe:
                        for pk, pv in pe.items():
                            assoc_strings[file + pk] = pv

        for k, v in assoc_strings.items():
            fn = k
            fn = fn.encode('ascii')
            fh = hash_little(fn)
            if fh in self.hash_present:
                vpath_map.propose(fn, ['ASSOC', None], possible_ftypes=v)

        self.log('STRINGS BY FILE NAME ASSOCIATION: Found {}'.format(len(assoc_strings)))

    def extract_node(self, node):
        if node.is_valid():
            if node.offset is not None:
                with ArchiveFile(self.file_obj_from(node)) as f:
                    if node.v_path is None:
                        ofile = self.working_dir + 'exported/{:08X}.dat'.format(node.hashid)
                    else:
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