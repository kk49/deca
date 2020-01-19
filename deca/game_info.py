from deca.ff_types import *
import os
import json


class GameInfo:
    def __init__(self, game_dir, exe_name, game_id):
        self.game_dir = game_dir
        self.exe_name = exe_name
        self.game_id = game_id
        self.archive_version = 3
        self.worlds = ['', 'worlds/base/']
        for i in range(8):
            self.worlds.append('worlds/world{}/'.format(i))

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


class GameInfoGZ(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'gz')

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
                b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
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


class GameInfoGZB(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'gzb')

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
                b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
            },
            {
                b'.fmod_sbankc': FTYPE_TXT,
                b'.fmod_bankc': FTYPE_RIFF,
            },
        ]


class GameInfoTHCOTW(GameInfo):
    def __init__(self, game_dir, exe_name):
        GameInfo.__init__(self, game_dir, exe_name, 'hp')

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
                b'.pfxc': self.pfs_ftype(),
            },
            {
                b'.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                b'.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                b'.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
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
    else:
        raise NotImplementedError()
