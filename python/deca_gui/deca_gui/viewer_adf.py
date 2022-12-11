from .viewer import *
from .viewer_text import DataViewerText
from deca.ff_adf import EDecaMissingAdfType, AdfDatabase


class DataViewerAdf(DataViewerText):
    def __init__(self):
        super().__init__()

    def vnode_process(self, vfs: VfsProcessor, vnode: VfsNode):
        adf_db = AdfDatabase(vfs)

        try:
            obj = adf_db.read_node(vfs, vnode)
            sbuf = obj.dump_to_string(vfs)
        except EDecaMissingAdfType as e:
            sbuf = 'Missing ADF_TYPE {:08x} in parsing of type {:08x}'.format(e.type_id, vnode.file_sub_type)

        self.content_set(sbuf)


