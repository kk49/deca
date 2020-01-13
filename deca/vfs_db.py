import os
import pickle
import io
import multiprocessing
import queue
import re
import json
import csv
import time
import sqlite3

from deca.file import ArchiveFile
from deca.vfs_base import VfsBase, VfsNode, VfsPathNode, VfsPathMap
from deca.game_info import GameInfo, game_info_load
from deca.errors import EDecaFileExists
from deca.ff_types import *
from deca.ff_txt import load_json
import deca.ff_rtpc
from deca.ff_adf import AdfDatabase, AdfTypeMissing, GdcArchiveEntry, adf_read_node
from deca.ff_rtpc import Rtpc
from deca.ff_arc_tab import TabFileV3, TabFileV4
from deca.ff_sarc import FileSarc, EntrySarc
from deca.util import Logger, remove_prefix_if_present, remove_suffix_if_present
from deca.hash_jenkins import hash_little
from deca.ff_determine import determine_file_type_and_size
from deca.kaitai.gfx import Gfx


language_codes = [
    'chi',  # Chinese
    'eng',  # English
    'fre',  # French
    'ger',  # German
    'jap',  # Japanese
    'pol',  # Polish
    'rus',  # Russian
    'sch',  # Simplified Chinese
    'spa',  # Spanish
    'swe',  # Swedish
]


def game_file_to_sortable_string(v):
    if v[0:4] == 'game':
        return 'game{:08}'.format(int(v[4:]))
    else:
        return v


class MultiProcessResults:
    def __init__(self, logger):
        self.logger = logger
        self.vpath_map = VfsPathMap(self.logger)
        self.adf_missing_types = {}
        self.map_name_usage = {}
        self.map_vhash_usage = {}
        self.map_adftype_usage = {}
        self.map_typedefs = {}

    def clear(self):
        self.vpath_map = VfsPathMap(self.logger)
        self.adf_missing_types = {}
        self.map_name_usage = {}
        self.map_vhash_usage = {}
        self.map_adftype_usage = {}
        self.map_typedefs = {}


class MultiProcessVfsBase:
    def __init__(self, name, q_in: multiprocessing.Queue, q_out: multiprocessing.Queue):
        self.name = name
        self.q_in = q_in
        self.q_out = q_out

        self.vfs: VfsBase = None

        self.results = MultiProcessResults(self)

        self.commands = {
            'load_vfs': self.command_load_vfs,
            'results_clear': self.command_results_clear,
            'results_send': self.command_results_send,
            'adf_initial_search': self.command_process_adf_initial,
        }

    def send(self, cmd, *params):
        self.q_out.put_nowait((self.name, cmd, params, ))

    def log(self, msg):
        self.send('log', msg)

    def command_load_vfs(self, vfs_filename):
        with open(vfs_filename, 'rb') as f:
            data = pickle.load(f)

        if isinstance(data, list):
            # version = data[0]
            self.vfs = data[1]
        else:
            # version = 1
            self.vfs = data

        self.vfs.logger_set(self)
        self.log('MultiProcessVfsBase.command_load_vfs: END')

    def command_results_clear(self):
        self.results.clear()

    def command_results_send(self):
        self.log('MultiProcessVfsBase.command_results_send: BEGIN')
        self.send('results', self.results)
        self.log('MultiProcessVfsBase.command_results_send: END')

    def process_nodes(self, indexs, method):
        nindexs = len(indexs)
        for i, index in enumerate(indexs):
            self.send('status', i, nindexs)
            node = self.vfs.table_vfsnode[index]
            method(node)

    def node_process_adf_initial(self, node):
        vpath_map = self.results.vpath_map
        adf_missing_types = self.results.adf_missing_types
        map_name_usage = self.results.map_name_usage
        map_vhash_usage = self.results.map_vhash_usage
        map_adftype_usage = self.results.map_adftype_usage
        map_typedefs = self.results.map_typedefs

        if node.is_valid():
            try:
                adf = adf_read_node(self.vfs, node)

                for sh in adf.table_stringhash:
                    vpath_map.propose(sh.value, [FTYPE_ADF, node])
                    rp = remove_prefix_if_present(b'intermediate/', sh.value)
                    if rp is not None:
                        vpath_map.propose(rp, [FTYPE_ADF, node])

                    rp = remove_suffix_if_present(b'.stop', sh.value)
                    if rp is None:
                        rp = remove_suffix_if_present(b'.play', sh.value)

                    if rp is not None:
                        # self.logger.log('Found possible wavc file from: {}'.format(sh.value))
                        for lng in language_codes:
                            fn = b'sound/dialogue/' + lng.encode('ascii') + b'/' + rp + b'.wavc'
                            # self.logger.log('  Trying: {}'.format(fn))
                            vpath_map.propose(fn, [FTYPE_ADF, node], possible_ftypes=[FTYPE_FSB5C])

                for sh in adf.found_strings:
                    vpath_map.propose(sh, [FTYPE_ADF, node])
                    rp = remove_prefix_if_present(b'intermediate/', sh)
                    if rp is not None:
                        vpath_map.propose(rp, [FTYPE_ADF, node])

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
                        for world in self.vfs.worlds:
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
                        self.log('COULD NOT MATCH GENERATED FILE NAME {:08X} {}'.format(node.vhash, fns[0]))

                for ientry in adf.table_typedef:
                    adf_type_hash = ientry.type_hash
                    ev = map_adftype_usage.get(adf_type_hash, set())
                    ev.add(node.uid)
                    map_adftype_usage[adf_type_hash] = ev
                    if ientry.type_hash not in map_typedefs:
                        map_typedefs[ientry.type_hash] = ientry

            except AdfTypeMissing as ae:
                adf_missing_types[ae.vhash] = adf_missing_types.get(ae.vhash, []) + [node.vhash]
                print('Missing Type {:08x} in {:08X} {} {}'.format(
                    ae.vhash, node.vhash, node.vpath, node.pvpath))

    def command_process_adf_initial(self, indexs):
        self.process_nodes(indexs, self.node_process_adf_initial)

    def run(self):
        keep_running = True
        while keep_running:
            try:
                cmd = self.q_in.get(block=True, timeout=10.0)
                params = cmd[1]
                cmd = cmd[0]

                self.log('Processing Command "{}"'.format(cmd))

                if cmd is not None:
                    if cmd == 'exit':
                        keep_running = False
                    else:
                        command = self.commands.get(cmd, None)
                        if command is None:
                            raise NotImplementedError(f'Command not implemented: {cmd}')
                        command(*params)

            except queue.Empty:
                pass
            except Exception as e:
                print('Exception: {}'.format(e))

        self.send('done')


def run_mp_vfs_base(name, q_in, q_out):
    p = MultiProcessVfsBase(name, q_in, q_out)
    p.run()


class VfsStructure(VfsBase):
    def __init__(self, game_info: GameInfo, working_dir, logger):
        VfsBase.__init__(self, game_info, working_dir, logger)
        self.adf_db = None
        self.external_files = set()
        self.progress_update_time_sec = 5.0

    def prepare_adf_db(self, debug=False):
        save_dir = os.path.join(self.working_dir, 'adf_types')
        os.makedirs(save_dir, exist_ok=True)
        self.adf_db = AdfDatabase(save_dir)

        exe_path = os.path.join(self.game_info.game_dir, self.game_info.exe_name)
        self.adf_db.extract_types_from_exe(exe_path)

    def load_from_archives(self, ver, debug=False):  # game_dir, archive_paths,
        self.logger.log('find all tab/arc files')
        input_files = []

        dir_in = self.game_info.archive_path()
        dir_found = []

        while len(dir_in) > 0:
            d = dir_in.pop(0)
            if os.path.isdir(d):
                dir_found.append(d)
                files = os.listdir(d)
                for file in files:
                    ff = os.path.join(d, file)
                    if os.path.isdir(ff):
                        dir_in.append(ff)

        for fcat in dir_found:
            self.logger.log('Processing Directory: {}'.format(fcat))
            if os.path.isdir(fcat):
                files = os.listdir(fcat)
                ifns = []
                for file in files:
                    if 'tab' == file[-3:]:
                        ifns.append(file[0:-4])
                ifns.sort(key=game_file_to_sortable_string)
                for ifn in ifns:
                    input_files.append(os.path.join(fcat, ifn))

        self.logger.log('process unarchived files')
        for ua_file in self.game_info.unarchived_files():
            with open(ua_file, 'rb') as f:
                ftype, fsize = determine_file_type_and_size(f, os.stat(ua_file).st_size)
            vpath = os.path.basename(ua_file).encode('utf-8')
            vhash = deca.hash_jenkins.hash_little(vpath)
            self.node_add(VfsNode(
                vhash=vhash, vpath=vpath, pvpath=ua_file, ftype=ftype,
                size_u=fsize, size_c=fsize, offset=0))

        self.logger.log('process all game tab / arc files')
        for ta_file in input_files:
            inpath = os.path.join(ta_file)
            file_arc = inpath + '.arc'
            self.node_add(VfsNode(ftype=FTYPE_ARC, pvpath=file_arc))

        any_change = True
        n_nodes = 0
        phase_id = 0
        last_update = None
        while any_change:
            phase_id = phase_id + 1
            self.logger.log('Expand Archives Phase {}: Begin'.format(phase_id))

            any_change = False
            idx = n_nodes  # start after last processed node
            n_nodes = len(self.table_vfsnode)  # only process this level of nodes
            while idx < n_nodes:
                ctime = time.time()
                if last_update is None or (last_update + self.progress_update_time_sec) < ctime:
                    last_update = ctime
                    self.logger.log('Finding Files: {} of {}'.format(idx, len(self.table_vfsnode)))

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
                        self.logger.log('Processing TAB: {}'.format(node.pvpath))
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
                        sarc_file.header_deserialize(self.file_obj_from(node))

                        for se in sarc_file.entries:
                            se: EntrySarc = se
                            offset = se.offset
                            if offset == 0:
                                offset = None  # sarc files with zero offset are not in file, but reference hash value
                            cnode = VfsNode(
                                vhash=se.vhash, pid=node.uid, level=node.level + 1, index=se.index,
                                offset=offset, size_c=se.length, size_u=se.length, vpath=se.vpath,
                                sarc_ext_hash=se.file_extention_hash)

                            self.node_add(cnode)
                            self.possible_vpath_map.propose(cnode.vpath, [FTYPE_SARC, node], vnode=cnode)

                    elif node.vhash == deca.hash_jenkins.hash_little(b'gdc/global.gdcc'):
                        # special case starting point for runtime
                        node.processed = True
                        any_change = True
                        with self.file_obj_from(node) as f:
                            buffer = f.read(node.size_u)
                        adf = self.adf_db.load_adf(buffer)

                        bnode_name = b'gdc/global.gdc.DECA'
                        bnode = VfsNode(
                            vhash=deca.hash_jenkins.hash_little(bnode_name),
                            vpath=bnode_name,
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

                    else:
                        pass
                idx = idx + 1
            self.logger.log('Expand Archives Phase {}: End'.format(phase_id))

    def get_vnode_indexs_from_ftype(self, ftype):
        indexs = []
        done_set = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == ftype and node.vhash not in done_set:
                done_set.add(node.vhash)
                indexs.append(idx)
        return indexs, done_set

    def find_vpath_adf(self, vpath_map, do_adfb=False):
        ftype = FTYPE_ADF
        if do_adfb:
            ftype = FTYPE_ADF_BARE

        self.logger.log('PROCESS ADFs: find strings, propose terrain patches. FTYPE = {}'.format(ftype))

        indexes, adf_done = self.get_vnode_indexs_from_ftype(ftype)
        scount = 0

        if len(indexes) > 0:
            q_results = multiprocessing.Queue()

            nprocs = min(len(indexes), max(1, multiprocessing.cpu_count() // 2))   # assuming hyperthreading exists and slows down processing
            nprocs = multiprocessing.cpu_count()

            indexes2 = [indexes[v::nprocs] for v in range(0, nprocs)]

            procs = []
            q_commands = []
            names = []
            for i, idxs in enumerate(indexes2):
                self.logger.log('Create Process: ({},{},{})'.format(min(idxs), max(idxs), len(idxs)))
                q_command = multiprocessing.Queue()
                q_commands.append(q_command)
                name = 'process_{}'.format(i)
                names.append(name)
                p = multiprocessing.Process(target=run_mp_vfs_base, args=(name, q_command, q_results))
                self.logger.log('Process: {}: Start'.format(p))
                p.start()

                q_command.put(['load_vfs', ['/home/krys/prj/work/gz/vfs_phase_1.pickle'], ])
                q_command.put(['results_clear', [], ])
                q_command.put(['adf_initial_search', [idxs], ])
                q_command.put(['results_send', [], ])
                q_command.put(['exit', [], ])
                procs.append(p)

            last_update = None
            start_time = time.time()
            status = {}
            proc_running = len(procs)
            while proc_running > 0:
                ctime = time.time()
                if last_update is None or (last_update + self.progress_update_time_sec) < ctime:
                    last_update = ctime
                    n_done = 0
                    n_total = 0
                    for k, v in status.items():
                        n_done += v[0]
                        n_total += v[1]
                    perc = 0
                    if n_total > 0:
                        perc = n_done / n_total
                    self.logger.log('Processing {}: {} of {} done ({:3.1f}%) elapsed {:5.1f} seconds'.format(
                        ftype, n_done, n_total, perc * 100.0, ctime - start_time))

                try:
                    msg = q_results.get(block=False, timeout=1)
                    proc_name = msg[0]
                    proc_cmd = msg[1]
                    proc_params = msg[2]

                    if proc_cmd not in {'log', 'status'}:
                        self.logger.log('Manager: received msg {}:{}'.format(proc_name, proc_cmd))

                    if proc_cmd == 'log':
                        self.logger.log('{}: {}'.format(proc_name, proc_params[0]))
                    elif proc_cmd == 'done':
                        proc_running -= 1
                    elif proc_cmd == 'status':
                        status[proc_name] = proc_params
                    elif proc_cmd == 'results':
                        results: MultiProcessResults = proc_params[0]
                        scount += len(results.vpath_map.nodes)

                        vpath_map.merge(results.vpath_map)

                        for k, v in results.adf_missing_types.items():
                            self.adf_missing_types[k] = self.adf_missing_types.get(k, []) + v

                        for k, v in results.map_name_usage.items():
                            self.map_name_usage[k] = self.map_name_usage.get(k, set()).union(v)

                        for k, v in results.map_vhash_usage.items():
                            self.map_vhash_usage[k] = self.map_vhash_usage.get(k, set()).union(v)

                        for k, v in results.map_adftype_usage.items():
                            self.map_adftype_usage[k] = self.map_adftype_usage.get(k, set()).union(v)

                        self.adf_db.typedefs_add(results.map_typedefs)

                        self.logger.log('Process Done {}'.format(proc_name))
                    else:
                        print(msg)
                except queue.Empty:
                    pass

            for p in procs:
                if p is not None:
                    self.logger.log('Process: {}: Joining'.format(p))
                    p.join()
                    self.logger.log('Process: {}: Joined'.format(p))

        self.logger.log('PROCESS ADFs: Total ADFs: {}, Total Strings: {}'.format(len(adf_done), scount))

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
                            if ext in {b'.tga', b'.dds'}:
                                vpath_map.propose(fn + b'.ddsc', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])
                            elif ext == b'.skeleton':
                                vpath_map.propose(fn + b'.bsk', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_TAG0])
                            elif ext == b'.ragdoll':
                                vpath_map.propose(fn + b'.brd', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_TAG0])
                                vpath_map.propose(fn + b'.ragdolsettingsc', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_ADF])
                            elif ext == b'.al':
                                vpath_map.propose(fn + b'.afsmb', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_RTPC])
                                vpath_map.propose(fn + b'.asb', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_RTPC])
                            elif ext == b'.model_xml':
                                vpath_map.propose(fn + b'.model_xmlc', [FTYPE_RTPC, node])
                                vpath_map.propose(fn + b'.model.xml', [FTYPE_RTPC, node])
                                vpath_map.propose(fn + b'.model.xmlc', [FTYPE_RTPC, node])
                                vpath_map.propose(fn + b'.xml', [FTYPE_RTPC, node])
                                vpath_map.propose(fn + b'.xmlc', [FTYPE_RTPC, node])
                                vpath_map.propose(fn + b'.modelc', [FTYPE_RTPC, node])
                            elif len(ext) > 0:
                                vpath_map.propose(s + b'c', [FTYPE_RTPC, node], possible_ftypes=[FTYPE_ADF])

                            '''
                            animations/skeletons/characters/machines/skirmisher_secondary_motion.skeleton -> bsk tag0
                            animations/ragdoll/skirmisher_sm.ragdoll -> brd tag0 , ragdolsettingsc ADF, ADF_BARE
                            animations/statemachines/machines/skirmisher/skirmisher_base.al -> {afsmb, asb} rtpc
                            editor/entities/characters/machines/skirmisher/skir_damage.mdp -> mdpc ADF, ADF_BARE
                            editor/entities/characters/default_ground_alignment.mtune -> mtunec ADF, ADF_BARE
                            '''
        q.put(vpath_map)

    def find_vpath_rtpc(self, vpath_map):
        self.logger.log('PROCESS RTPCs: look for hashable strings in RTPC files')

        indexes, rtpc_done = self.get_vnode_indexs_from_ftype(FTYPE_RTPC)
        scount = 0
        if len(indexes) > 0:
            q = multiprocessing.Queue()

            if os.name != 'nt':
                nprocs = min(len(indexes), max(1, multiprocessing.cpu_count() // 2))  # assuming hyperthreading exists and slows down processing

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

    def find_vpath_gfx(self, vpath_map):
        self.logger.log('PROCESS GFXs: look for hashable strings in autodesk ScaleForm files')
        done_set = set()
        for idx in range(len(self.table_vfsnode)):
            node = self.table_vfsnode[idx]
            if node.is_valid() and node.ftype == FTYPE_GFX and node.vhash not in done_set:
                with self.file_obj_from(node) as f:
                    buffer = f.read(node.size_u)

                gfx = Gfx.from_bytes(buffer)

                for tag in gfx.zlib_body.tags:
                    if Gfx.TagType.gfx_exporter_info == tag.record_header.tag_type:
                        vpath_map.propose(f'ui/{tag.tag_body.name}.gfx', [FTYPE_GFX, node], possible_ftypes=[FTYPE_GFX])
                        for i in range(255):
                            fn = 'ui/{}_i{:x}.ddsc'.format(tag.tag_body.name, i)
                            vpath_map.propose(fn, [FTYPE_GFX, node], possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])

                    elif tag.record_header.tag_type in {Gfx.TagType.gfx_define_external_image, Gfx.TagType.gfx_define_external_image2}:
                        fn = tag.tag_body.file_name
                        fn = os.path.basename(fn)
                        fn, ext = os.path.splitext(fn)
                        vpath_map.propose(f'ui/{fn}.ddsc', [FTYPE_GFX, node], possible_ftypes=[FTYPE_AVTX, FTYPE_DDS])

                    elif Gfx.TagType.import_assets2 == tag.record_header.tag_type:
                        fn = tag.tag_body.url
                        fn = os.path.basename(fn)
                        fn, ext = os.path.splitext(fn)
                        vpath_map.propose(f'ui/{tag.tag_body.url}', [FTYPE_GFX, node], possible_ftypes=[FTYPE_GFX])
                        vpath_map.propose(f'ui/{fn}.gfx', [FTYPE_GFX, node], possible_ftypes=[FTYPE_GFX])

                done_set.add(node.vhash)

        self.logger.log('PROCESS GFXs: Total GFX files {}'.format(len(done_set)))

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
                        for item in v:
                            vpath_map.propose(item, [FTYPE_TXT, node])
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
        guess_strings['gdc/global.gdcc'] = FTYPE_ADF
        guess_strings['textures/ui/world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
        for res_i in range(8):
            guess_strings['settings/hp_settings/reserve_{}.bin'.format(res_i)] = FTYPE_RTPC
            guess_strings['settings/hp_settings/reserve_{}.bl'.format(res_i)] = FTYPE_SARC
            guess_strings['textures/ui/map_reserve_{}/world_map.ddsc'.format(res_i)] = [FTYPE_AVTX, FTYPE_DDS]
            guess_strings['textures/ui/map_reserve_{}/world_map.ddsc'.format(res_i)] = [FTYPE_AVTX, FTYPE_DDS]
            for zoom_i in [1, 2, 3]:
                for index in range(500):
                    fn = 'textures/ui/map_reserve_{}/zoom{}/{}.ddsc'.format(res_i, zoom_i, index)
                    guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for zoom_i in [1, 2, 3]:
            for index in range(500):
                fn = 'textures/ui/warboard_map/zoom{}/{}.ddsc'.format(zoom_i, index)
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

        for lng in language_codes:
            fn = 'text/master_{}.stringlookup'.format(lng)
            guess_strings[fn] = [FTYPE_ADF, FTYPE_ADF_BARE]

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
            file_ext = os.path.splitext(k.decode('utf-8'))
            if len(file_ext[0]) > 0 and len(file_ext[1]) > 0:
                file = file_ext[0]
                ext = file_ext[1]
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

    def node_update_vpath_mapping(self, vnode):
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
            if vnode.ftype is None and vnode.vpath is not None:
                file, ext = os.path.splitext(vnode.vpath)
                if ext[0:4] == b'.atx':
                    vnode.ftype = FTYPE_ATX
                elif ext == b'.hmddsc':
                    vnode.ftype = FTYPE_HMDDSC

    def process_vpaths(self):
        self.logger.log('process_vpaths: Input count {}'.format(len(self.possible_vpath_map.nodes)))

        self.hash_map_present = set()
        self.hash_map_missing = set()
        self.hash_map_conflict = set()
        self.map_hash_to_vpath = {}
        self.map_vpath_to_vfsnodes = {}

        found_vpaths = set()

        vp: VfsPathNode
        for vp in self.possible_vpath_map.nodes.values():
            vpid = vp.vhash
            if vpid in self.map_hash_to_vnodes:
                vnodes = self.map_hash_to_vnodes[vpid]
                vnode: VfsNode
                for vnode in vnodes:
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

        vnode: VfsNode
        for vnode in self.table_vfsnode:
            if vnode.is_valid() and vnode.vhash is not None:
                self.node_update_vpath_mapping(vnode)

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

    def search_for_vpaths(self):
        self.find_vpath_adf(self.possible_vpath_map, do_adfb=False)
        self.find_vpath_adf(self.possible_vpath_map, do_adfb=True)
        self.find_vpath_rtpc(self.possible_vpath_map)
        self.find_vpath_gfx(self.possible_vpath_map)
        self.find_vpath_json(self.possible_vpath_map)
        self.find_vpath_exe(self.possible_vpath_map)
        self.find_vpath_procmon_dir(self.possible_vpath_map)
        self.find_vpath_procmon_file(self.possible_vpath_map)
        self.find_vpath_custom(self.possible_vpath_map)
        self.find_vpath_guess(self.possible_vpath_map)
        self.find_vpath_by_assoc(self.possible_vpath_map)

        self.process_vpaths()

    def dump_status(self):
        self.logger.log('hashes: {}, mappings missing: {}, mappings present {}, mapping conflict {}'.format(
            len(self.hash_present),
            len(self.hash_map_missing),
            len(self.hash_map_present),
            len(self.hash_map_conflict)))

        for k, vs in self.adf_missing_types.items():
            for v in vs:
                vps = self.map_hash_to_vpath.get(v, {})
                for vp in vps:
                    self.logger.log('Missing Type {:08x} in {:08X} {}'.format(k, v, vp))

        for vid in self.hash_map_conflict:
            for vps in self.map_hash_to_vpath[vid]:
                for vp in vps:
                    self.logger.log('CONFLICT: {:08X} {}'.format(vid, vp))

    def external_file_add(self, filename):
        if not hasattr(self, 'external_files'):
            self.external_files = set()

        if filename not in self.external_files and os.path.isfile(filename):
            with open(filename, 'rb') as f:
                ftype, fsize = determine_file_type_and_size(f, os.stat(filename).st_size)

            vpath = filename.replace(':', '/')
            vpath = vpath.replace('\\', '/')
            vpath = ('__EXTERNAL_FILES__' + vpath).encode('ascii')
            vhash = deca.hash_jenkins.hash_little(vpath)
            vnode = VfsNode(
                vhash=vhash, vpath=vpath, pvpath=filename, ftype=ftype,
                size_u=fsize, size_c=fsize, offset=0)
            self.node_add(vnode)
            self.node_update_vpath_mapping(vnode)

            self.external_files.add(filename)

            self.logger.log('ADDED {} TO EXTERNAL FILES'.format(filename))
        else:
            self.logger.log('FAILED TO OPEN:  {}'.format(filename))


def vfs_structure_prep(game_info, working_dir, logger=None, debug=False):
    os.makedirs(working_dir, exist_ok=True)

    if logger is None:
        logger = Logger(working_dir)

    version = 0
    vfs = None
    phase_0_cache_file = working_dir + 'vfs_phase_0.pickle'
    phase_1_cache_file = working_dir + 'vfs_phase_1.pickle'
    cache_file = working_dir + 'vfs_cache.pickle'
    if os.path.isfile(cache_file):
        logger.log('LOADING: {} : {}'.format(game_info.game_dir, working_dir))
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)

        if isinstance(data, list):
            version = data[0]
            vfs = data[1]
        else:
            version = 1
            vfs = data

        vfs.logger_set(logger)
        logger.log('LOADING: COMPLETE')

    if version < 1:
        logger.log('CREATING: {} {}'.format(game_info.game_dir, working_dir))

        game_info.save(os.path.join(working_dir, 'project.json'))

        version = 1
        vfs = VfsStructure(game_info, working_dir, logger)

        # parse exe
        if os.path.isfile(phase_0_cache_file):
            with open(phase_0_cache_file, 'rb') as f:
                data = pickle.load(f)
                vfs = data[1]
        else:
            vfs.prepare_adf_db(debug=debug)
            with open(phase_0_cache_file, 'wb') as f:
                data = [version, vfs]
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        # parse archive files
        if os.path.isfile(phase_1_cache_file):
            with open(phase_1_cache_file, 'rb') as f:
                data = pickle.load(f)
                vfs = data[1]
        else:
            vfs.load_from_archives(debug=debug, ver=game_info.archive_version)
            with open(phase_1_cache_file, 'wb') as f:
                data = [version, vfs]
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        # search for vpaths
        vfs.search_for_vpaths()
        with open(cache_file, 'wb') as f:
            data = [version, vfs]
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.log('CREATING: COMPLETE')

    vfs.dump_status()

    vfs.working_dir = working_dir

    # dump vpath file if not present
    vpath_file = os.path.join(vfs.working_dir, 'vpaths.txt')
    if not os.path.isfile(vpath_file):
        logger.log('CREATING: vpaths.txt')
        vpaths = list(vfs.map_vpath_to_vfsnodes.keys())
        vpaths.sort()
        with open(vpath_file, 'w') as f:
            for vpath in vpaths:
                f.write('{}\n'.format(vpath))

    return vfs


def vfs_structure_open(project_file, logger=None, debug=False):
    working_dir = os.path.join(os.path.split(project_file)[0], '')
    game_info = game_info_load(project_file)

    return vfs_structure_prep(game_info, working_dir, logger=logger, debug=debug)
