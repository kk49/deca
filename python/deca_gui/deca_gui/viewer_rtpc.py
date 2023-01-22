from .viewer import *
from .viewer_text import DataViewerText
from deca.ff_rtpc import RtpcVisitorDumpToString


class DataViewerRtpc(DataViewerText):
    def __init__(self):
        super().__init__()

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        with vfs.file_obj_from(vnode) as f:
            buffer = f.read(vnode.size_u)

        dump = RtpcVisitorDumpToString(vfs)
        dump.visit(buffer)
        sbuf = dump.result()

        self.content_set(sbuf)
