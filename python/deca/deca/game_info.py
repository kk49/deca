import deca
from deca.ff_types import *
from deca.util import deca_root
from typing import List
import os
import json
import re


game_info_prefixes = [
    '../work/gameinfo',
    'resources/deca/gameinfo',
]


class GameInfo:
    def __init__(self, game_dir, exe_name, game_id):
        self.game_dir = game_dir
        self.exe_name = exe_name
        self.game_id = game_id
        self.archive_version = 3
        self.file_hash_size = 4
        self.oo_decompress_dll = None
        self.area_prefixes = ['']

        self.world_patches = [
            'terrain/hp/patches/',
            'terrain/jc3/patches/'
        ]

        self.world_occluders = [
            'terrain/hp/occluder/',
            'terrain/jc3/occluder/'
        ]

        self.world_navheightfields = [
            'terrain/hp/navheightfield/globalhires/',
            'terrain/jc3/navheightfield/globalhires/'
        ]

        self.world_hm = [
            'terrain/hp/horizonmap/horizon_'            
            'terrain/jc3/horizonmap/horizon_'
        ]

        self.world_ai = [
            'ai/tiles/'
        ]

        self.map_zooms = [0, 1, 2, 3]
        self.map_max_count = 500
        self.map_prefixes = [
            'textures/ui/',
        ]

    def save(self, filename):
        settings = {
            'game_dir': self.game_dir,
            'exe_name': self.exe_name,
            'game_id': self.game_id,
            'archive_paths': self.archive_paths(),
        }

        with open(filename, 'w') as f:
            json.dump(settings, f, indent=2)

    def unarchived_files(self):
        return []

    def archive_paths(self):
        raise NotImplementedError()

    def mdic_ftype(self):
        raise NotImplementedError()

    def navmesh_ftype(self):
        raise NotImplementedError()

    def obc_ftype(self):
        raise NotImplementedError()

    def pfs_ftype(self):
        raise NotImplementedError()

    def file_assoc(self):
        raise NotImplementedError()

    def has_garcs(self):
        return False


def expand_list(data0, envs):
    data_out = data0
    for env in envs:
        data_in = data_out

        if env[1]:
            data_out = []

            for value in env[1]:
                for din in data_in:
                    data_out.append(din.replace(env[0], value))

    data_in = data_out
    data_out = []
    seen = set()
    for value in data_in:
        if value not in seen:
            seen.add(value)
            data_out.append(value)

    return data_out


class GameInfoJson(GameInfo):
    def __init__(self, game_dir, exe_name, jdata):
        GameInfo.__init__(self, game_dir, exe_name, jdata['game_id'])
        self.archive_version = jdata['archive_version']
        self.file_hash_size = jdata['file_hash_size']

        self.oo_decompress_dll = jdata.get('oo_decompress_dll', None)
        if not self.oo_decompress_dll:
            self.oo_decompress_dll = None

        self.map_zooms = jdata['map_zooms']
        self.map_max_count = jdata['map_max_count']
        self.world_indexes = ['{}'.format(v) for v in jdata.get('world_indexes', [])]

        self.area_prefixes = jdata.get('area_prefixes', [])
        self.world_patches = jdata.get('world_patches', [])
        self.world_occluders = jdata.get('world_occluders', [])
        self.world_navheightfields = jdata.get('world_navheightfields', [])
        self.world_hm = jdata.get('world_hm', [])
        self.world_ai = jdata.get('world_ai', [])
        self.map_prefixes = jdata.get('map_prefixes', [])
        self._unarchived_files = jdata.get('unarchived_files', [])
        self._archive_path = jdata.get('archive_paths', [])
        self._mdic_ftype = jdata.get('mdic_ftype', '').split(',')
        self._navmesh_ftype = jdata.get('navmesh_ftype', '').split(',')
        self._obc_ftype = jdata.get('obc_ftype', '').split(',')
        self._pfs_ftype = jdata.get('pfs_ftype', '').split(',')
        self._file_assoc = jdata.get('file_assoc', [])
        self._has_garcs = jdata.get('has_garcs', False)

        if self.game_dir.endswith('/') or self.game_dir.endswith('\\'):
            gd = self.game_dir[:-1]
        else:
            gd = self.game_dir

        envs = [
            ('${DECA_DIR}', ['.']),
            ('${GAME_DIR}', [gd]),
            ('${AREA_PREFIX}', self.area_prefixes),
            ('${WORLD_INDEX}', self.world_indexes),
        ]

        if self.oo_decompress_dll is not None:
            self.oo_decompress_dll = expand_list([self.oo_decompress_dll], envs)[0]
        self.world_patches = expand_list(self.world_patches, envs)
        self.world_occluders = expand_list(self.world_occluders, envs)
        self.world_navheightfields = expand_list(self.world_navheightfields, envs)
        self.world_hm = expand_list(self.world_hm, envs)
        self.world_ai = expand_list(self.world_ai, envs)
        self.map_prefixes = expand_list(self.map_prefixes, envs)
        self._unarchived_files = expand_list(self._unarchived_files, envs)
        self._archive_paths = expand_list(self._archive_path, envs)

        old_fa = self._file_assoc
        self._file_assoc = []
        for fa in old_fa:
            nfa = {}
            for k, v in fa.items():
                nfa[k.encode('ascii')] = v.split(',')
            self._file_assoc.append(nfa)

    def unarchived_files(self):
        return self._unarchived_files

    def archive_paths(self):
        return self._archive_paths

    def mdic_ftype(self):
        return self._mdic_ftype

    def navmesh_ftype(self):
        return self._navmesh_ftype

    def obc_ftype(self):
        return self._obc_ftype

    def pfs_ftype(self):
        return self._pfs_ftype

    def file_assoc(self):
        return self._file_assoc

    def has_garcs(self):
        return self._has_garcs


class GameInfoGZ(GameInfo):
    def __init__(self, game_dir, exe_name, game_id='gz'):
        GameInfo.__init__(self, game_dir, exe_name, game_id)
        self.map_prefixes += [
            'textures/ui/map_reserve_0/',
            'textures/ui/map_reserve_1/',
            'textures/ui/warboard_map/',
        ]

    def unarchived_files(self):
        files = [os.path.join(self.game_dir, 'Shaders_F.shader_bundle')]
        return files

    def archive_paths(self):
        archive_paths = []
        for cat in ['initial', 'supplemental', 'optional']:
            archive_paths.append(os.path.join(self.game_dir, 'archives_win64', cat))
        return archive_paths

    def mdic_ftype(self):
        return [FTYPE_ADF, FTYPE_ADF_BARE]

    def navmesh_ftype(self):
        return FTYPE_TAG0

    def obc_ftype(self):
        return FTYPE_OBC

    def pfs_ftype(self):
        return FTYPE_TAG0

    def file_assoc(self):
        return [
            {
                b'.ee': FTYPE_SARC,
                b'.epe': FTYPE_RTPC,
            },
            {
                b'.bl': FTYPE_SARC,
                b'.nl': FTYPE_SARC,
                b'.fl': FTYPE_SARC,
                b'.blo': FTYPE_RTPC,
                b'.nl.mdic': self.mdic_ftype(),
                b'.fl.mdic': self.mdic_ftype(),
                b'.pfs': self.pfs_ftype(),
                b'.obc': FTYPE_OBC,
            },
            {
                b'.meshc': FTYPE_ADF,
                b'.hrmeshc': FTYPE_ADF,
                b'.modelc': FTYPE_ADF,
                b'.model_deps': FTYPE_TXT,
                b'.pfxc': self.pfs_ftype(),
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                # b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
            {
                b'.swf': FTYPE_GFX,
                b'.cfx': FTYPE_GFX,
                b'.gfx': FTYPE_GFX,
            },
        ]


class GameInfoGZB(GameInfoGZ):
    def __init__(self, game_dir, exe_name):
        GameInfoGZ.__init__(self, game_dir, exe_name, 'gzb')


class GameInfoTHCOTW(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'hp')
        self.area_prefixs = [
            '',
            'globalhires_',

            'hp_germany_farmland_fall_',
            'hp_pacific_northwest_',
            'hp_siberia_',
            'hp_africa_',

            'hp_patagonia_',
            'hp_trophyworld_',
            'hp_yukon_',
            'hp_trophyworld_2_',
            
            'hp_iberia_',
        ]

        self.world_patches += [
            'worlds/base/terrain/hp/patches/'
        ]

        self.world_occluders += [
            'worlds/base/terrain/hp/occluder/'
        ]

        self.world_navheightfields += [
            'worlds/base/terrain/hp/navheightfield/globalhires/'
        ]

        self.world_ai += [
            'worlds/base/ai/tiles/'
        ]

        for i in range(4):
            self.world_patches.append(f'worlds/world{i}/terrain/world{i}/patches/')
            self.world_occluders.append(f'worlds/world{i}/terrain/world{i}/occluder/')
            self.world_navheightfields.append(f'worlds/world{i}/terrain/world{i}/navheightfield/globalhires/')
            self.world_ai.append(f'worlds/world{i}/ai/tiles/')

            for area in self.area_prefixs:
                self.world_hm.append(f'worlds/base/terrain/hp/horizonmap/horizon_hp_{area}')
                self.world_hm.append(f'worlds/world{i}/terrain/world{i}/horizonmap/horizon_hp_{area}')

    def archive_paths(self):
        archive_paths = []
        archive_paths.append(os.path.join(self.game_dir, 'archives_win64'))
        return archive_paths

    def mdic_ftype(self):
        return FTYPE_MDI

    def navmesh_ftype(self):
        return FTYPE_H2014

    def obc_ftype(self):
        return None

    def pfs_ftype(self):
        return FTYPE_PFX

    def file_assoc(self):
        return [
            {
                b'.ee': FTYPE_SARC,
                b'.epe': FTYPE_RTPC,
            },
            {
                b'.bl': FTYPE_SARC,
                b'.nl': FTYPE_SARC,
                b'.fl': FTYPE_SARC,
                b'.blo': FTYPE_RTPC,
                b'.nl.mdic': self.mdic_ftype(),
                b'.fl.mdic': self.mdic_ftype(),
                b'.pfs': self.pfs_ftype(),
                b'.obc': FTYPE_OBC,
            },
            {
                b'.meshc': FTYPE_ADF,
                b'.hrmeshc': FTYPE_ADF,
                b'.modelc': FTYPE_ADF,
                b'.model_deps': FTYPE_TXT,
                b'.pfxc': self.pfs_ftype()
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                b'.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
            {
                b'.swf': FTYPE_GFX,
                b'.cfx': FTYPE_GFX,
                b'.gfx': FTYPE_GFX,
            },

        ]


class GameInfoJC3(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'jc3')
        self.map_prefixes += [
            'dlc/agency/textures/ui/map0/',
            'dlc/agency/textures/ui/map1/',
            'dlc/agency/textures/ui/map2/',
            'dlc/agency/textures/ui/map3/',
            'dlc/daredevil/textures/ui/',
            'dlc/demonios/textures/ui/',
        ]

    def archive_paths(self):
        archive_paths = []
        archive_paths.append(os.path.join(self.game_dir, 'patch_win64'))
        archive_paths.append(os.path.join(self.game_dir, 'archives_win64'))
        archive_paths.append(os.path.join(self.game_dir, 'dlc_win64'))
        return archive_paths

    def mdic_ftype(self):
        return FTYPE_MDI

    def navmesh_ftype(self):
        return FTYPE_H2014

    def obc_ftype(self):
        return None

    def pfs_ftype(self):
        return FTYPE_PFX

    def file_assoc(self):
        return [
            {
                b'.ee': FTYPE_SARC,
                b'.epe': FTYPE_RTPC,
            },
            {
                b'.bl': FTYPE_SARC,
                b'.nl': FTYPE_SARC,
                b'.fl': FTYPE_SARC,
                b'.blo': FTYPE_RTPC,
                b'.nl.mdic': self.mdic_ftype(),
                b'.fl.mdic': self.mdic_ftype(),
                b'.pfs': self.pfs_ftype(),
                b'.obc': FTYPE_OBC,
            },
            {
                b'.meshc': FTYPE_ADF,
                b'.hrmeshc': FTYPE_ADF,
                b'.modelc': FTYPE_ADF,
                b'.model_deps': FTYPE_TXT,
                b'.pfxc': self.pfs_ftype(),
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                b'.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
            {
                b'.swf': FTYPE_GFX,
                b'.cfx': FTYPE_GFX,
                b'.gfx': FTYPE_GFX,
            },

        ]


class GameInfoJC4(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'jc4')
        self.archive_version = 4
        self.oo_decompress_dll = os.path.join(game_dir, 'oo2core_7_win64.dll')
        self.map_prefixes += [
            'dlc/agency/textures/ui/map0/',
            'dlc/agency/textures/ui/map1/',
            'dlc/agency/textures/ui/map2/',
            'dlc/agency/textures/ui/map3/',
            'dlc/daredevil/textures/ui/',
            'dlc/demonios/textures/ui/',
        ]

    def archive_paths(self):
        archive_paths = []
        archive_paths.append(os.path.join(self.game_dir, 'archives_win64'))
        return archive_paths

    def mdic_ftype(self):
        return FTYPE_ADF

    def navmesh_ftype(self):
        return FTYPE_H2014

    def obc_ftype(self):
        return None

    def pfs_ftype(self):
        return FTYPE_PFX

    def file_assoc(self):
        return [
            {
                b'.ee': FTYPE_SARC,
                b'.epe': FTYPE_RTPC,
            },
            {
                b'.bl': FTYPE_SARC,
                b'.nl': FTYPE_SARC,
                b'.fl': FTYPE_SARC,
                b'.blo': FTYPE_RTPC,
                b'.nl.mdic': self.mdic_ftype(),
                b'.fl.mdic': self.mdic_ftype(),
                b'.pfs': self.pfs_ftype(),
                b'.obc': FTYPE_OBC,
            },
            {
                b'.meshc': FTYPE_ADF,
                b'.hrmeshc': FTYPE_ADF,
                b'.modelc': FTYPE_ADF,
                b'.model_deps': FTYPE_TXT,
                b'.pfxc': self.pfs_ftype(),
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                b'.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
            {
                b'.swf': FTYPE_GFX,
                b'.cfx': FTYPE_GFX,
                b'.gfx': FTYPE_GFX,
            },
        ]


class GameInfoRage2(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'rg2')
        self.archive_version = 5
        self.file_hash_size = 8
        self.oo_decompress_dll = os.path.join(game_dir, 'oo2core_7_win64.dll')
        self.map_prefixes += [
        ]

        self.world_patches = [
            'terrain/heatwave/patches/width_3/',
            'terrain/heatwave/patches/width_4/',
            'terrain/heatwave/patches/width_8/',
        ]

        self.world_occluders = [
            'terrain/heatwave/occluder/',
        ]

        self.world_navheightfields = [
            'terrain/hp/navheightfield/globalhires/',
        ]

        self.world_hm = [
            'terrain/heatwave/horizonmap/horizonmap_tessellation_disabled_',
            'terrain/heatwave/horizonmap/horizonmap_moon_tessellation_disabled_',
        ]

        self.map_zooms = [1, 2, 3, 4, 5]
        self.map_max_count = 1024
        self.map_prefixes = [
            'textures/ui/world_map/worldmap_',
            'textures/ui/world_map/',
        ]

    def archive_paths(self):
        archive_paths = [
            os.path.join(self.game_dir, 'archives_win64'),
        ]
        return archive_paths

    def mdic_ftype(self):
        return FTYPE_ADF

    def navmesh_ftype(self):
        return FTYPE_H2014

    def obc_ftype(self):
        return None

    def pfs_ftype(self):
        return FTYPE_PFX

    def file_assoc(self):
        return [
            {
                b'.ee': FTYPE_ANY_TYPE,
                b'.epe': FTYPE_RTPC,
            },
            {
                b'.bl': FTYPE_ANY_TYPE,
                b'.nl': FTYPE_ANY_TYPE,
                b'.fl': FTYPE_ANY_TYPE,
                b'.blo': FTYPE_RTPC,
                b'.nl.mdic': self.mdic_ftype(),
                b'.fl.mdic': self.mdic_ftype(),
                b'.pfs': self.pfs_ftype(),
                b'.obc': FTYPE_OBC,
            },
            {
                b'.meshc': FTYPE_ADF,
                b'.hrmeshc': FTYPE_ADF,
                b'.modelc': FTYPE_ADF,
                b'.model_deps': FTYPE_TXT,
                b'.pfxc': self.pfs_ftype(),
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                b'.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                # b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
            {
                b'.swf': FTYPE_GFX,
                b'.cfx': FTYPE_GFX,
                b'.gfx': FTYPE_GFX,
            },
        ]

    def has_garcs(self):
        return True


class GameInfoFactory:
    def __init__(self, json_file):
        self.json_file = json_file
        with open(json_file, 'r') as f:
            self.json = json.load(f)

    def create(self, game_dir, exe_name, game_id=None):
        exe_match = self.json.get('exe_match', None)
        exe_not_match = self.json.get('exe_not_match', None)

        full_path = os.path.join(game_dir, exe_name)

        if game_id is not None and game_id != self.json['game_id']:
            return None

        if exe_match is None or not re.match(exe_match, full_path):
            return None

        if exe_not_match is not None and re.match(exe_not_match, full_path):
            return None

        return GameInfoJson(game_dir, exe_name, self.json)


def determine_game_info(game_dir, exe_name, game_id=None):
    json_files = []
    for prefix0 in game_info_prefixes:
        prefix = os.path.abspath(os.path.join(deca_root(), prefix0))
        if os.path.isdir(prefix):
            json_files += [os.path.join(prefix, fn) for fn in os.listdir(prefix) if fn.endswith('json')]

    for fn in json_files:
        factory = GameInfoFactory(fn)
        game_info = factory.create(game_dir, exe_name, game_id)
        if game_info is not None:
            return game_info

    return None


def determine_game(game_dir, exe_name):
    game_info = determine_game_info(game_dir, exe_name)
    if game_info is not None:
        return game_info

    # game_info = None
    # if exe_name.find('GenerationZero') >= 0 and game_dir.find('BETA') >= 0:
    #     game_info = GameInfoGZB(game_dir, exe_name)
    # elif exe_name.find('GenerationZero') >= 0:
    #     game_info = GameInfoGZ(game_dir, exe_name)
    # elif exe_name.find('theHunterCotW') >= 0:
    #     game_info = GameInfoTHCOTW(game_dir, exe_name)
    # elif exe_name.find('JustCause3') >= 0:
    #     game_info = GameInfoJC3(game_dir, exe_name)
    # elif exe_name.find('JustCause4') >= 0:
    #     game_info = GameInfoJC4(game_dir, exe_name)
    # elif exe_name.find('RAGE2') >= 0:
    #     game_info = GameInfoRage2(game_dir, exe_name)
    # else:
    #     pass
    #
    return game_info


def game_info_load(project_file):
    with open(project_file) as f:
        settings = json.load(f)

    game_dir = settings['game_dir']
    exe_name = settings['exe_name']
    game_id = settings['game_id']

    game_info = determine_game_info(game_dir, exe_name, game_id=game_id)
    if game_info is not None:
        return game_info

    raise NotImplementedError()

    # if game_id == 'gz':
    #     return GameInfoGZ(game_dir, exe_name)
    # elif game_id == 'hp':
    #     return GameInfoTHCOTW(game_dir, exe_name)
    # elif game_id == 'jc3':
    #     return GameInfoJC3(game_dir, exe_name)
    # elif game_id == 'jc4':
    #     return GameInfoJC4(game_dir, exe_name)
    # elif game_id == 'gzb':
    #     return GameInfoGZB(game_dir, exe_name)
    # elif game_id == 'rg2':
    #     return GameInfoRage2(game_dir, exe_name)
    # else:
    #     raise NotImplementedError()
