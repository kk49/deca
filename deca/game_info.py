from deca.ff_types import *
import os
import json


class GameInfo:
    def __init__(self, game_dir, exe_name, game_id):
        self.game_dir = game_dir
        self.exe_name = exe_name
        self.game_id = game_id

    def save(self, filename):
        settings = {
            'game_dir': self.game_dir,
            'exe_name': self.exe_name,
            'game_id': self.game_id,
            'archive_paths': self.archive_path(),
        }

        with open(filename, 'w') as f:
            json.dump(settings, f, indent=2)

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
                '.ee': FTYPE_SARC,
                '.epe': FTYPE_RTPC,
            },
            {
                '.bl': FTYPE_SARC,
                '.nl': FTYPE_SARC,
                '.fl': FTYPE_SARC,
                '.blo': FTYPE_RTPC,
                '.nl.mdic': self.mdic_ftype(),
                '.fl.mdic': self.mdic_ftype(),
                '.pfs': self.pfs_ftype(),
                '.obc': FTYPE_OBC,
            },
            {
                '.meshc': FTYPE_ADF,
                '.hrmeshc': FTYPE_ADF,
                '.modelc': FTYPE_ADF,
                '.model_deps': FTYPE_TXT,
                '.pfxc': self.pfs_ftype(),
            },
            {
                '.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                '.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
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
                '.ee': FTYPE_SARC,
                '.epe': FTYPE_RTPC,
            },
            {
                '.bl': FTYPE_SARC,
                '.nl': FTYPE_SARC,
                '.fl': FTYPE_SARC,
                '.blo': FTYPE_RTPC,
                '.nl.mdic': self.mdic_ftype(),
                '.fl.mdic': self.mdic_ftype(),
                '.pfs': self.pfs_ftype(),
                '.obc': FTYPE_OBC,
            },
            {
                '.meshc': FTYPE_ADF,
                '.hrmeshc': FTYPE_ADF,
                '.modelc': FTYPE_ADF,
                '.model_deps': FTYPE_TXT,
                '.pfxc': self.pfs_ftype(),
            },
            {
                '.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                '.atx0': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx1': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx2': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx3': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx4': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx5': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx6': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx7': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx8': [FTYPE_ATX, FTYPE_NO_TYPE],
                '.atx9': [FTYPE_ATX, FTYPE_NO_TYPE],
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
                '.ee': FTYPE_SARC,
                '.epe': FTYPE_RTPC,
            },
            {
                '.bl': FTYPE_SARC,
                '.nl': FTYPE_SARC,
                '.fl': FTYPE_SARC,
                '.blo': FTYPE_RTPC,
                '.nl.mdic': self.mdic_ftype(),
                '.fl.mdic': self.mdic_ftype(),
                '.pfs': self.pfs_ftype(),
                '.obc': FTYPE_OBC,
            },
            {
                '.meshc': FTYPE_ADF,
                '.hrmeshc': FTYPE_ADF,
                '.modelc': FTYPE_ADF,
                '.model_deps': FTYPE_TXT,
                '.pfxc': self.pfs_ftype()
            },
            {
                '.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                '.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
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
                '.ee': FTYPE_SARC,
                '.epe': FTYPE_RTPC,
            },
            {
                '.bl': FTYPE_SARC,
                '.nl': FTYPE_SARC,
                '.fl': FTYPE_SARC,
                '.blo': FTYPE_RTPC,
                '.nl.mdic': self.mdic_ftype(),
                '.fl.mdic': self.mdic_ftype(),
                '.pfs': self.pfs_ftype(),
                '.obc': FTYPE_OBC,
            },
            {
                '.meshc': FTYPE_ADF,
                '.hrmeshc': FTYPE_ADF,
                '.modelc': FTYPE_ADF,
                '.model_deps': FTYPE_TXT,
                '.pfxc': self.pfs_ftype(),
            },
            {
                '.ddsc': [FTYPE_AVTX, FTYPE_DDS],
                '.hmddsc': [FTYPE_ATX, FTYPE_NO_TYPE],
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
    elif game_id == 'gzb':
        return GameInfoGZB(game_dir, exe_name)
    else:
        raise NotImplementedError()
