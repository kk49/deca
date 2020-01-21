import os
import multiprocessing
import queue
import re
import csv
import time

from deca.vfs_db import VfsDatabase, VfsNode, propose_h4, db_to_vfs_node
from deca.vfs_commands import run_mp_vfs_base, language_codes, MultiProcessVfsBase
from deca.game_info import GameInfoGZ, GameInfoGZB, GameInfoTHCOTW, GameInfoJC3, GameInfoJC4
from deca.ff_types import *
import deca.ff_rtpc
from deca.ff_adf import AdfDatabase
from deca.util import Logger, make_dir_for_file
from deca.hash_jenkins import hash_little
from deca.ff_determine import determine_file_type_and_size


def vfs_structure_new(filename):
    exe_path = filename[0]
    game_dir, exe_name = os.path.split(exe_path)
    game_dir = os.path.join(game_dir, '')

    game_info = None
    vfs = None
    if exe_name.find('GenerationZero') >= 0 and game_dir.find('BETA') >= 0:
        game_info = GameInfoGZB(game_dir, exe_name)
    elif exe_name.find('GenerationZero') >= 0:
        game_info = GameInfoGZ(game_dir, exe_name)
    elif exe_name.find('theHunterCotW') >= 0:
        game_info = GameInfoTHCOTW(game_dir, exe_name)
    elif exe_name.find('JustCause3') >= 0:
        game_info = GameInfoJC3(game_dir, exe_name)
    elif exe_name.find('JustCause4') >= 0:
        game_info = GameInfoJC4(game_dir, exe_name)
    else:
        pass

    if game_info is not None:
        working_dir = '../work/{}/'.format(game_info.game_id)
        project_file = os.path.join(working_dir, 'project.json')
        make_dir_for_file(project_file)
        game_info.save(project_file)
        vfs = vfs_structure_prep(project_file, working_dir)  # , logger=self.logger)

    return vfs


def vfs_structure_open(project_file, logger=None, debug=False):
    working_dir = os.path.join(os.path.split(project_file)[0], '')
    return vfs_structure_prep(project_file, working_dir, logger=logger, debug=debug)


def vfs_structure_prep(project_file, working_dir, logger=None, debug=False):

    if logger is None:
        logger = Logger(working_dir)

    vfs = VfsProcessor(project_file, working_dir, logger)
    vfs.process(debug)
    return vfs


def game_file_to_sortable_string(v):
    if v[0:4] == 'game':
        return 'game{:08}'.format(int(v[4:]))
    else:
        return v


class VfsProcessor(VfsDatabase):
    def __init__(self, project_file, working_dir, logger):
        VfsDatabase.__init__(self, project_file, working_dir, logger)

        self.external_files = set()
        self.progress_update_time_sec = 5.0

        self.mp_q_results = multiprocessing.Queue()
        # assuming hyper-threading exists and slows down processing
        # self.mp_n_processes = 1
        self.mp_n_processes = max(1, 2 * multiprocessing.cpu_count() // 4)
        # self.mp_n_processes = max(1, 3 * multiprocessing.cpu_count() // 4)

        self.mp_processes = {}
        for i in range(self.mp_n_processes):
            name = 'process_{}'.format(i)

            self.logger.log('Create Process: {}'.format(name))
            q_command = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=run_mp_vfs_base, args=(name, project_file, working_dir, q_command, self.mp_q_results))
            self.mp_processes[name] = (name, p, q_command)

            self.logger.log('Process: {}: Start'.format(p))
            p.start()

    def process(self, debug=False):
        version = self.db_query_one("PRAGMA user_version")[0]
        if version < 1:
            self.db_reset()
            self.load_from_archives(debug=debug)
            self.process_by_ftype(FTYPE_ADF, 'process_adf_initial')
            self.process_by_ftype(FTYPE_ADF_BARE, 'process_adf_initial')
            self.process_by_ftype(FTYPE_RTPC, 'process_rtpc_initial')
            self.process_by_ftype(FTYPE_GFX, 'process_gfx_initial')
            self.process_by_ftype(FTYPE_TXT, 'process_txt_initial')
            self.find_vpath_exe()
            self.find_vpath_procmon_dir()
            self.find_vpath_resources()
            self.find_vpath_guess()
            self.find_vpath_by_assoc()
            self.process_by_vhash('process_vhash_final')
            self.update_used_depths()
            self.dump_vpaths()
            self.db_execute_one("PRAGMA user_version = 1;")

        # TODO process any hashless strings in vhash4 and vhash6 table, assume outside program added them for testing

        self.dump_status()
        self.logger.log('PROCESSING: COMPLETE')

    def dump_vpaths(self):
        vpath_file = os.path.join(self.working_dir, 'vpaths.txt')
        vpaths = self.nodes_select_distinct_vpath()
        vpaths = list(set([v for v in vpaths if v is not None]))
        vpaths.sort()
        if not os.path.isfile(vpath_file):
            self.logger.log('CREATING: vpaths.txt')
            with open(vpath_file, 'w') as f:
                for vpath in vpaths:
                    f.write('{}\n'.format(vpath))

    def dump_status(self):
        # possible different vpaths with same hash, uncommon
        q = "SELECT DISTINCT hash, COUNT(*) c FROM core_hash4 GROUP BY hash HAVING c > 1;"
        dup_hash4 = self.db_query_all(q)
        for vhash, c in dup_hash4:
            q = "SELECT DISTINCT hash, string FROM core_hash4 WHERE hash = (?)"
            hashes = self.db_query_all(q, [vhash])
            fcs = []
            gtz_count = 0
            for h, s in hashes:
                q = "SELECT DISTINCT uid FROM core_vnodes WHERE vpath = (?)"
                nodes = self.db_query_all(q, [s])
                fc = len(nodes)
                self.logger.log(f'SUMMARY: Duplicate String4 Hashes: {h:08x} {s}: {fc} nodes')
                fcs.append(len(nodes))
                if fc > 0:
                    gtz_count += 1
            if gtz_count > 1:
                for (h, s), fc in zip(hashes, fcs):
                    self.logger.log(f'WARNING: Duplicate String4 Hashes: {h:08x} {s}: {fc} nodes')

        # nodes with same hash but different paths, rare
        q = "SELECT DISTINCT vpath_hash, vpath, COUNT(*) c FROM core_vnodes GROUP BY vpath_hash, vpath_hash HAVING c > 1;"
        dup_nodes = self.db_query_all(q)
        dup_map = {}
        dup_count = {}
        for vhash, vpath, c in dup_nodes:
            if vhash not in dup_map:
                dup_map[vhash] = {vpath}
            else:
                dup_map[vhash].add(vpath)
                dup_count[vhash] = len(dup_map[vhash])

        for vhash, count in dup_count.items():
            vpaths = dup_map[vhash]
            for vpath in vpaths:
                self.logger.log(f'SUMMARY: Duplicate Node Hashes: {vhash:08x} {vpath}')

        # ADF type summary
        adf_db = AdfDatabase()
        adf_db.load_from_database(self)

        missing_types = set()
        for t, uid in adf_db.type_missing:
            missing_types.add(t)
            node = self.node_where_uid(uid)
            self.logger.log('SUMMARY: Missing Type {:08x} in {:08X} {}'.format(t, node.vhash, node.vpath))

        self.logger.log(f'SUMMARY: Missing Types: {len(missing_types)} ')

        # unmatched summary, common
        q = "SELECT vpath_hash FROM core_vnodes WHERE vpath IS NULL"
        nodes_no_vpath = self.db_query_all(q)
        nodes_no_vpath = [r[0] for r in nodes_no_vpath]
        nodes_no_vpath_set = set(nodes_no_vpath)
        self.logger.log(f'SUMMARY: Unmatched Nodes: {len(nodes_no_vpath)}')
        self.logger.log(f'SUMMARY: Unmatched Path Hashes: {len(nodes_no_vpath_set)}')

    def mp_issue_commands(self, command_list: list, step_id=None, debug=False):
        command_todo = command_list.copy()
        command_active = {}
        command_complete = []

        if step_id is None:
            step_id = ''
        else:
            step_id = ': {}'.format(step_id)

        status = {}
        last_update = None
        start_time = time.time()

        local = False
        if local:
            test = MultiProcessVfsBase('test', self.project_file, self.working_dir, None, self.mp_q_results)
            for command in command_todo:
                test.process_command(command[0], command[1])
        else:
            while (len(command_todo) + len(command_active)) > 0:
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
                    available_procs = set(self.mp_processes.keys()) - set(command_active.keys())
                    proc = available_procs.pop()
                    proc = self.mp_processes[proc]
                    name = proc[0]
                    q_command: queue.Queue = proc[2]
                    command = command_todo.pop(0)
                    command_active[name] = command
                    q_command.put_nowait(command)
                else:
                    try:
                        msg = self.mp_q_results.get(block=False, timeout=1)
                        proc_name = msg[0]
                        proc_cmd = msg[1]
                        proc_params = msg[2]

                        if proc_cmd not in {'trace', 'log', 'status'} and debug:
                            self.logger.log('Manager: received msg {}:{}'.format(proc_name, proc_cmd))

                        if proc_cmd == 'log':
                            self.logger.log('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'trace':
                            self.logger.trace('{}: {}'.format(proc_name, proc_params[0]))
                        elif proc_cmd == 'status':
                            status[proc_name] = proc_params
                        elif proc_cmd == 'cmd_done':
                            command_active.pop(proc_name)
                            command_complete.append([proc_name, proc_params])
                            if debug:
                                self.logger.log('Manager: {} completed {}'.format(proc_name, proc_params))
                        else:
                            print(msg)
                    except queue.Empty:
                        pass

    def load_from_archives(self, debug=False):
        self.logger.log('Process EXE file')

        self.logger.log('find all tab/arc files')
        input_files = []

        dir_in = self.game_info.archive_path()
        dir_found = []

        # add exe to be parsed in normal way
        exe_path = os.path.join(self.game_info.game_dir, self.game_info.exe_name)
        node = VfsNode(ftype=FTYPE_EXE, pvpath=exe_path)
        self.node_add_one(node)

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
            node = VfsNode(
                vhash=vhash, vpath=vpath, pvpath=ua_file, ftype=ftype,
                size_u=fsize, size_c=fsize, offset=0)
            self.determine_ftype(node)
            self.node_add_one(node)

        self.logger.log('process all game tab / arc files')
        for ta_file in input_files:
            inpath = os.path.join(ta_file)
            file_arc = inpath + '.arc'
            node = VfsNode(ftype=FTYPE_ARC, pvpath=file_arc)
            self.node_add_one(node)

        any_change = True
        phase_id = 0
        last_update = None
        processed_nodes = set()
        while any_change:
            phase_id = phase_id + 1

            any_change = False

            new_nodes = set(self.nodes_where_processed_select_uid(0))
            new_nodes = new_nodes - processed_nodes

            if len(new_nodes) > 0:
                self.logger.log('Expand Archives Phase {}: Begin'.format(phase_id))
                any_change = True
                new_nodes_list = list(new_nodes)

                indexes = [new_nodes_list[v::self.mp_n_processes] for v in range(0, self.mp_n_processes)]

                commands = []
                for ii in indexes:
                    commands.append(['process_archives_initial', [ii]])

                self.mp_issue_commands(commands, step_id='Archives')
                processed_nodes = processed_nodes.union(new_nodes)
                self.logger.log('Expand Archives Phase {}: End'.format(phase_id))

    def get_vnode_indexs_from_ftype(self, ftype, process_dups=False):
        indexs = []
        done_set = set()
        src_indexes = self.nodes_where_ftype_select_uid(ftype)
        for idx in src_indexes:
            node = self.node_where_uid(idx)
            if node.is_valid() and node.ftype == ftype and (process_dups or node.vhash not in done_set):
                done_set.add(node.vhash)
                indexs.append(idx)
        return indexs, done_set

    def process_by_ftype(self, ftype, cmd, process_dups=False):
        self.logger.log('PROCESS: FTYPE = {}'.format(ftype))

        indexes, nodes_done = self.get_vnode_indexs_from_ftype(ftype, process_dups)

        if len(indexes) > 0:
            indexes2 = [indexes[v::self.mp_n_processes] for v in range(0, self.mp_n_processes)]

            commands = []
            for idxs in indexes2:
                commands.append([cmd, [idxs]])

            self.mp_issue_commands(commands, step_id=ftype)

        self.logger.log('PROCESS: FTYPE = {}: Total files {}'.format(ftype, len(nodes_done)))

    def process_by_vhash(self, cmd):
        self.logger.log('PROCESS: VHASHes')

        vhashes = self.nodes_select_distinct_vhash()

        if len(vhashes) > 0:
            indexes2 = [vhashes[v::self.mp_n_processes] for v in range(0, self.mp_n_processes)]

            commands = []
            for idxs in indexes2:
                commands.append([cmd, [idxs]])

            self.mp_issue_commands(commands, step_id='vhash')

        self.logger.log('PROCESS: VHASHes: Total VHASHes {}'.format(len(vhashes)))

    def find_vpath_exe(self):
        fn = './resources/{}/all_strings.tsv'.format(self.game_info.game_id)
        if os.path.isfile(fn):
            hash4_to_add = []
            self.logger.log('STRINGS FROM EXE: look for hashable strings in EXE strings from IDA in ./resources/{}/all_strings.tsv'.format(self.game_info.game_id))
            with open(fn, 'rb') as f:
                exe_strings = f.readlines()
            exe_strings = [line.split(b'\t') for line in exe_strings]
            exe_strings = [line[3].strip() for line in exe_strings if len(line) >= 4]
            exe_strings = list(set(exe_strings))
            for s in exe_strings:
                propose_h4(hash4_to_add, s, None)

            hash4_to_add = list(set(hash4_to_add))
            if len(hash4_to_add) > 0:
                self.logger.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
                self.hash4_add_many(hash4_to_add)

            self.logger.log('STRINGS FROM EXE: Found {} strings'.format(len(exe_strings)))

    def find_vpath_procmon_dir(self):
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

            hash4_to_add = []

            for s in custom_strings:
                propose_h4(hash4_to_add, s.strip().encode('ascii'), None, used_at_runtime=True)

            hash4_to_add = list(set(hash4_to_add))
            if len(hash4_to_add) > 0:
                self.logger.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
                self.hash4_add_many(hash4_to_add)

        self.logger.log('STRINGS FROM HASH FROM PROCMON DIR: Total {} strings'.format(len(custom_strings)))

    def find_vpath_resources(self):
        fns = [
            './resources/strings.txt',
            './resources/{}/strings.txt'.format(self.game_info.game_id),
            './resources/{}/strings_procmon.txt'.format(self.game_info.game_id),
        ]
        hash4_to_add = []

        for fn in fns:
            if os.path.isfile(fn):
                self.logger.log('STRINGS FROM RESOURCES: look for hashable strings in {}'.format(fn))
                with open(fn, 'rb') as f:
                    custom_strings = f.readlines()
                    custom_strings = set(custom_strings)
                    for s in custom_strings:
                        propose_h4(hash4_to_add, s.strip(), None, used_at_runtime=True)

        hash4_to_add = list(set(hash4_to_add))
        if len(hash4_to_add) > 0:
            self.logger.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
            self.hash4_add_many(hash4_to_add)

        self.logger.log('STRINGS FROM RESOURCES: Total {} strings'.format(len(hash4_to_add)))

    def find_vpath_guess(self):
        self.logger.log('STRINGS BY GUESSING: ...')
        guess_strings = {}
        guess_strings['gdc/global.gdcc'] = FTYPE_ADF
        guess_strings['textures/ui/world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
        for res_i in range(10):
            guess_strings['settings/hp_settings/reserve_{}.bin'.format(res_i)] = FTYPE_RTPC
            guess_strings['settings/hp_settings/reserve_{}.bl'.format(res_i)] = FTYPE_SARC
            guess_strings['textures/ui/map_reserve_{}/world_map.ddsc'.format(res_i)] = [FTYPE_AVTX, FTYPE_DDS]

            for zoom_i in [1, 2, 3]:
                for index in range(500):
                    fn = 'textures/ui/map_reserve_{}/zoom{}/{}.ddsc'.format(res_i, zoom_i, index)
                    guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for zoom_i in [1, 2, 3]:
            for index in range(500):
                fn = 'textures/ui/warboard_map/zoom{}/{}.ddsc'.format(zoom_i, index)
                guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

        for world_rec in self.game_info.worlds:
            for area_prefix in self.game_info.area_prefixs:
                for i in range(64):
                    fn = world_rec[2] + 'horizonmap/horizon_{}{}.ddsc'.format(area_prefix, i)
                    guess_strings[fn] = [FTYPE_AVTX, FTYPE_DDS]

            for i in range(64):
                for j in range(64):
                    fn = world_rec[0] + 'ai/tiles/{:02d}_{:02d}.navmeshc'.format(i, j)
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

        hash4_to_add = []
        for k, v in guess_strings.items():
            fn = k
            fn = fn.encode('ascii')
            propose_h4(hash4_to_add, fn, None, possible_ftypes=v)

        hash4_to_add = list(set(hash4_to_add))
        if len(hash4_to_add) > 0:
            self.logger.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
            self.hash4_add_many(hash4_to_add)

        self.logger.log('STRINGS BY GUESSING: Total {} guesses'.format(len(guess_strings)))

    def find_vpath_by_assoc(self):
        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: epe/ee, blo/bl/nl/fl/nl.mdic/fl.mdic, mesh*/model*, avtx/atx?]')
        pair_exts = self.game_info.file_assoc()

        all_hash4 = self.hash4_select_distinct_string()
        assoc_strings = {}

        for k in all_hash4:
            file_ext = os.path.splitext(k)
            if len(file_ext[0]) > 0 and len(file_ext[1]) > 0:
                file = file_ext[0]
                ext = file_ext[1]
                for pe in pair_exts:
                    if ext in pe:
                        for pk, pv in pe.items():
                            assoc_strings[file + pk] = pv

        hash_present = set(self.nodes_select_distinct_vhash())
        hash4_to_add = []
        for k, v in assoc_strings.items():
            fn = k
            fh = hash_little(fn)
            if fh in hash_present:
                propose_h4(hash4_to_add, fn, None, possible_ftypes=v)

        hash4_to_add = list(set(hash4_to_add))
        if len(hash4_to_add) > 0:
            self.logger.log('DATABASE: Inserting {} hash 4 strings'.format(len(hash4_to_add)))
            self.hash4_add_many(hash4_to_add)

        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: Found {}'.format(len(assoc_strings)))

    # def find_adf_types_exe_noheader(self):
    #     exe_path = os.path.join(self.game_info.game_dir, self.game_info.exe_name)
    #
    #     with open(exe_path, 'rb') as f:
    #         buffer = f.read(os.stat(exe_path).st_size)
    #
    #     for k, v in self.adf_missing_types.items():
    #         lid = struct.pack('<L', k)
    #         offset = 0
    #         while True:
    #             offset = buffer.find(lid, offset)
    #             if offset < 0:
    #                 break
    #             print('Found {:08X} @ {}'.format(k, offset))
    #
    #             t = TypeDef()
    #             with ArchiveFile(io.BytesIO(buffer)) as f:
    #                 f.seek(offset - 12)  # rewind to begining of type
    #                 t.deserialize(f, {})
    #
    #             offset += 1

    def update_used_depths(self):
        level = 0
        while True:
            self.logger.log('UPDATING USE DEPTH: {}'.format(level))
            # puids = self.db_query_all("SELECT uid FROM core_vnodes WHERE used_at_runtime_depth == (?)", [level])
            # puids = [n[0] for n in puids]
            #
            # if len(puids) == 0:
            #     break

            child_nodes = self.db_query_all(
                """
                SELECT * FROM core_vnodes WHERE 
                    parent_id IN (SELECT uid FROM core_vnodes WHERE used_at_runtime_depth == (?))
                """,
                [level]
            )
            child_nodes = [db_to_vfs_node(n) for n in child_nodes]

            level = level + 1

            nodes_to_update = []
            for child_node in child_nodes:
                if child_node.used_at_runtime_depth is None or child_node.used_at_runtime_depth > level:
                    child_node.used_at_runtime_depth = level
                    nodes_to_update.append(child_node)

            if len(nodes_to_update) > 0:
                self.logger.log('DATABASE: Updating {} nodes'.format(len(nodes_to_update)))
                self.node_update_many(nodes_to_update)
            else:
                break

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
            self.node_add_one(vnode)
            self.node_update_vpath_mapping(vnode)

            self.external_files.add(filename)

            self.logger.log('ADDED {} TO EXTERNAL FILES'.format(filename))
        else:
            self.logger.log('FAILED TO OPEN:  {}'.format(filename))
