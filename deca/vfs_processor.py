import os
import re
import csv
import time

import deca.ff_rtpc

from .vfs_db import VfsDatabase, VfsNode, db_to_vfs_node, language_codes
from .db_wrap import DbWrap
from .vfs_commands import MultiProcessControl
from .game_info import determine_game
from .ff_types import *
from .ff_adf import AdfDatabase
from .util import Logger, make_dir_for_file
from .hashes import hash32_func


def vfs_structure_new(filename):
    exe_path = filename[0]
    game_dir, exe_name = os.path.split(exe_path)
    game_dir = os.path.join(game_dir, '')

    game_info = determine_game(game_dir, exe_name)
    vfs = None

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
        VfsDatabase.__init__(self, project_file, working_dir, logger, init_display=True)
        self.last_status_update = None

    def log(self, msg):
        self.logger.log(msg)

    def trace(self, msg):
        self.logger.trace(msg)

    def status(self, i, n):
        curr_time = time.time()
        if self.last_status_update is None or self.last_status_update + 5 < curr_time:
            self.last_status_update = curr_time
            self.log('Completed {} of {}'.format(i, n))

    def find_initial_files(self, debug=False):
        self.logger.log('Add EXE files')
        exe_path = os.path.join(self.game_info.game_dir, self.game_info.exe_name)
        f_size = os.stat(exe_path).st_size
        node = VfsNode(file_type=FTYPE_EXE, p_path=exe_path, size_u=f_size, size_c=f_size, offset=0)
        self.determine_ftype(node)
        self.node_add_one(node)

        self.logger.log('Add unarchived files')
        for ua_file in self.game_info.unarchived_files():
            f_size = os.stat(ua_file).st_size
            v_path = os.path.basename(ua_file).encode('utf-8')
            v_hash = deca.hashes.hash32_func(v_path)
            node = VfsNode(v_hash=v_hash, v_path=v_path, p_path=ua_file, size_u=f_size, size_c=f_size, offset=0)
            self.determine_ftype(node)
            self.node_add_one(node)

        self.logger.log('Add TAB / ARC files')
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
                    if file.endswith('.tab'):
                        ifns.append(file[0:-4])
                ifns.sort(key=game_file_to_sortable_string)
                for ifn in ifns:
                    input_files.append(os.path.join(fcat, ifn))

        for ta_file in input_files:
            inpath = os.path.join(ta_file)
            file_arc = inpath + '.arc'
            f_size = os.stat(file_arc).st_size
            node = VfsNode(file_type=FTYPE_ARC, p_path=file_arc, size_u=f_size, size_c=f_size, offset=0)
            self.determine_ftype(node)
            self.node_add_one(node)

    def process(self, debug=False):
        inner_loop = [
            [self.process_by_ftype_match, (FTYPE_EXE, 'process_exe')],
            [self.process_by_ftype_match, (FTYPE_ARC, 'process_arc')],
            [self.process_by_ftype_match, (FTYPE_TAB, 'process_tab')],
            [self.process_by_ftype_match, (FTYPE_SARC, 'process_sarc')],
            [self.process_by_vhash_match, (deca.hashes.hash32_func(b'gdc/global.gdcc'), 'process_global_gdcc')],
            [self.process_by_ftype_match, (FTYPE_GDCBODY, 'process_global_gdcc_body')],
            [self.process_by_ext_hash_match, (deca.hashes.hash32_func(b'.resourcebundle'), 'process_resource_bundle')],
            [self.process_by_vpath_endswith, (b'.resourcebundle', 'process_resource_bundle')],
            [self.process_by_ftype_match, (FTYPE_ADF, 'process_adf_initial')],
            [self.process_by_ftype_match, (FTYPE_ADF_BARE, 'process_adf_initial')],
            [self.process_by_ftype_match, (FTYPE_RTPC, 'process_rtpc_initial')],
            [self.process_by_ftype_match, (FTYPE_GFX, 'process_gfx_initial')],
            [self.process_by_ftype_match, (FTYPE_TXT, 'process_txt_initial')],
            [self.process_by_ftype_match, (FTYPE_SYMLINK, 'process_symlink')],
        ]

        version = self.db_query_one("PRAGMA user_version")[0]
        if version < 1:
            self.db_reset()
            self.db_execute_one("PRAGMA user_version = 1;")
            self.find_initial_files(debug=debug)

        self.process_remove_temporary_nodes()

        self.find_vpath_procmon_dir()
        self.find_vpath_resources()
        self.find_vpath_guess()

        outer_phase_id = 0
        inner_loop_count = 2
        while inner_loop_count > 1:
            outer_phase_id = outer_phase_id + 1
            self.logger.log('Phase {}: Begin'.format(outer_phase_id))

            inner_processed_nodes = set()
            inner_phase_id = 0
            changed = True
            inner_loop_count = 0
            while changed:
                inner_loop_count += 1
                inner_phase_id = inner_phase_id + 1

                self.logger.log('Phase {}.{}: File Process Begin'.format(outer_phase_id, inner_phase_id))

                processed_nodes = set()

                for ops in inner_loop:
                    result = ops[0](*(ops[1]))
                    processed_nodes = processed_nodes.union(result)

                self.logger.log('Phase {}.{}: File Process End'.format(outer_phase_id, inner_phase_id))

                changed = processed_nodes != inner_processed_nodes
                inner_processed_nodes = processed_nodes

            if inner_loop_count > 1:
                self.find_vpath_by_assoc()
                self.process_all_vhashes('process_vhash_final')

            self.logger.log('Phase {}: End'.format(outer_phase_id))

        self.update_used_depths()
        self.dump_vpaths()
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
                for v_path in vpaths:
                    f.write('{}\n'.format(v_path))

    def dump_status(self):
        # possible different vpaths with same hash, uncommon
        q = "SELECT DISTINCT hash32, COUNT(*) c FROM core_hash_strings GROUP BY hash32 HAVING c > 1;"
        dup_hash4 = self.db_query_all(q)
        for v_hash, c in dup_hash4:
            q = "SELECT DISTINCT hash32, string FROM core_hash_strings WHERE hash32 = (?)"
            hashes = self.db_query_all(q, [v_hash])
            fcs = []
            gtz_count = 0
            for h, s in hashes:
                q = "SELECT DISTINCT uid FROM core_vnodes WHERE v_path = (?)"
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
        q = "SELECT DISTINCT v_hash, v_path, COUNT(*) c FROM core_vnodes GROUP BY v_hash, v_hash HAVING c > 1;"
        dup_nodes = self.db_query_all(q)
        dup_map = {}
        dup_count = {}
        for v_hash, v_path, c in dup_nodes:
            if v_hash not in dup_map:
                dup_map[v_hash] = {v_path}
            else:
                dup_map[v_hash].add(v_path)
                dup_count[v_hash] = len(dup_map[v_hash])

        for v_hash, count in dup_count.items():
            vpaths = dup_map[v_hash]
            for v_path in vpaths:
                self.logger.log(f'SUMMARY: Duplicate Node Hashes: {v_hash:08x} {v_path}')

        # ADF type summary
        adf_db = AdfDatabase()
        adf_db.load_from_database(self)

        missing_types = set()
        for t, uid in adf_db.type_missing:
            missing_types.add(t)
            node: VfsNode = self.node_where_uid(uid)
            self.logger.log('SUMMARY: Missing Type {:08x} in {:08X} {}'.format(t, node.v_hash, node.v_path))

        self.logger.log(f'SUMMARY: Missing Types: {len(missing_types)} ')

        # unmatched summary, common
        q = "SELECT v_hash FROM core_vnodes WHERE v_path IS NULL"
        nodes_no_vpath = self.db_query_all(q)
        nodes_no_vpath = [r[0] for r in nodes_no_vpath]
        nodes_no_vpath_set = set(nodes_no_vpath)
        self.logger.log(f'SUMMARY: Unmatched Nodes: {len(nodes_no_vpath)}')
        self.logger.log(f'SUMMARY: Unmatched Path Hashes: {len(nodes_no_vpath_set)}')

    def src_indexes_process(self, src_indexes):
        indexes = []
        nodes = {}
        for uid, v_hash, processed in src_indexes:
            if v_hash is None and not processed:
                # handle physical only files with no vpath (EXE, ARC, TAB, EXTERNALS)
                indexes.append(uid)
            else:
                # normal case of files that have v_hashes and v_paths (possibly)
                info = nodes.get(v_hash, None)
                if info is None:
                    nodes[v_hash] = (uid, processed)
                elif processed and not info[1]:
                    nodes[v_hash] = (uid, processed)

        done_set = set()
        for k, v in nodes.items():
            uid, processed = v
            if processed:
                done_set.add(k)
            else:
                indexes.append(uid)

        return indexes, done_set

    def process_by_ftype_match(self, f_type, cmd):
        self.logger.log('PROCESS: F_TYPE = {}: Begin'.format(f_type))

        src_indexes = self.nodes_where_f_type_select_uid_v_hash_processed(f_type)
        indexes, done_set = self.src_indexes_process(src_indexes)
        if indexes:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, indexes, step_id=f_type)

        self.logger.log('PROCESS: F_TYPE = {}: End: Already Processed: {}, Additional: {}'.format(
            f_type, len(done_set), len(indexes)))

        return indexes

    def process_by_vhash_match(self, v_hash, cmd):
        self.logger.log('PROCESS: V_HASH = 0x{:08X}: Begin'.format(v_hash))

        src_indexes = self.nodes_where_v_hash_select_uid_v_hash_processed(v_hash)
        indexes, done_set = self.src_indexes_process(src_indexes)
        if indexes:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, indexes, step_id=f'v_hash = {v_hash}')

        self.logger.log('PROCESS: V_HASH = 0x{:08X}: End: Already Processed: {}, Additional: {}'.format(
            v_hash, len(done_set), len(indexes)))

        return indexes

    def process_by_ext_hash_match(self, ext_hash, cmd):
        self.logger.log('PROCESS: EXT_HASH = 0x{:08X}: Begin'.format(ext_hash))

        src_indexes = self.nodes_where_ext_hash_select_uid_v_hash_processed(ext_hash)
        indexes, done_set = self.src_indexes_process(src_indexes)
        if indexes:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, indexes, step_id=f'ext_hash = {ext_hash}')

        self.logger.log('PROCESS: EXT_HASH = 0x{:08X}: End: Already Processed: {}, Additional: {}'.format(
            ext_hash, len(done_set), len(indexes)))

        return indexes

    def process_by_vpath_endswith(self, suffix, cmd):
        self.logger.log('PROCESS: ENDS_WITH = {}: Begin'.format(suffix))

        src_indexes = self.nodes_where_vpath_endswith_select_uid_v_hash_processed(suffix)
        indexes, done_set = self.src_indexes_process(src_indexes)
        if indexes:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, indexes, step_id=f'endswith = {suffix}')

        self.logger.log('PROCESS: ENDS_WITH = {}: End: Already Processed: {}, Additional: {}'.format(
            suffix, len(done_set), len(indexes)))

        return indexes

    def process_all_vhashes(self, cmd):
        self.logger.log('PROCESS: VHASHes: Begin')
        vhashes = self.nodes_select_distinct_vhash()
        if len(vhashes) > 0:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, vhashes, step_id='v_hash')
        self.logger.log('PROCESS: VHASHes: End: Total VHASHes {}'.format(len(vhashes)))

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

            with DbWrap(self, logger=self) as db:
                for s in custom_strings:
                    db.propose_string(s.strip().encode('ascii'), None, used_at_runtime=True)

        self.logger.log('STRINGS FROM HASH FROM PROCMON DIR: Total {} strings'.format(len(custom_strings)))

    def find_vpath_resources(self):
        fns = [
            (False, './resources/strings.txt'),
            (False, './resources/{}/strings.txt'.format(self.game_info.game_id)),
            (True, './resources/{}/strings_procmon.txt'.format(self.game_info.game_id)),
        ]

        search_dir = './resources/ghidra_strings'
        if os.path.isdir(search_dir):
            for file in os.listdir(search_dir):
                fns.append((False, os.path.join(search_dir, file)))

        string_count = 0
        with DbWrap(self, logger=self) as db:
            for used_at_runtime, fn in fns:
                if os.path.isfile(fn):
                    self.logger.log('STRINGS FROM RESOURCES: Loading possible strings from {}'.format(fn))
                    with open(fn, 'rb') as f:
                        custom_strings = f.readlines()
                    custom_strings = set(custom_strings)
                    string_count += len(custom_strings)
                    self.logger.log('STRINGS FROM RESOURCES: Loaded {} strings'.format(len(custom_strings)))
                    for s in custom_strings:
                        db.propose_string(s.strip(), None, used_at_runtime=used_at_runtime)

        self.logger.log('STRINGS FROM RESOURCES: Total {} strings'.format(string_count))

    def find_vpath_guess(self):
        self.logger.log('STRINGS BY GUESSING: ...')
        guess_strings = {}
        guess_strings['gdc/global.gdcc'] = FTYPE_ADF

        for res_i in range(10):
            guess_strings['settings/hp_settings/reserve_{}.bin'.format(res_i)] = FTYPE_RTPC
            guess_strings['settings/hp_settings/reserve_{}.bl'.format(res_i)] = FTYPE_SARC

        # maps
        for map_prefix in self.game_info.map_prefixes:
            guess_strings[map_prefix + 'world_map.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]
            for zoom_i in self.game_info.map_zooms:
                for index in range(self.game_info.map_max_count):
                    guess_strings[map_prefix + f'zoom{zoom_i}/{index}.ddsc'] = [FTYPE_AVTX, FTYPE_DDS]

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

        with DbWrap(self, logger=self) as db:
            for k, v in guess_strings.items():
                fn = k
                fn = fn.encode('ascii')
                db.propose_string(fn, None, possible_file_types=v)

        self.logger.log('STRINGS BY GUESSING: Total {} guesses'.format(len(guess_strings)))

    def find_vpath_by_assoc(self):
        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: epe/ee, blo/bl/nl/fl/nl.mdic/fl.mdic, mesh*/model*, avtx/atx?]')
        pair_exts = self.game_info.file_assoc()

        all_hash4 = self.hash_string_select_distinct_string()
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

        with DbWrap(self, logger=self) as db:
            for k, v in assoc_strings.items():
                fn = k
                fh = hash32_func(fn)
                if fh in hash_present:
                    db.propose_string(fn, None, possible_file_types=v)

        self.logger.log('STRINGS BY FILE NAME ASSOCIATION: Found {}'.format(len(assoc_strings)))

    def update_used_depths(self):
        level = 0
        keep_going = True
        while keep_going:
            keep_going = False
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

            with DbWrap(self, logger=self) as db:
                for child_node in child_nodes:
                    if child_node.used_at_runtime_depth is None or child_node.used_at_runtime_depth > level:
                        keep_going = True
                        child_node.used_at_runtime_depth = level
                        db.node_update(child_node)

    def process_remove_temporary_nodes(self):
        uids = self.nodes_where_temporary_select_uid(True)
        uids = [(uid, ) for uid in uids]
        if uids:
            self.nodes_delete_where_uid(uids)

    def external_file_add(self, filename, is_temporary_file=True):
        if os.path.isfile(filename):
            f_size = os.stat(filename).st_size

            v_path = filename.replace(':', '/')
            v_path = v_path.replace('\\', '/')
            v_path = ('__EXTERNAL_FILES__' + v_path).encode('ascii')
            v_hash = deca.hashes.hash32_func(v_path)

            # tag atx file type since they have no header info

            vnode = VfsNode(
                v_hash=v_hash, v_path=v_path, p_path=filename,
                size_u=f_size, size_c=f_size, offset=0, is_temporary_file=is_temporary_file)
            self.determine_ftype(vnode)
            self.node_add_one(vnode)

            self.logger.log('ADDED {} TO EXTERNAL FILES'.format(filename))
        else:
            self.logger.log('FAILED TO OPEN:  {}'.format(filename))
