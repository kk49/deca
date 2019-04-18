import os
import io
import multiprocessing
import re
import pickle
import json
import csv

import deca.ff_rtpc
from deca.errors import DecaFileExists
from deca.file import ArchiveFile, SubsetFile
from deca.game_info import GameInfo, game_info_load
from deca.ff_types import *
from deca.ff_txt import load_json
from deca.ff_adf import load_adf, load_adf_bare, AdfTypeMissing, GdcArchiveEntry
from deca.ff_adf_export_import import adf_export
from deca.ff_rtpc import Rtpc
from deca.ff_aaf import extract_aaf
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_sarc import FileSarc, EntrySarc
from deca.ff_determine import determine_file_type_and_size
from deca.ff_avtx import Ddsc
from deca.hash_jenkins import hash_little
from deca.util import Logger


class VfsPathNode:
    def __init__(self, vpath):
        self.vpath = vpath
        self.vhash = None
        self.vfsnodes = []
        self.src = []  # [[SARC, vfsnode], [RTPC, vfsnode], [ADF, vfsnode], [GUESS], ]
        self.used_at_runtime = False
        self.possible_ftypes = set()


class VfsPathMap:
    def __init__(self, logger):
        self.logger = logger
        self.nodes = {}

    def merge(self, other):
        for k, v in other.nodes.items():
            v2 = self.nodes.get(k, VfsPathNode(k))

            if v2.vhash is None:
                v2.vhash = v.vhash
            elif v.vhash is not None:
                if v.vhash != v2.vhash:
                    raise Exception('merge: {}: hash mismatch {} != {}'.format(k, v.vhash, v2.vhash))

            v2.vfsnodes = v2.vfsnodes + v.vfsnodes
            v2.src = v2.src + v.src
            v2.used_at_runtime = v2.used_at_runtime or v.used_at_runtime
            for kf in v.possible_ftypes:
                v2.possible_ftypes.add(kf)

            self.nodes[k] = v2

    def propose(self, vpath, src, used_at_runtime=False, vnode=None, possible_ftypes=FTYPE_ANY_TYPE):
        '''
        Add proposed vpath to map
        :param vpath: string representing vpath
        :param src: currently a vaguely formated list of information about where the vpath came from # TODO
        :param used_at_runtime: bool that indicates if this usage is known to be used by the executable gotten from procmon
        :param vnode: include vnode if the vnode was explicitly labeled, like in a sarc
        :param possible_ftypes: Value, or [Value] of file types that are expect to be connected to vpath
        :return: VpatjInference object
        '''

        if isinstance(vpath, str):
            vpath = vpath.encode('ascii', 'ignore')
        elif isinstance(vpath, bytes):
            try:
                vpath.decode('utf-8')
            except UnicodeDecodeError:
                self.logger.log('propose: BAD STRING NOT UTF-8 {}'.format(vpath))
                return None
        else:
            self.logger.log('propose: BAD STRING {}'.format(vpath))
            return None

        vpath = vpath.replace(b'\\\\', b'/').replace(b'\\', b'/')

        if vpath in self.nodes:
            iv = self.nodes[vpath]
        else:
            iv = VfsPathNode(vpath)
            iv.vhash = hash_little(vpath)

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
            vhash=None, pvpath=None, vpath=None, pid=None, level=0, index=None, offset=None,
            size_c=None, size_u=None, processed=False, used_at_runtime_depth=None,
            adf_type=None, sarc_type=None):
        self.uid = uid
        self.ftype = ftype
        self.adf_type = adf_type
        self.sarc_type = sarc_type
        self.is_compressed = compressed
        self.vpath = vpath
        self.vhash = vhash
        self.pvpath = pvpath
        self.pid = pid
        self.level = level
        self.index = index  # index in parent
        self.offset = offset  # offset in parent
        self.size_c = size_c  # compressed size in client
        self.size_u = size_u  # extracted size
        self.children = set()
        self.used_at_runtime_depth = used_at_runtime_depth
        self.processed = processed

    def file_type(self):
        if self.is_compressed:
            return self.ftype + '.z'
        else:
            return self.ftype

    def is_valid(self):
        return self.uid is not None and self.uid != 0

    def used_depth_set(self, v):
        if self.used_at_runtime_depth is None or self.used_at_runtime_depth > v:
            self.used_at_runtime_depth = v
            for ch in self.children:
                ch.used_depth_set(v+1)

    def __str__(self):
        info = []
        if self.ftype is not None:
            info.append('ft:{}'.format(self.file_type()))
        if self.vhash is not None:
            info.append('h:{:08X}'.format(self.vhash))
        if self.vpath is not None:
            info.append('v:{}'.format(self.vpath))
        if self.pvpath is not None:
            info.append('p:{}'.format(self.pvpath))
        if len(info) == 0:
            info.append('child({},{})'.format(self.pid, self.index))
        return ' '.join(info)


def game_file_to_sortable_string(v):
    if v[0:4] == 'game':
        return 'game{:08}'.format(int(v[4:]))
    else:
        return v


class VfsStructure:
    def __init__(self, game_info: GameInfo, working_dir, logger):
        self.game_info = game_info

        self.worlds = ['', 'worlds/base/']
        for widx in range(8):
            self.worlds.append('worlds/world{}/'.format(widx))

        self.external_adf_types = None

        self.working_dir = working_dir
        self.logger = logger

        # basic node tracking
        self.uid = 0
        self.table_vfsnode = [VfsNode()]
        self.map_uid_to_vfsnode = {}  # TODO currently redundant, may always be

        # tracking node hashs
        self.map_hash_to_vnodes = {}
        self.hash_present = set()

        # track info from ADFs
        self.map_name_usage = {}
        self.map_vhash_usage = {}
        self.map_adftype_usage = {}
        self.adf_missing_types = {}

        # track possible vpaths
        self.possible_vpath_map = VfsPathMap(self.logger)

        # results from connecting vpaths to vfsnodes
        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

    def logger_set(self, logger):
        self.logger = logger

    def file_obj_from(self, node: VfsNode, mode='rb'):
        if node.ftype == FTYPE_ARC:
            return open(node.pvpath, mode)
        elif node.ftype == FTYPE_TAB:
            return self.file_obj_from(self.table_vfsnode[node.pid])
        elif node.is_compressed:
            cache_dir = self.working_dir + '__CACHE__/'
            os.makedirs(cache_dir, exist_ok=True)
            file_name = cache_dir + '{:08X}.dat'.format(node.vhash)
            if not os.path.isfile(file_name):
                pnode = self.table_vfsnode[node.pid]
                with ArchiveFile(self.file_obj_from(pnode, mode)) as pf:
                    pf.seek(node.offset)
                    extract_aaf(pf, file_name)
            return open(file_name, mode)
        elif node.ftype == FTYPE_ADF_BARE:
            pnode = self.table_vfsnode[node.pid]
            return self.file_obj_from(pnode, mode)
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
            if node.vhash is not None:
                self.hash_present.add(node.vhash)
                vl = self.map_hash_to_vnodes.get(node.vhash, [])
                if node.offset is None:
                    vl.append(node)  # put symlinks at end
                else:
                    vl = [node] + vl  # put real files up front
                self.map_hash_to_vnodes[node.vhash] = vl

            if node.pid is not None:
                pnode = self.table_vfsnode[node.pid]
                pnode.children.add(node)
                if pnode.used_at_runtime_depth is not None and \
                   (node.used_at_runtime_depth is None or node.used_at_runtime_depth > (1+pnode.used_at_runtime_depth)):
                    node.used_depth_set(pnode.used_at_runtime_depth + 1)

        return node

    def load_from_archives(self, ver=3, debug=False):  # game_dir, archive_paths,
        self.logger.log('find all tab/arc files')
        input_files = []
        for fcat in self.game_info.archive_path():
            print(fcat)
            if os.path.isdir(fcat):
                files = os.listdir(fcat)
                ifns = []
                for file in files:
                    if 'tab' == file[-3:]:
                        ifns.append(file[0:-4])
                ifns.sort(key=game_file_to_sortable_string)
                for ifn in ifns:
                    input_files.append(os.path.join(fcat, ifn))

        self.logger.log('process all game tab / arc files')
        for ta_file in input_files:
            inpath = os.path.join(ta_file)
            file_arc = inpath + '.arc'
            self.node_add(VfsNode(ftype=FTYPE_ARC, pvpath=file_arc))

        any_change = True
        n_nodes = 0
        phase_id = 0
        while any_change:
            phase_id = phase_id + 1
            self.logger.log('Expand Archives Phase {}: Begin'.format(phase_id))

            any_change = False
            idx = n_nodes  # start after last processed node
            n_nodes = len(self.table_vfsnode)  # only process this level of nodes
            while idx < n_nodes:
                # if idx % 10000 == 0:
                #     self.logger.log('Processing {} of {}'.format(idx, len(self.table_vfsnode)))
                node = self.table_vfsnode[idx]
                if node.is_valid() and not node.processed:
                    if node.ftype == FTYPE_ARC:
                        # here we add the tab file as a child of the ARC, a trick to make it work with our data model
                        node.processed = True
                        any_change = True
                        tab_path = os.path.splitext(node.pvpath)
                        tab_path = tab_path[0] + '.tab'
                        cnode = VfsNode(ftype=FTYPE_TAB, pvpath=tab_path, pid=node.uid, level=node.level)
                        self.node_add(cnode)
                    elif node.ftype == FTYPE_TAB:
                        node.processed = True
                        any_change = True
                        with ArchiveFile(open(node.pvpath, 'rb'), debug=debug) as f:
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
                                    vhash=te.hashname, pid=node.uid, level=node.level + 1, index=i,
                                    offset=te.offset, size_c=te.size_c, size_u=te.size_u)
                                self.node_add(cnode)

                    elif node.ftype == FTYPE_SARC:
                        node.processed = True
                        any_change = True
                        sarc_file = FileSarc()
                        sarc_file.deserialize(self.file_obj_from(node))

                        for se in sarc_file.entries:
                            se: EntrySarc = se
                            offset = se.offset
                            if offset == 0:
                                offset = None  # sarc files with zero offset are not in file, but reference hash value
                            cnode = VfsNode(
                                vhash=se.vhash, pid=node.uid, level=node.level + 1, index=se.index,
                                offset=offset, size_c=se.length, size_u=se.length, vpath=se.vpath,
                                sarc_type=se.unk_file_type_hash)

                            self.node_add(cnode)
                            self.possible_vpath_map.propose(cnode.vpath, [FTYPE_SARC, node], vnode=cnode)

                    elif node.vhash == deca.hash_jenkins.hash_little(b'gdc/global.gdcc'):  # special case starting point for runtime
                        node.processed = True
                        any_change = True
                        with self.file_obj_from(node) as f:
                            buffer = f.read(node.size_u)
                        adf = load_adf(buffer)

                        bnode = VfsNode(
                            ftype=FTYPE_GDCBODY, pid=node.uid, level=node.level,
                            offset=adf.table_instance[0].offset,
                            size_c=adf.table_instance[0].size,
                            size_u=adf.table_instance[0].size)
                        self.node_add(bnode)

                        for entry in adf.table_instance_values[0]:
                            if isinstance(entry, GdcArchiveEntry):
                                # self.logger.log('GDCC: {:08X} {}'.format(entry.vpath_hash, entry.vpath))
                                adf_type = entry.adf_type_hash
                                ftype = None
                                if adf_type is not None:
                                    ftype = FTYPE_ADF_BARE
                                    # self.logger.log('ADF_BARE: Need Type: {:08x} {}'.format(adf_type, entry.vpath))
                                cnode = VfsNode(
                                    vhash=entry.vpath_hash, pid=bnode.uid, level=bnode.level + 1, index=entry.index,
                                    offset=entry.offset, size_c=entry.size, size_u=entry.size, vpath=entry.vpath,
                                    ftype=ftype, adf_type=adf_type)
                                self.node_add(cnode)
                                self.possible_vpath_map.propose(cnode.vpath, [FTYPE_ADF, node], vnode=cnode)

                idx = idx + 1
            self.logger.log('Expand Archives Phase {}: End'.format(phase_id))

        self.find_vpath_adf(self.possible_vpath_map)
        self.find_vpath_rtpc(self.possible_vpath_map)
        self.find_vpath_json(self.possible_vpath_map)
        self.find_vpath_exe(self.possible_vpath_map)
        self.find_vpath_procmon_dir(self.possible_vpath_map)
        self.find_vpath_procmon_file(self.possible_vpath_map)
        self.find_vpath_custom(self.possible_vpath_map)
        self.find_vpath_guess(self.possible_vpath_map)
        self.find_vpath_by_assoc(self.possible_vpath_map)

        self.process_vpaths()

        self.dump_status()

    def dump_status(self):
        self.logger.log('hashes: {}, mappings missing: {}, mappings present {}, mapping conflict {}'.format(
            len(self.hash_present),
            len(self.hash_map_missing),
            len(self.hash_map_present),
            len(self.hash_map_conflict)))

        for k, vs in self.adf_missing_types.items():
            for v in vs:
                vp = self.map_hash_to_vpath.get(v, b'')
                self.logger.log('Missing Type {:08x} in {:08X} {}'.format(k, v, vp.decode('utf-8')))

        for vid in self.hash_map_conflict:
            for vp in self.map_hash_to_vpath[vid]:
                self.logger.log('CONFLICT: {:08X} {}'.format(vid, vp))

    def process_vpaths(self):
        self.logger.log('process_vpaths: Input count {}'.format(len(self.possible_vpath_map.nodes)))

        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

        found_vpaths = set()
        for vp in self.possible_vpath_map.nodes.values():
            vp: VfsPathNode = vp
            vpid = vp.vhash
            if vpid in self.map_hash_to_vnodes:
                vnodes = self.map_hash_to_vnodes[vpid]
                for vnode in vnodes:
                    vnode: VfsNode = vnode
                    if vnode.is_valid():
                        if vnode.vpath is None:
                            if (len(vp.possible_ftypes) == 0) or (FTYPE_ANY_TYPE in vp.possible_ftypes) or \
                               (vnode.ftype is None and FTYPE_NO_TYPE in vp.possible_ftypes) or \
                               (vnode.ftype in vp.possible_ftypes):
                                self.logger.trace('vpath:add  {} {:08X} {} {} {}'.format(vp.vpath, vp.vhash, len(vp.src), vp.possible_ftypes, vnode.ftype))
                                vnode.vpath = vp.vpath
                                found_vpaths.add(vp.vpath)
                            else:
                                self.logger.log('vpath:skip {} {:08X} {} {} {}'.format(vp.vpath, vp.vhash, len(vp.src), vp.possible_ftypes, vnode.ftype))

                        if vnode.vpath == vp.vpath:
                            if vp.used_at_runtime and (vnode.used_at_runtime_depth is None or vnode.used_at_runtime_depth > 0):
                                # print('rnt', vp.vpath)
                                vnode.used_depth_set(0)
            else:
                self.logger.trace('vpath:miss {} {:08X} {} {}'.format(vp.vpath, vp.vhash, len(vp.src), vp.possible_ftypes))

        for vnode in self.table_vfsnode:
            vnode: VfsNode = vnode
            if vnode.is_valid():
                if vnode.vhash is not None:
                    vid = vnode.vhash
                    if vnode.vpath is None:
                        self.hash_map_missing.add(vid)
                    else:
                        self.hash_map_present.add(vid)
                        vpath = vnode.vpath
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

                        # tag atx file type since they have no header info
                        if vnode.ftype is None:
                            file, ext = os.path.splitext(vnode.vpath)
                            if ext[0:4] == b'.atx':
                                vnode.ftype = FTYPE_ATX
                            elif ext == b'.hmddsc':
                                vnode.ftype = FTYPE_HMDDSC

        found_vpaths = list(found_vpaths)
        found_vpaths.sort()
        with open(self.working_dir + 'found_vpaths.txt', 'a') as f:
            for vp in found_vpaths:
                f.write('{}\n'.format(vp.decode('utf-8')))

        #         for s in ss:
        #             hid = hash_little(s)
        #             if hid in self.hash_present:
        #                 if hid in self.map_hash_to_vpath:
        #                     if s != self.map_hash_to_vpath[hid]:
        #                         self.logger.trace('HASH CONFLICT STRINGS: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], s))
        #                         self.hash_bad[hid] = (self.map_hash_to_vpath[hid], s)
        #                 else:
        #                     if dump_found_paths:
        #                         f.write('{:08X}\t{}\n'.format(hid, s))
        #                     self.map_hash_to_vpath[hid] = s
        #                     self.map_vpath_to_hash[s] = hid
        #                     found = found + 1
        #
        # self.logger.log('fill in v_paths, mark extensions identified files as ftype')
        #
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION')
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.vhash is not None:
        #         hid = node.vhash
        #         if node.vpath is not None:
        #             if hid in self.map_hash_to_vpath:
        #                 if self.map_hash_to_vpath[hid] != node.vpath:
        #                     self.logger.trace('HASH CONFLICT ARCHIVE: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.vpath))
        #                     self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.vpath)
        #             else:
        #                 self.map_hash_to_vpath[hid] = node.vpath
        #                 self.map_vpath_to_hash[node.vpath] = hid
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION: found {} hashes, {} mapped'.format(len(self.hash_present), len(self.map_hash_to_vpath)))
        #
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.vhash is not None and node.vpath is None:
        #         if node.vhash in self.map_hash_to_vpath:
        #             node.vpath = self.map_hash_to_vpath[node.vhash]
        #
        #     if node.is_valid() and node.vhash is not None:
        #         if node.ftype not in {FTYPE_ARC, FTYPE_TAB}:
        #             if node.vhash in self.map_hash_to_vpath:
        #                 self.hash_map_present.add(node.vhash)
        #             else:
        #                 self.hash_map_missing.add(node.vhash)
        #
        #     if node.is_valid() and node.vpath is not None:
        #         if os.path.splitext(node.vpath)[1][0:4] == b'.atx':
        #             if node.ftype is not None:
        #                 raise Exception('ATX marked as non ATX: {}'.format(node.vpath))
        #             node.ftype = FTYPE_ATX
        #
        #         lst = self.map_vpath_to_vfsnodes.get(node.vpath, [])
        #         if len(lst) > 0 and lst[0].offset is None:  # Do not let symlink be first is list # TODO Sort by accessibility
        #             lst = [node] + lst
        #         else:
        #             lst.append(node)
        #         self.map_vpath_to_vfsnodes[node.vpath] = lst

    def find_vpath_adf(self, vpath_map):
        self.logger.log('PROCESS ADFs: find strings, propose terrain patches')
        indexes = []
        adf_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_ADF and node.vhash not in adf_done:
                adf_done.add(node.vhash)
                indexes.append(idx)

        q = multiprocessing.Queue()

        if os.name != 'nt':
            nprocs = max(1, multiprocessing.cpu_count() // 2)  # assuming hyperthreading exists and slows down processing

            indexes2 = [indexes[v::nprocs] for v in range(0, nprocs)]

            procs = []
            for idxs in indexes2:
                self.logger.log('Create Process: ({},{},{})'.format(min(idxs), max(idxs), len(idxs)))
                p = multiprocessing.Process(target=self.find_vpath_adf_core, args=(q, idxs,))
                self.logger.log('Process: {}: Start'.format(p))
                p.start()
                procs.append(p)
        else:
            procs = [None]
            self.find_vpath_adf_core(q, indexes)

        scount = 0
        for i in range(len(procs)):
            self.logger.log('Waiting {} of {}'.format(i+1, len(procs)))
            vpath_map_work, adf_missing_types, map_name_usage, map_vhash_usage, map_adftype_usage = q.get()
            scount += len(vpath_map_work.nodes)

            vpath_map.merge(vpath_map_work)

            for k, v in adf_missing_types.items():
                self.adf_missing_types[k] = self.adf_missing_types.get(k, []) + v

            for k, v in map_name_usage.items():
                self.map_name_usage[k] = self.map_name_usage.get(k, set()).union(v)

            for k, v in map_vhash_usage.items():
                self.map_vhash_usage[k] = self.map_vhash_usage.get(k, set()).union(v)

            for k, v in map_adftype_usage.items():
                self.map_adftype_usage[k] = self.map_adftype_usage.get(k, set()).union(v)

            self.logger.log('Process Done {} of {}'.format(i + 1, len(procs)))

        for p in procs:
            if p is not None:
                self.logger.log('Process: {}: Joining'.format(p))
                p.join()
                self.logger.log('Process: {}: Joined'.format(p))

        self.logger.log('PROCESS ADFs: Total ADFs: {}, Total Strings: {}'.format(len(adf_done), scount))

    def find_vpath_adf_core(self, q, indexs):
        vpath_map = VfsPathMap(self.logger)
        adf_missing_types = {}
        map_name_usage = {}
        map_vhash_usage = {}
        map_adftype_usage = {}

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
                        st = map_vhash_usage.get(s, set())
                        st.add(node)
                        map_vhash_usage[s] = st

                    if len(adf.table_instance_values) > 0 and \
                            adf.table_instance_values[0] is not None and \
                            isinstance(adf.table_instance_values[0], dict):
                        obj0 = adf.table_instance_values[0]

                        fns = []
                        # self name patch files
                        if 'PatchLod' in obj0 and 'PatchPositionX' in obj0 and 'PatchPositionZ' in obj0:
                            for world in self.worlds:
                                fn = world + 'terrain/hp/patches/patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                                    obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                                fns.append(fn)
                            fn = 'terrain/jc3/patches/patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                                obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                            fns.append(fn)

                        # self name environc files
                        if adf.table_instance[0].name == b'environ':
                            fn = 'environment/weather/{}.environc'.format(obj0['Name'].decode('utf-8'))
                            fns.append(fn)
                            fn = 'environment/{}.environc'.format(obj0['Name'].decode('utf-8'))
                            fns.append(fn)

                        found_any = False
                        for fn in fns:
                            if node.vhash == hash_little(fn):
                                vpath_map.propose(fn, [FTYPE_ADF, node], possible_ftypes=FTYPE_ADF)
                                found_any = True

                        if len(fns) > 0 and not found_any:
                            self.logger.log('COULD NOT MATCH GENERATED FILE NAME {:08X} {}'.format(node.vhash, fns[0]))

                    for ientry in adf.table_typedef:
                        adf_type_hash = ientry.type_hash
                        ev = map_adftype_usage.get(adf_type_hash, set())
                        ev.add(node.uid)
                        map_adftype_usage[adf_type_hash] = ev

                except AdfTypeMissing as ae:
                    adf_missing_types[ae.vhash] = adf_missing_types.get(ae.vhash, []) + [node.vhash]
                    print('Missing Type {:08x} in {:08X} {} {}'.format(
                        ae.vhash, node.vhash, node.vpath, node.pvpath))

        q.put([vpath_map, adf_missing_types, map_name_usage, map_vhash_usage, map_adftype_usage])

    def find_vpath_rtpc(self, vpath_map):
        self.logger.log('PROCESS RTPCs: look for hashable strings in RTPC files')
        indexes = []
        rtpc_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_RTPC and node.vhash not in rtpc_done:
                rtpc_done.add(node.vhash)
                indexes.append(idx)

        q = multiprocessing.Queue()

        if os.name != 'nt':
            nprocs = max(1, multiprocessing.cpu_count() // 2)  # assuming hyperthreading exists and slows down processing

            indexes2 = [indexes[v::nprocs] for v in range(0, nprocs)]

            procs = []
            for idxs in indexes2:
                self.logger.log('Create Process: ({},{},{})'.format(min(idxs), max(idxs), len(idxs)))
                p = multiprocessing.Process(target=self.find_vpath_rtpc_core, args=(q, idxs,))
                self.logger.log('Process: {}: Start'.format(p))
                p.start()
                procs.append(p)
        else:
            procs = [None]
            self.find_vpath_rtpc_core(q, indexes)

        scount = 0
        for i in range(len(procs)):
            self.logger.log('Waiting {} of {}'.format(i+1, len(procs)))
            vpath_map_work = q.get()
            scount += len(vpath_map_work.nodes)
            vpath_map.merge(vpath_map_work)
            self.logger.log('Process Done {} of {}'.format(i+1, len(procs)))

        for p in procs:
            if p is not None:
                self.logger.log('Process: {}: Joining'.format(p))
                p.join()
                self.logger.log('Process: {}: Joined'.format(p))

        self.logger.log('PROCESS RTPCs: Total RTPCs: {}, Total Strings: {}'.format(len(rtpc_done), scount))

    def find_vpath_rtpc_core(self, q, indexs):
        vpath_map = VfsPathMap(self.logger)
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
        self.logger.log('PROCESS JSONs: look for hashable strings in json files')
        json_done = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_TXT and node.vhash not in json_done:
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)

                json = load_json(buffer)
                if json is not None:
                    json_done.add(node.vhash)

                # Parse {"0":[]. "1":[]}
                if isinstance(json, dict) and '0' in json and '1' in json:
                    for k, v in json.items():
                        for l in v:
                            vpath_map.propose(l, [FTYPE_TXT, node])
        self.logger.log('PROCESS JSONs: Total JSON files {}'.format(len(json_done)))

    def find_vpath_exe(self, vpath_map):
        fn = './resources/{}/all_strings.tsv'.format(self.game_info.game_id)
        if os.path.isfile(fn):
            self.logger.log('STRINGS FROM EXE: look for hashable strings in EXE strings from IDA in ./resources/{}/all_strings.tsv'.format(self.game_info.game_id))
            with open(fn, 'r') as f:
                exe_strings = f.readlines()
            exe_strings = [line.split('\t') for line in exe_strings]
            exe_strings = [line[3].strip() for line in exe_strings if len(line) >= 4]
            exe_strings = list(set(exe_strings))
            for s in exe_strings:
                vpath_map.propose(s, ['EXE', None])
            self.logger.log('STRINGS FROM EXE: Found {} strings'.format(len(exe_strings)))

    def find_vpath_procmon_file(self, vpath_map):
        fn = './resources/{}/strings_procmon.txt'.format(self.game_info.game_id)
        if os.path.isfile(fn):
            self.logger.log('STRINGS FROM PROCMON: look for hashable strings in resources/{}/strings_procmon.txt'.format(self.game_info.game_id))
            with open(fn) as f:
                custom_strings = f.readlines()
                custom_strings = set(custom_strings)
                for s in custom_strings:
                    vpath_map.propose(s.strip(), ['PROCMON', None], used_at_runtime=True)
            self.logger.log('STRINGS FROM HASH FROM PROCMON: Total {} strings'.format(len(custom_strings)))

    def find_vpath_procmon_dir(self, vpath_map):
        path_name = './procmon_csv/{}'.format(self.game_info.game_id)
        custom_strings = set()

        if os.path.isdir(path_name):
            fns = os.listdir(path_name)
            fns = [os.path.join(path_name, fn) for fn in fns]
            for fn in fns:
                if os.path.isfile(fn):
                    self.logger.log('STRINGS FROM PROCMON DIR: look for hashable strings in {}'.format(fn))
                    with open(fn, 'r') as f:
                        db = csv.reader(f, delimiter=',', quotechar='"')
                        p = re.compile(r'^.*\\dropzone\\(.*)$')
                        for row in db:
                            pth = row[6]
                            # print(pth)
                            r = p.match(pth)
                            if r is not None:
                                s = r.groups(1)[0]
                                s = s.replace('\\', '/')
                                custom_strings.add(s)

        for s in custom_strings:
            vpath_map.propose(s.strip(), ['PROCMON', None], used_at_runtime=True)
        self.logger.log('STRINGS FROM HASH FROM PROCMON DIR: Total {} strings'.format(len(custom_strings)))

    def find_vpath_custom(self, vpath_map):
        fn = './resources/{}/strings.txt'.format(self.game_info.game_id)
        if os.path.isfile(fn):
            self.logger.log('STRINGS FROM CUSTOM: look for hashable strings in resources/{}/strings.txt'.format(self.game_info.game_id))
            with open(fn) as f:
                custom_strings = f.readlines()
                custom_strings = set(custom_strings)
                for s in custom_strings:
                    vpath_map.propose(s.strip(), ['CUSTOM', None])
            self.logger.log('STRINGS FROM CUSTOM: Total {} strings'.format(len(custom_strings)))

    def find_vpath_guess(self, vpath_map):
        self.logger.log('STRINGS BY GUESSING: ...')
        guess_strings = {}
        guess_strings['textures/ui/world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
        for res_i in range(8):
            guess_strings['settings/hp_settings/reserve_{}.bin'.format(res_i)] = FTYPE_RTPC
            guess_strings['settings/hp_settings/reserve_{}.bl'.format(res_i)] = FTYPE_SARC
            guess_strings['textures/ui/map_reserve_{}/world_map.ddsc'.format(res_i)] = [FTYPE_AVTX, FTYPE_DDS]
            for zoom_i in [1, 2, 3]:
                for index in range(500):
                    fn = 'textures/ui/map_reserve_{}/zoom{}/{}.ddsc'.format(res_i, zoom_i, index)
                    guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for world in self.worlds:
            for i in range(64):
                fn = world + 'terrain/hp/horizonmap/horizon_{}.ddsc'.format(i)
                guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

            for i in range(64):
                for j in range(64):
                    fn = world + 'ai/tiles/{:02d}_{:02d}.navmeshc'.format(i, j)
                    guess_strings[fn] = [FTYPE_TAG0, FTYPE_H2014]

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

        self.logger.log('STRINGS BY GUESSING: Total {} guesses'.format(len(guess_strings)))

    def find_vpath_by_assoc(self, vpath_map):
        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: epe/ee, blo/bl/nl/fl/nl.mdic/fl.mdic, mesh*/model*, avtx/atx?]')
        pair_exts = self.game_info.file_assoc()

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

        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: Found {}'.format(len(assoc_strings)))

    def extract_node(self, node: VfsNode, extract_dir: str, do_sha1sum, allow_overwrite):
        if node.is_valid():
            if node.offset is not None:
                with ArchiveFile(self.file_obj_from(node)) as f:
                    if node.vpath is None:
                        ofile = extract_dir + '{:08X}.dat'.format(node.vhash)
                    else:
                        ofile = extract_dir + '{}'.format(node.vpath.decode('utf-8'))

                    self.logger.log('Exporting {}'.format(ofile))

                    ofiledir = os.path.dirname(ofile)
                    os.makedirs(ofiledir, exist_ok=True)

                    buf = f.read(node.size_u)

                    if not allow_overwrite and os.path.isfile(ofile):
                        raise DecaFileExists(ofile)

                    with ArchiveFile(open(ofile, 'wb')) as fo:
                        fo.write(buf)

                    if node.ftype in {FTYPE_ADF, FTYPE_ADF_BARE}:
                        buffer = b''
                        with ArchiveFile(self.file_obj_from(node)) as f:
                            while True:
                                v = f.read(16 * 1024 * 1024)
                                if len(v) == 0:
                                    break
                                buffer = buffer + v

                        if node.ftype == FTYPE_ADF_BARE:
                            obj = load_adf_bare(buffer, node.adf_type, node.offset, node.size_u)
                        else:
                            obj = load_adf(buffer)

                        if obj is not None:
                            adf_export(obj, ofile)
                    elif node.ftype in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                        ddsc = None
                        if node.ftype == FTYPE_BMP:
                            f_ddsc = self.file_obj_from(node)
                            ddsc = Ddsc()
                            ddsc.load_bmp(f_ddsc)
                        elif node.ftype == FTYPE_DDS:
                            f_ddsc = self.file_obj_from(node)
                            ddsc = Ddsc()
                            ddsc.load_dds(f_ddsc)
                        elif node.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
                            if node.vpath is None:
                                f_ddsc = self.file_obj_from(node)
                                ddsc = Ddsc()
                                ddsc.load_ddsc(f_ddsc)
                            else:
                                filename = os.path.splitext(node.vpath)
                                if len(filename[1]) == 0 and node.ftype == FTYPE_AVTX:
                                    filename_ddsc = node.vpath
                                else:
                                    filename_ddsc = filename[0] + b'.ddsc'

                                if filename_ddsc in self.map_vpath_to_vfsnodes:
                                    extras = [b'.hmddsc']
                                    for i in range(1, 16):
                                        extras.append('.atx{}'.format(i).encode('ascii'))
                                    f_ddsc = self.file_obj_from(self.map_vpath_to_vfsnodes[filename_ddsc][0])
                                    f_atxs = []
                                    for extra in extras:
                                        filename_atx = filename[0] + extra
                                        if filename_atx in self.map_vpath_to_vfsnodes:
                                            f_atxs.append(self.file_obj_from(self.map_vpath_to_vfsnodes[filename_atx][0]))
                                    ddsc = Ddsc()
                                    ddsc.load_ddsc(f_ddsc)
                                    for atx in f_atxs:
                                        ddsc.load_atx(atx)

                        if ddsc is not None:
                            npimp = ddsc.mips[0].pil_image()
                            npimp.save(ofile + '.png')

                    # TODO
                    # if do_sha1sum:
                    #     # path, file = os.path.split(ofile)
                    #     # sfile = os.path.join(path, '.' + file)
                    #     sfile = ofile + '.deca_sha1sum'
                    #     hsha = sha1(buf).hexdigest()
                    #     self.logger.log('SHA1SUM {} {}'.format(hsha, sfile))
                    #     with open(sfile, 'w') as fo:
                    #         fo.write(hsha)
                return ofile

        return None

    def extract_nodes(self, vpath: str, extract_dir: str, do_sha1sum, allow_overwrite=False):
        vpath_re = re.compile(vpath)
        for k, v in self.map_vpath_to_vfsnodes.items():
            if vpath_re.match(k):
                self.extract_node(v[0], extract_dir, do_sha1sum, allow_overwrite)


def vfs_structure_prep(game_info, working_dir, logger=None, debug=False):
    os.makedirs(working_dir, exist_ok=True)

    if logger is None:
        logger = Logger(working_dir)

    cache_file = working_dir + 'vfs_cache.pickle'
    if os.path.isfile(cache_file):
        logger.log('LOADING: {} : {}'.format(game_info.game_dir, working_dir))
        with open(cache_file, 'rb') as f:
            vfs = pickle.load(f)
        vfs.logger_set(logger)
        vfs.dump_status()
        logger.log('LOADING: COMPLETE')
    else:
        logger.log('CREATING: {} {}'.format(game_info.game_dir, working_dir))

        game_info.save(os.path.join(working_dir, 'project.json'))

        vfs = VfsStructure(game_info, working_dir, logger)
        vfs.load_from_archives(debug=debug)
        with open(cache_file, 'wb') as f:
            pickle.dump(vfs, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.log('CREATING: COMPLETE')

    vfs.working_dir = working_dir

    # find external adf types
    vfs.external_adf_types = {}
    adftype_path = './resources/adf/'
    if os.path.isdir(adftype_path):
        files = os.listdir(adftype_path)
        for file in files:
            fn0, ext0 = os.path.splitext(file)
            fn, ext = os.path.splitext(fn0)
            try:
                adftype_hash = int(fn, 16)
                vfs.external_adf_types[adftype_hash] = adftype_path + file
            except ValueError:
                pass

    return vfs


def vfs_structure_open(project_file, logger=None, debug=False):
    working_dir = os.path.join(os.path.split(project_file)[0], '')
    game_info = game_info_load(project_file)

    return vfs_structure_prep(game_info, working_dir, logger=logger, debug=debug)


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
vhash : u32
pvpath : str
vpath : str
pid : u64
index : u64  # index in parent
offset : u64 # offset in parent
size_c : u64 # compressed size in client
size_u : u64 # extracted size

VfshashToNameMap
VfsNameToHashMap
'''