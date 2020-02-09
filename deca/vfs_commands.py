import os
import io
import multiprocessing
import queue
import time
import sys
import traceback
import numpy as np

import deca.ff_rtpc

from .file import ArchiveFile
from .vfs_db import VfsDatabase, VfsNode, language_codes, v_hash_type_4, v_hash_type_8
from .db_wrap import DbWrap
from .ff_types import *
from .ff_txt import load_json
from .ff_adf import AdfTypeMissing, GdcArchiveEntry
from .ff_rtpc import Rtpc, k_type_str
from .ff_arc_tab import tab_file_load, TabEntryFileBase
from .ff_sarc import FileSarc, EntrySarc
from .ff_gtoc import process_buffer_gtoc, GtocArchiveEntry, GtocFileEntry
from .util import remove_prefix_if_present, remove_suffix_if_present
from .kaitai.gfx import Gfx


print_node_info = False


class LogWrapper:
    def __init__(self, logger):
        self._logger = logger

    def log(self, msg):
        self._logger.log(msg)

    def trace(self, msg):
        self._logger.trace(msg)

    def status(self, i, n):
        self._logger.log(f'STATUS: {i} of {n}')

    def exception(self, exc):
        self._logger.error(f'EXCEPTION {exc}')


class MultiProcessControl:
    def __init__(self, project_file, working_dir, logger):
        self.project_file = project_file
        self.working_dir = working_dir
        self.logger = logger
        self.progress_update_time_sec = 5.0

        # assuming hyper-threading exists and slows down processing
        # self.mp_n_processes = 1
        # self.mp_n_processes = max(1, 2 * multiprocessing.cpu_count() // 4)
        self.mp_n_processes = max(1, 3 * multiprocessing.cpu_count() // 4)

    def do_map(self, cmd, params, step_id=None):
        self.logger.log(f'Manager: "{cmd}" with {len(params)} parameters using {self.mp_n_processes} processes')

        indexes = [params[v::self.mp_n_processes] for v in range(0, self.mp_n_processes)]

        command_list = []
        for ii in indexes:
            command_list.append([cmd, [ii]])

        results = self.mp_issue_commands(command_list, step_id=step_id)

        all_results = []
        for r in results:
            all_results += r

        return all_results

    def mp_issue_commands(self, command_list: list, step_id=None):
        command_todo = [(i, cmd) for i, cmd in enumerate(command_list)]
        command_active = {}
        command_complete = []
        command_results = [None] * len(command_list)

        exception_list = []

        if step_id is None:
            step_id = ''
        else:
            step_id = ': {}'.format(step_id)

        status = {}
        last_update = None
        start_time = time.time()

        local = False
        if local:
            vfs = VfsDatabase(self.project_file, self.working_dir, self.logger)
            processor = Processor(vfs, LogWrapper(self.logger))
            for i, command in command_todo:
                command_results[i] = processor.process_command(command[0], command[1])
            vfs.shutdown()
        else:
            mp_q_results = multiprocessing.Queue()

            mp_processes = {}
            for i in range(self.mp_n_processes):
                name = 'process_{}'.format(i)

                self.logger.debug('Process Create: {}'.format(name))
                q_command = multiprocessing.Queue()
                p = multiprocessing.Process(
                    target=run_mp_vfs_base, args=(name, self.project_file, self.working_dir, q_command, mp_q_results))
                mp_processes[name] = (name, p, q_command)

                self.logger.debug('Process Start: {}'.format(p))

                p.start()

            processes_available = set(mp_processes.keys())

            while len(processes_available) > 0 and (len(command_todo) + len(command_active)) > 0:
                ctime = time.time()
                if last_update is None or (last_update + self.progress_update_time_sec) < ctime:
                    n_done = 0
                    n_total = 0
                    for k, v in status.items():
                        n_done += v[0]
                        n_total += v[1]
                    if n_total > 0:
                        last_update = ctime
                        self.logger.log('Processing{}: {} of {} done ({:3.1f}%) elapsed {:5.1f} seconds'.format(
                            step_id, n_done, n_total, n_done / n_total * 100.0, ctime - start_time))

                if len(command_active) < self.mp_n_processes and len(command_todo) > 0:
                    # add commands
                    available_procs = processes_available - set(command_active.keys())
                    proc = available_procs.pop()
                    proc = mp_processes[proc]
                    name = proc[0]
                    q_command: queue.Queue = proc[2]
                    command = command_todo.pop(0)
                    command_active[name] = command
                    q_command.put(command[1])
                else:
                    try:
                        msg = mp_q_results.get(block=False, timeout=1)
                        proc_name = msg[0]
                        proc_cmd = msg[1]
                        proc_params = msg[2]

                        if proc_cmd not in {'trace', 'debug', 'log', 'status', 'exception', 'process_done'}:
                            self.logger.debug('Manager: received msg {}:{}'.format(proc_name, proc_cmd))

                        if proc_cmd == 'log':
                            self.logger.log('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'debug':
                            self.logger.debug('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'trace':
                            self.logger.trace('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'error':
                            self.logger.error('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'warning':
                            self.logger.warning('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'exception':
                            exception_list.append(proc_params)
                            self.logger.error('{}: EXCEPTION: {}'.format(proc_name, proc_params))
                        elif proc_cmd == 'status':
                            status[proc_name] = proc_params
                        elif proc_cmd == 'cmd_done':
                            command = command_active.pop(proc_name)
                            command_complete.append([proc_name, proc_params[0]])
                            command_results[command[0]] = proc_params[1]
                            self.logger.debug('Manager: {} completed {} {}'.format(proc_name, proc_params[0], len(proc_params[1])))
                        elif proc_cmd == 'process_done':
                            self.logger.debug('Manager: {} DONE'.format(proc_name))
                            command_active.pop(proc_name)
                            processes_available.discard(proc_name)
                        else:
                            print(msg)
                    except queue.Empty:
                        pass

            # shutdown processes
            for k in processes_available:
                v = mp_processes[k]
                v[2].put(('exit', []))
                self.logger.debug('Manager: Issued Exit to {}'.format(k))

            # join
            for k, v in mp_processes.items():
                self.logger.debug('Manager: Joining {}'.format(k))
                v[1].join()

            if exception_list:
                raise Exception('Manager: PROCESSING FAILED')

            self.logger.log('Manager: Done')

            return command_results


class Processor:
    def __init__(self, vfs: VfsDatabase, comm):
        self._vfs = vfs
        self._comm = comm

        self.commands = {
            'process_file_type_find': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_file_type_find),
            'process_symlink': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_symlink),
            'process_exe': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_exe),
            'process_arc': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_arc),
            'process_tab': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_tab),
            'process_gtoc': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_gtoc),
            'process_garc': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_garc),
            'process_sarc': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_sarc),
            'process_global_gdcc': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_global_gdcc),
            'process_global_gdcc_body': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_global_gdcc_body),
            'process_resource_bundle': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_resource_bundle),
            'process_adf_initial': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_adf_initial),
            'process_rtpc_initial': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_rtpc_initial),
            'process_gfx_initial': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_gfx_initial),
            'process_txt_initial': lambda idxs: self.loop_over_uid_wrapper(idxs, self.process_txt_initial),
            'process_vhash_final': lambda idxs: self.loop_over_vhash_wrapper(idxs, self.process_vhash_final),
        }

        nhf = []
        for prefix in self._vfs.game_info.world_navheightfields:
            for v0 in range(64):
                for v1 in range(64):
                    fn = prefix + '{:02d}_{:02d}.nhf'.format(v0, v1)
                    nhf.append((fn, self._vfs.file_hash(fn)))

        self.nav_height_field_possible_names = nhf

    def process_command(self, cmd, params):
        command = self.commands.get(cmd, None)
        if command is None:
            raise NotImplementedError(f'Command not implemented: {cmd}')
        result = command(*params)
        return result

    def loop_over_uid_wrapper(self, indexes, func):
        n_indexes = len(indexes)
        results = [None] * n_indexes
        with DbWrap(self._vfs, logger=self._comm, index_offset=n_indexes) as db:
            for i, index in enumerate(indexes):
                self._comm.status(i, n_indexes)
                node = db.db().node_where_uid(index)
                results[i] = (index, func(node, db))
            self._comm.status(n_indexes, n_indexes)

        return results

    def loop_over_vhash_wrapper(self, vhashes, func):
        n_indexes = len(vhashes)
        results = [None] * n_indexes
        with DbWrap(self._vfs, logger=self._comm, index_offset=n_indexes) as db:
            for i, v_hash in enumerate(vhashes):
                self._comm.status(i, n_indexes)
                results[i] = (v_hash, func(v_hash, db))
            self._comm.status(n_indexes, n_indexes)

        return results

    def process_file_type_find(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing File Type Determine: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))
        db.db().determine_file_type(node)
        if node.file_type is None:
            return False
        else:
            db.node_update(node)
            return True

    def process_symlink(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing SYMLINK: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        node.processed_file_set(True)
        db.node_update(node)

        return True

    def process_exe(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing EXE: {} {}'.format(node.uid, node.p_path))

        db.extract_types_from_exe(node.p_path)
        node.processed_file_set(True)
        db.node_update(node)

        return True

    def process_arc(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing ARC: {} {}'.format(node.uid, node.p_path))

        # here we add the tab file as a child of the ARC, a trick to make it work with our data model
        tab_path = os.path.splitext(node.p_path)
        tab_path = tab_path[0] + '.tab'
        cnode = VfsNode(file_type=FTYPE_TAB, p_path=tab_path, pid=node.uid, v_hash_type=db.file_hash_type)
        db.node_add(cnode)
        node.processed_file_set(True)
        db.node_update(node)

        return True

    def process_tab(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing TAB: {} {}'.format(node.uid, node.p_path))

        ver = db.db().game_info.archive_version
        debug = False

        tab_file = tab_file_load(node.p_path, ver)

        te: TabEntryFileBase
        for i, te in enumerate(tab_file.file_table):
            if te.size_c == 0 or te.size_u == 0:
                # handle zero length items as symlinks?
                blocks = None
                te.offset = None
            else:
                if te.file_block_table is None:
                    blocks = None
                else:
                    blocks = []
                    offset = te.offset
                    for bi, block in enumerate(te.file_block_table):
                        blocks.append((offset, block[0], block[1]))
                        offset += block[0]

                # for now don't include the nameless top level symlinks
                cnode = VfsNode(
                    v_hash_type=db.file_hash_type,
                    v_hash=te.hashname, pid=node.uid, index=i,
                    offset=te.offset, size_c=te.size_c, size_u=te.size_u,
                    compression_type=te.compression_type,
                    compression_flag=te.compression_flags,
                    blocks=blocks)

                db.node_add(cnode)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_sarc(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing SARC: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        sarc_file = FileSarc()
        sarc_file.header_deserialize(db.db().file_obj_from(node))

        for se in sarc_file.entries:
            se: EntrySarc = se
            offset = se.offset
            if offset == 0:
                offset = None  # sarc files with zero offset are not in file, but reference hash value
            cnode = VfsNode(
                v_hash_type=db.file_hash_type,
                v_hash=se.v_hash, v_path=se.v_path, ext_hash=se.file_ext_hash,
                pid=node.uid, index=se.index,
                offset=offset, size_c=se.length, size_u=se.length,
            )

            db.node_add(cnode)
            db.propose_string(cnode.v_path, node)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_global_gdcc(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing global gdcc": gdc/global.gdcc')

        # special case starting point for runtime
        adf = db.node_read_adf(node)

        cnode_name = b'gdc/global.gdc.DECA'
        cnode = VfsNode(
            v_hash=db.file_hash(cnode_name),
            v_hash_type=db.file_hash_type,
            v_path=cnode_name,
            file_type=FTYPE_GDCBODY, pid=node.uid,
            offset=adf.table_instance[0].offset,
            size_c=adf.table_instance[0].size,
            size_u=adf.table_instance[0].size,
        )
        db.node_add(cnode)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_global_gdcc_body(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing global gdcc body": gdc/global.gdcc.DECA')

        pnode = db.db().node_where_uid(node.pid)
        adf = db.node_read_adf(pnode)

        for entry in adf.table_instance_values[0]:
            if isinstance(entry, GdcArchiveEntry):
                # self.logger.log('GDCC: {} {}'.format(entry.v_hash_to_str(), entry.v_path))
                adf_type = entry.adf_type_hash
                file_type = None
                if adf_type is not None:
                    file_type = FTYPE_ADF_BARE
                    # self.logger.log('ADF_BARE: Need Type: {:08x} {}'.format(adf_type, entry.v_path))
                cnode = VfsNode(
                    v_hash_type=db.file_hash_type,
                    v_hash=entry.v_hash, pid=node.uid, index=entry.index,
                    offset=entry.offset, size_c=entry.size, size_u=entry.size, v_path=entry.v_path,
                    file_type=file_type, adf_type=adf_type)
                db.node_add(cnode)
                db.propose_string(cnode.v_path, node)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_resource_bundle(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing ResourceBundle: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        with ArchiveFile(db.db().file_obj_from(node)) as f:
            index = 0
            while f.tell() < node.size_u:
                v_hash = f.read_u32()
                ext_hash = f.read_u32()
                size = f.read_u32()
                offset = f.tell()
                buffer = f.read(size)

                cnode = VfsNode(
                    v_hash_type=db.file_hash_type,
                    v_hash=v_hash, pid=node.uid, index=index,
                    offset=offset, size_c=size, size_u=size,
                    ext_hash=ext_hash)
                index += 1

                db.node_add(cnode)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_adf_initial(self, node: VfsNode, db: DbWrap):
        if print_node_info:
            self._comm.trace('Processing Adf Initial: {} {} {}'.format(node.uid, node.v_hash_to_str, node.v_path))

        try:
            adf = db.node_read_adf(node)

            for sh in adf.table_stringhash:
                db.propose_string(sh.value, node)

                rp = remove_prefix_if_present(b'intermediate/', sh.value)
                if rp is not None:
                    db.propose_string(rp, node)

                rp = remove_suffix_if_present(b'.stop', sh.value)
                if rp is None:
                    rp = remove_suffix_if_present(b'.play', sh.value)

                if rp is not None:
                    # self.logger.log('Found possible wavc file from: {}'.format(sh.value))
                    for lng in language_codes:
                        fn = b'sound/dialogue/' + lng.encode('ascii') + b'/' + rp + b'.wavc'
                        db.propose_string(fn, node, possible_file_types=[FTYPE_FSB5C])

            for sh in adf.found_strings:
                db.propose_string(sh, node)
                rp = remove_prefix_if_present(b'intermediate/', sh)
                if rp is not None:
                    db.propose_string(rp, node)

            for sh in adf.table_name:
                db.propose_string(sh[1], node, is_field_name=True)

            if len(adf.table_instance_values) > 0 and \
                    adf.table_instance_values[0] is not None and \
                    isinstance(adf.table_instance_values[0], dict):
                obj0 = adf.table_instance_values[0]

                fns = []
                # self name patch files
                if 'PatchLod' in obj0 and 'PatchPositionX' in obj0 and 'PatchPositionZ' in obj0:
                    for prefix in db.db().game_info.world_patches:
                        fn = prefix + 'patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                            obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                        fns.append(fn)

                    for prefix in db.db().game_info.world_occluders:
                        fn = prefix + 'patch_{:02d}_{:02d}_{:02d}.streampatch'.format(
                            obj0['PatchLod'], obj0['PatchPositionX'], obj0['PatchPositionZ'])
                        fns.append(fn)

                if adf.table_instance[0].name == b'NavHeightfield':
                    fns = fns + self.nav_height_field_possible_names

                # self name environc files
                if adf.table_instance[0].name == b'environ':
                    fn = 'environment/weather/{}.environc'.format(obj0['Name'].decode('utf-8'))
                    fns.append(fn)
                    fn = 'environment/presets/{}.environc'.format(obj0['Name'].decode('utf-8'))
                    fns.append(fn)
                    fn = 'environment/{}.environc'.format(obj0['Name'].decode('utf-8'))
                    fns.append(fn)

                found_any = False
                for fne in fns:
                    if isinstance(fne, str):
                        fn = fne
                        fnh = self._vfs.file_hash(fn)
                    else:
                        fn = fne[0]
                        fnh = fne[1]

                    if node.v_hash == fnh:
                        if node.v_path is None:
                            node.v_path = fn
                        db.propose_string(fn, node, possible_file_types=[FTYPE_ADF, FTYPE_ADF_BARE])
                        found_any = True

                if len(fns) > 0 and not found_any:
                    self._comm.log('COULD NOT MATCH GENERATED FILE NAME {} {}'.format(node.v_hash_to_str(), fns[0]))

            # only mark as processed if AdfTypeMissing exception did not happen
            node.processed_file_set(True)
            db.node_update(node)
            return True

        except AdfTypeMissing as ae:
            self._comm.log('Missing Type {:08x} in {} {} {}'.format(
                ae.type_id, node.v_hash_to_str(), node.v_path, node.p_path))
        return False

    def process_rtpc_initial(self, node: VfsNode, db: DbWrap):
        if print_node_info:
            self._comm.trace('Processing RTPC Initial: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        with db.db().file_obj_from(node) as f:
            buf = f.read(node.size_u)

        rtpc = Rtpc()
        with io.BytesIO(buf) as f:
            rtpc.deserialize(f)

        rnodelist = [rtpc.root_node]

        while len(rnodelist) > 0:
            rnode = rnodelist.pop(0)

            for c in rnode.child_table:
                rnodelist.append(c)

            for p in rnode.prop_table:
                if p.type == k_type_str:
                    s = p.data
                    db.propose_string(s, node)

                    fn, ext = os.path.splitext(s)
                    if ext in {b'.tga', b'.dds'}:
                        db.propose_string(fn + b'.ddsc', node, possible_file_types=[FTYPE_AVTX, FTYPE_DDS])
                    elif ext == b'.skeleton':
                        db.propose_string(fn + b'.bsk', node, possible_file_types=[FTYPE_TAG0])
                    elif ext == b'.ragdoll':
                        db.propose_string(fn + b'.brd', node, possible_file_types=[FTYPE_TAG0])
                        db.propose_string(fn + b'.ragdolsettingsc', node, possible_file_types=[FTYPE_ADF])
                    elif ext == b'.al':
                        db.propose_string(fn + b'.afsmb', node, possible_file_types=[FTYPE_RTPC])
                        db.propose_string(fn + b'.asb', node, possible_file_types=[FTYPE_RTPC])
                    elif ext == b'.model_xml':
                        db.propose_string(fn + b'.model_xmlc', node)
                        db.propose_string(fn + b'.model.xml', node)
                        db.propose_string(fn + b'.model.xmlc', node)
                        db.propose_string(fn + b'.xml', node)
                        db.propose_string(fn + b'.xmlc', node)
                        db.propose_string(fn + b'.modelc', node)
                    elif ext == b'.bik':
                        db.propose_string(s + b'c', node, possible_file_types=[FTYPE_BINK_BIK, FTYPE_BINK_KB2])
                    elif len(ext) > 0:
                        db.propose_string(s + b'c', node, possible_file_types=[FTYPE_ADF])

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_gfx_initial(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing GFX Initial: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        with db.db().file_obj_from(node) as f:
            buffer = f.read(node.size_u)

        gfx = Gfx.from_bytes(buffer)

        image_tags = {Gfx.TagType.gfx_define_external_image, Gfx.TagType.gfx_define_external_image2}
        for tag in gfx.zlib_body.tags:
            if Gfx.TagType.gfx_exporter_info == tag.record_header.tag_type:
                db.propose_string(f'ui/{tag.tag_body.name}.gfx', node, possible_file_types=[FTYPE_GFX])
                for ii in range(255):
                    fn = 'ui/{}_i{:x}.ddsc'.format(tag.tag_body.name, ii)
                    db.propose_string(fn, node, possible_file_types=[FTYPE_AVTX, FTYPE_DDS])

            elif tag.record_header.tag_type in image_tags:
                fn = tag.tag_body.file_name
                fn = os.path.basename(fn)
                fn, ext = os.path.splitext(fn)
                fn = f'ui/{fn}.ddsc'
                db.propose_string(fn, node, possible_file_types=[FTYPE_AVTX, FTYPE_DDS])

            elif Gfx.TagType.import_assets2 == tag.record_header.tag_type:
                fn = tag.tag_body.url
                fn = os.path.basename(fn)
                fn, ext = os.path.splitext(fn)
                db.propose_string(f'ui/{tag.tag_body.url}', node, possible_file_types=[FTYPE_GFX])
                db.propose_string(f'ui/{fn}.gfx', node, possible_file_types=[FTYPE_GFX])

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_txt_initial(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing TXT Initial: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        with db.db().file_obj_from(node) as f:
            buffer = f.read(node.size_u)

        json = load_json(buffer)

        # Parse {"0":[]. "1":[]}
        if isinstance(json, dict) and '0' in json and '1' in json:
            for k, v in json.items():
                for item in v:
                    db.propose_string(item, node)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_gtoc(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing gt0c Initial: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        with db.db().file_obj_from(node) as f:
            buffer = f.read(node.size_u)

        archives, all_paths = process_buffer_gtoc(buffer, node.uid)

        for path in all_paths:
            db.propose_string(path, parent_node=node)

        db.gtoc_archive_add(archives)

        node.processed_file_set(True)
        db.node_update(node)
        return True

    def process_garc(self, node: VfsNode, db: DbWrap):
        self._comm.trace('Processing garc Initial: {} {} {}'.format(node.uid, node.v_hash_to_str(), node.v_path))

        hash32 = None
        hash64 = None
        string = node.v_path
        if db.db().game_info.file_hash_size == 4:
            hash32 = node.v_hash
        elif db.db().game_info.file_hash_size == 8:
            hash64 = node.v_hash
        else:
            raise NotImplementedError(f'process_garc: Hash size of {db.db().game_info.file_hash_size} not handled')

        # find possible hash strings for node
        hash_strings = db.db().hash_string_match(hash32=hash32, hash64=hash64, string=string)

        gtoc_archives = []
        for rowid, string, hash32, hash48, hash64, ext_hash32 in hash_strings:
            results = db.db().gtoc_archive_where_hash32_magic(path_hash32=hash32, magic=node.magic)
            gtoc_archives = gtoc_archives + results

        if len(gtoc_archives) == 0:
            self._comm.trace('No gtoc archives found for {} {} {}'.format(
                node.uid, node.v_hash_to_str(), node.v_path))
        elif len(gtoc_archives) > 1:
            self._comm.log('TOO MANY!!! {} gtoc archives found for {} {} {}'.format(
                len(gtoc_archives), node.uid, node.v_hash_to_str(), node.v_path))
        else:
            node.file_type = FTYPE_GARC

            gtoc_archive: GtocArchiveEntry = gtoc_archives[0]

            file_entry: GtocFileEntry
            for fei, file_entry in enumerate(gtoc_archive.file_entries):
                v_hash = db.db().file_hash(file_entry.path)
                child = VfsNode(
                    v_hash_type=db.file_hash_type,
                    v_hash=v_hash,
                    v_path=file_entry.path,
                    ext_hash=file_entry.ext_hash32,
                    size_c=file_entry.file_size,
                    size_u=file_entry.file_size,
                    pid=node.uid,
                    offset=file_entry.offset_in_archive,
                    index=fei,
                )

                db.node_add(child)

            node.processed_file_set(True)
            db.node_update(node)
            return True

        return False

    def process_vhash_final(self, v_hash_in, db: DbWrap):
        nodes = db.db().nodes_where_match(v_hash=v_hash_in)

        if db.file_hash_type == v_hash_type_4:
            hash_strings = db.db().hash_string_match(hash32=v_hash_in)
        elif db.file_hash_type == v_hash_type_8:
            hash_strings = db.db().hash_string_match(hash64=v_hash_in)
        else:
            raise NotImplementedError('Unhandled Hash Type {}'.format(db.file_hash_type))

        missed_vpaths = set()
        h4ref_map = {}
        for rowid, v_path, _, _, _, _ in hash_strings:
            missed_vpaths.add(v_path)
            h4ref_map[rowid] = db.db().hash_string_references_match(hash_row_id=rowid)

        # h4rowid, src_node, is_adf_field_name, used_at_runtime, possible_ftypes in h4ref

        if len(nodes) > 0:
            node: VfsNode
            for node in nodes:
                if node.is_valid():
                    updated = False

                    if node.file_type is None:
                        ftype_int = ftype_list[FTYPE_NO_TYPE]
                    else:
                        ftype_int = ftype_list[node.file_type]

                    for rowid, v_path, _, _, _, _ in hash_strings:
                        h4ref = h4ref_map[rowid]

                        if node.v_path is None:
                            for _, src_node, _, _, possible_ftypes in h4ref:
                                if possible_ftypes is None or possible_ftypes == 0:
                                    possible_ftypes = ftype_list[FTYPE_ANY_TYPE]

                                if (ftype_int & possible_ftypes) != 0:
                                    self._comm.trace('v_path:add  {} {} {} {} {}'.format(
                                        node.v_hash_to_str(), v_path, node.file_type, possible_ftypes, src_node))
                                    node.v_path = v_path
                                    updated = True
                                    break
                                else:
                                    self._comm.log('v_path:skip {} {} {} {} {}'.format(
                                        node.v_hash_to_str(), v_path, node.file_type, possible_ftypes, src_node))

                        if node.v_path == v_path:
                            for _, _, _, used_at_runtime, _ in h4ref:
                                if used_at_runtime:
                                    node.used_at_runtime_depth = 0
                                    updated = True
                                    break

                    if node.file_type is None and node.v_path is not None:
                        file, ext = os.path.splitext(node.v_path)
                        if ext[0:4] == b'.atx':
                            node.file_type = FTYPE_ATX
                            updated = True
                        elif ext == b'.hmddsc':
                            node.file_type = FTYPE_HMDDSC
                            updated = True

                    missed_vpaths.discard(node.v_path)

                    if node.ext_hash is None and node.v_path is not None:
                        file, ext = os.path.splitext(node.v_path)
                        node.ext_hash = self._vfs.ext_hash(ext)
                        updated = True

                    if updated:
                        db.node_update(node)

        for v_path in missed_vpaths:
            v_hash = db.file_hash(v_path)
            self._comm.trace('v_path:miss {} {:016X}'.format(v_path, np.uint64(v_hash)))

        return True

        # found_vpaths = list(found_vpaths)
        # found_vpaths.sort()
        # with open(self.working_dir + 'found_vpaths.txt', 'a') as f:
        #     for vp in found_vpaths:
        #         f.write('{}\n'.format(vp.decode('utf-8')))

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
        # self.logger.log('fill in v_paths, mark extensions identified files as file_type')
        #
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION')
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.v_hash is not None:
        #         hid = node.v_hash
        #         if node.v_path is not None:
        #             if hid in self.map_hash_to_vpath:
        #                 if self.map_hash_to_vpath[hid] != node.v_path:
        #                     self.logger.trace('HASH CONFLICT ARCHIVE: {:08X}: {} != {}'.format(hid, self.map_hash_to_vpath[hid], node.v_path))
        #                     self.hash_bad[hid] = (self.map_hash_to_vpath[hid], node.v_path)
        #             else:
        #                 self.map_hash_to_vpath[hid] = node.v_path
        #                 self.map_vpath_to_hash[node.v_path] = hid
        # self.logger.log('PROCESS BASELINE VNODE INFORMATION: found {} hashes, {} mapped'.format(len(self.hash_present), len(self.map_hash_to_vpath)))
        #
        # for idx in range(len(self.table_vfsnode)):
        #     node = self.table_vfsnode[idx]
        #     if node.is_valid() and node.v_hash is not None and node.v_path is None:
        #         if node.v_hash in self.map_hash_to_vpath:
        #             node.v_path = self.map_hash_to_vpath[node.v_hash]
        #
        #     if node.is_valid() and node.v_hash is not None:
        #         if node.file_type not in {FTYPE_ARC, FTYPE_TAB}:
        #             if node.v_hash in self.map_hash_to_vpath:
        #                 self.hash_map_present.add(node.v_hash)
        #             else:
        #                 self.hash_map_missing.add(node.v_hash)
        #
        #     if node.is_valid() and node.v_path is not None:
        #         if os.path.splitext(node.v_path)[1][0:4] == b'.atx':
        #             if node.file_type is not None:
        #                 raise Exception('ATX marked as non ATX: {}'.format(node.v_path))
        #             node.file_type = FTYPE_ATX
        #
        #         lst = self.map_vpath_to_vfsnodes.get(node.v_path, [])
        #         if len(lst) > 0 and lst[0].offset is None:  # Do not let symlink be first is list # TODO Sort by accessibility
        #             lst = [node] + lst
        #         else:
        #             lst.append(node)
        #         self.map_vpath_to_vfsnodes[node.v_path] = lst


class MultiProcessVfsBase:
    def __init__(self, name, q_in: multiprocessing.Queue, q_out: multiprocessing.Queue):
        self.name = name
        self.q_in = q_in
        self.q_out = q_out

    def send(self, cmd, *params):
        self.q_out.put((self.name, cmd, params, ))

    def log(self, msg):
        self.send('log', msg)

    def trace(self, msg):
        self.send('debug', msg)

    def status(self, i, n):
        self.send('status', i, n)

    def exception(self, exc):
        self.send('exception', exc)

    def run(self, processor: Processor):
        keep_running = True
        while keep_running:
            try:
                cmd = self.q_in.get(block=True, timeout=1.0)
                params = cmd[1]
                cmd = cmd[0]

                if cmd is not None:
                    self.trace('Processing Command "{}({})"'.format(cmd, len(params)))

                    if cmd == 'exit':
                        keep_running = False
                    else:
                        result = processor.process_command(cmd, params)
                        self.send('cmd_done', cmd, result)
            except queue.Empty:
                pass


def run_mp_vfs_base(name, project_file, working_dir, q_in, q_out):
    try:
        p = MultiProcessVfsBase(name, q_in, q_out)
        vfs = VfsDatabase(project_file, working_dir, p)
        processor = Processor(vfs, p)
        p.run(processor)
        vfs.shutdown()
    except:
        ei = sys.exc_info()
        q_out.put((name, 'exception', [ei[0], ei[1], traceback.format_tb(ei[2])], ))

    q_out.put((name, 'process_done', [],))
