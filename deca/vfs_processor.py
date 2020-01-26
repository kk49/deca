import os
import re
import csv
import time

from deca.vfs_db import VfsDatabase, VfsNode, db_to_vfs_node, language_codes
from .db_wrap import DbWrap
from deca.vfs_commands import MultiProcessControl
from deca.game_info import GameInfoGZ, GameInfoGZB, GameInfoTHCOTW, GameInfoJC3, GameInfoJC4
from deca.ff_types import *
import deca.ff_rtpc
from deca.ff_adf import AdfDatabase
from deca.util import Logger, make_dir_for_file
from deca.hashes import hash32_func
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

        self.process_remove_temporary_nodes()

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
        q = "SELECT DISTINCT hash32, COUNT(*) c FROM core_hash_strings GROUP BY hash32 HAVING c > 1;"
        dup_hash4 = self.db_query_all(q)
        for vhash, c in dup_hash4:
            q = "SELECT DISTINCT hash32, string FROM core_hash_strings WHERE hash32 = (?)"
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
            vhash = deca.hashes.hash32_func(vpath)
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

        phase_id = 0
        processed_nodes = set()
        while True:
            phase_id = phase_id + 1
            new_nodes = set(self.nodes_where_processed_select_uid(0))
            new_nodes = new_nodes - processed_nodes

            if len(new_nodes) > 0:
                self.logger.log('Expand Archives Phase {}: Begin'.format(phase_id))
                commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
                commander.do_map('process_archives_initial', list(new_nodes), step_id='Archives')
                processed_nodes = processed_nodes.union(new_nodes)
                self.logger.log('Expand Archives Phase {}: End'.format(phase_id))
            else:
                break

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
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, indexes, step_id=ftype)
        self.logger.log('PROCESS: FTYPE = {}: Total files {}'.format(ftype, len(nodes_done)))

    def process_by_vhash(self, cmd):
        self.logger.log('PROCESS: VHASHes')
        vhashes = self.nodes_select_distinct_vhash()
        if len(vhashes) > 0:
            commander = MultiProcessControl(self.project_file, self.working_dir, self.logger)
            commander.do_map(cmd, vhashes, step_id='vhash')
        self.logger.log('PROCESS: VHASHes: Total VHASHes {}'.format(len(vhashes)))

    def find_vpath_exe(self):
        fn = './resources/{}/all_strings.tsv'.format(self.game_info.game_id)
        if os.path.isfile(fn):
            self.logger.log('STRINGS FROM EXE: look for hashable strings in EXE strings from IDA in ./resources/{}/all_strings.tsv'.format(self.game_info.game_id))
            with open(fn, 'rb') as f:
                exe_strings = f.readlines()
            exe_strings = [line.split(b'\t') for line in exe_strings]
            exe_strings = [line[3].strip() for line in exe_strings if len(line) >= 4]
            exe_strings = list(set(exe_strings))

            with DbWrap(self, logger=self) as db:
                for s in exe_strings:
                    db.propose_string(s, None)

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

    def external_file_add(self, filename):
        if os.path.isfile(filename):
            with open(filename, 'rb') as f:
                ftype, fsize = determine_file_type_and_size(f, os.stat(filename).st_size)

            if ftype is None:
                file, ext = os.path.splitext(filename)
                if ext[0:4] == b'.atx':
                    ftype = FTYPE_ATX
                elif ext == b'.hmddsc':
                    ftype = FTYPE_HMDDSC

            vpath = filename.replace(':', '/')
            vpath = vpath.replace('\\', '/')
            vpath = ('__EXTERNAL_FILES__' + vpath).encode('ascii')
            vhash = deca.hashes.hash32_func(vpath)

            # tag atx file type since they have no header info

            vnode = VfsNode(
                vhash=vhash, vpath=vpath, pvpath=filename, ftype=ftype,
                size_u=fsize, size_c=fsize, offset=0, is_temporary_file=True)
            self.node_add_one(vnode)

            self.logger.log('ADDED {} TO EXTERNAL FILES'.format(filename))
        else:
            self.logger.log('FAILED TO OPEN:  {}'.format(filename))
