from deca.db_processor import vfs_structure_new, vfs_structure_open, VfsNode
from deca.ff_types import *
from deca.ff_adf import AdfDatabase
from deca.gui.viewer_adf import DataViewerAdf
from deca.gui.viewer_rtpc import DataViewerRtpc
from deca.gui.viewer_image import DataViewerImage
from deca.gui.viewer_raw import DataViewerRaw
from deca.gui.viewer_info import DataViewerInfo
from deca.gui.viewer_text import DataViewerText
from deca.gui.viewer_sarc import DataViewerSarc
from deca.gui.viewer_obc import DataViewerObc
from PySide2.QtWidgets import QSizePolicy, QWidget, QVBoxLayout, QTabWidget


class DataViewWidget(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.vfs = None
        self.adf_db = None

        self.tab_info = DataViewerInfo()
        self.tab_raw = DataViewerRaw()
        self.tab_text = DataViewerText()
        self.tab_sarc = DataViewerSarc()
        self.tab_image = DataViewerImage()
        self.tab_adf = DataViewerAdf()
        self.tab_rtpc = DataViewerRtpc()
        self.tab_obc = DataViewerObc()

        self.tab_widget = QTabWidget()
        self.tab_info_index = self.tab_widget.addTab(self.tab_info, 'Info')
        self.tab_raw_index = self.tab_widget.addTab(self.tab_raw, 'Raw/Hex')
        self.tab_text_index = self.tab_widget.addTab(self.tab_text, 'Text')
        self.tab_sarc_index = self.tab_widget.addTab(self.tab_sarc, 'SARC')
        self.tab_image_index = self.tab_widget.addTab(self.tab_image, 'Image')
        self.tab_adf_index = self.tab_widget.addTab(self.tab_adf, 'ADF')
        self.tab_rtpc_index = self.tab_widget.addTab(self.tab_rtpc, 'RTPC')
        self.tab_obc_index = self.tab_widget.addTab(self.tab_obc, 'OBC')

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setVerticalStretch(1)
        self.tab_widget.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def vfs_set(self, vfs):
        self.vfs = vfs
        self.adf_db = AdfDatabase()
        self.adf_db.load_from_database(self.vfs)

    def vnode_selection_changed(self, vpaths):
        print('DataViewWidget:vnode_selection_changed: {}'.format(vpaths))

    def vnode_2click_selected(self, vnode: VfsNode):
        print('DataViewWidget:vnode_2click_selected: {}'.format(vnode))

        self.tab_widget.setTabEnabled(self.tab_info_index, True)
        self.tab_info.vnode_process(self.vfs, vnode)

        self.tab_widget.setTabEnabled(self.tab_raw_index, True)
        self.tab_raw.vnode_process(self.vfs, vnode)

        self.tab_widget.setTabEnabled(self.tab_text_index, False)
        self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
        self.tab_widget.setTabEnabled(self.tab_image_index, False)
        self.tab_widget.setTabEnabled(self.tab_adf_index, False)
        self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
        self.tab_widget.setTabEnabled(self.tab_obc_index, False)

        if vnode.file_type in {FTYPE_TXT}:
            self.tab_widget.setTabEnabled(self.tab_text_index, True)
            self.tab_text.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_text_index)
        elif vnode.file_type in {FTYPE_SARC}:
            self.tab_widget.setTabEnabled(self.tab_sarc_index, True)
            self.tab_sarc.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_sarc_index)
        elif vnode.file_type in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC, FTYPE_DDS, FTYPE_BMP}:
            self.tab_widget.setTabEnabled(self.tab_image_index, True)
            self.tab_image.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_image_index)
        elif vnode.file_type in {FTYPE_ADF, FTYPE_ADF_BARE, FTYPE_ADF0}:
            self.tab_widget.setTabEnabled(self.tab_adf_index, True)
            self.tab_adf.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_adf_index)
        elif vnode.file_type in {FTYPE_RTPC}:
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, True)
            self.tab_rtpc.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_rtpc_index)
        elif vnode.file_type in {FTYPE_OBC}:
            self.tab_widget.setTabEnabled(self.tab_obc_index, True)
            self.tab_obc.vnode_process(self.vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_obc_index)
        else:
            self.tab_widget.setCurrentIndex(self.tab_raw_index)
