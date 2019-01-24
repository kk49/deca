from deca.ff_types import *


class GameInfo:
    def __init__(self, game_id):
        self.game_id = game_id

    def mdic_ftype(self):
        raise NotImplementedError()

    def navmesh_ftype(self):
        raise NotImplementedError()

    def obc_ftype(self):
        raise NotImplementedError()

    def pfs_ftype(self):
        raise NotImplementedError()


class GameInfoGZB(GameInfo):
    def __init__(self):
        GameInfo.__init__(self, 'gzb')

    def mdic_ftype(self):
        return [FTYPE_ADF, FTYPE_ADF_BARE]

    def navmesh_ftype(self):
        return FTYPE_TAG0

    def obc_ftype(self):
        return FTYPE_OBC


class GameInfoTHCOTW(GameInfo):
    def __init__(self):
        GameInfo.__init__(self, 'hp')

    def mdic_ftype(self):
        return FTYPE_MDI

    def navmesh_ftype(self):
        return FTYPE_H2014

    def obc_ftype(self):
        return None

    def pfs_ftype(self):
        return FTYPE_PFX
