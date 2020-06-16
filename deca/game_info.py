from deca.ff_types import *
import os
import json


def determine_game(game_dir, exe_name):
    game_info = None
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
    elif exe_name.find('RAGE2') >= 0:
        game_info = GameInfoRage2(game_dir, exe_name)
    else:
        pass

    return game_info


def game_info_load(project_file):
    with open(project_file) as f:
        settings = json.load(f)
    game_dir = settings['game_dir']
    exe_name = settings['exe_name']
    game_id = settings['game_id']

    if game_id == 'gz':
        return GameInfoGZ(game_dir, exe_name)
    elif game_id == 'hp':
        return GameInfoTHCOTW(game_dir, exe_name)
    elif game_id == 'jc3':
        return GameInfoJC3(game_dir, exe_name)
    elif game_id == 'jc4':
        return GameInfoJC4(game_dir, exe_name)
    elif game_id == 'gzb':
        return GameInfoGZB(game_dir, exe_name)
    elif game_id == 'rg2':
        return GameInfoRage2(game_dir, exe_name)
    else:
        raise NotImplementedError()


class GameInfo:
    def __init__(self, game_dir, exe_name, game_id):
        self.game_dir = game_dir
        self.exe_name = exe_name
        self.game_id = game_id
        self.archive_version = 3
        self.file_hash_size = 4
        self.oo_decompress_dll = None
        self.area_prefixs = ['']

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
            'archive_paths': self.archive_path(),
        }

        with open(filename, 'w') as f:
            json.dump(settings, f, indent=2)

    def unarchived_files(self):
        return []

    def archive_path(self):
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

    def archive_path(self):
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
            'hp_trophyworld_'
            'hp_yukon_',
            'hp_trophyworld_2_'
            
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

    def archive_path(self):
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

    def archive_path(self):
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

    def archive_path(self):
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

    def archive_path(self):
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
