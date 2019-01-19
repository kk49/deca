from deca.ff_vfs import VfsStructure


class Builder:
    def __init__(self):
        pass

    def build_dir(self, vfs: VfsStructure, src_path: str, dst_path: str):
        pass

    def build_src(self, vfs: VfsStructure, src_file: str, dst_path: str):
        # TODO Eventually process a simple script to update files based on relative addressing to handle other mods and
        #  patches
        pass
