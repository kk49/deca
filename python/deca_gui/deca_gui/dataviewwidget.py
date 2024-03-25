from typing import Optional, List
from deca.db_processor import VfsNode
from deca.db_view import VfsView
from deca.db_processor import VfsNode, VfsProcessor
from deca.ff_types import *
from .viewer_adf import DataViewerAdf
from .viewer_rtpc import DataViewerRtpc
from .viewer_image import DataViewerImage
from .viewer_raw import DataViewerRaw
from .viewer_info import DataViewerInfo
from .viewer_text import DataViewerText
from .viewer_sarc import DataViewerSarc
from .viewer_obc import DataViewerObc
from .deca_interfaces import IVfsViewSrc
from PySide2.QtCore import Signal
from PySide2.QtWidgets import QSizePolicy, QWidget, QVBoxLayout, QTabWidget


class DataViewWidget(QWidget):

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)

        self.data_source: Optional[IVfsViewSrc] = None

        self.tab_info = DataViewerInfo()
        self.tab_raw = DataViewerRaw()
        self.tab_text = DataViewerText()
        self.tab_sarc = DataViewerSarc()
        self.tab_image = DataViewerImage()
        self.tab_adf = DataViewerAdf()
        self.tab_adf_gdc = DataViewerAdf()
        self.tab_rtpc = DataViewerRtpc()
        self.tab_obc = DataViewerObc()

        self.tab_widget = QTabWidget()
        self.tab_info_index = self.tab_widget.addTab(self.tab_info, 'Info')
        self.tab_raw_index = self.tab_widget.addTab(self.tab_raw, 'Raw/Hex')
        self.tab_text_index = self.tab_widget.addTab(self.tab_text, 'Text')
        self.tab_sarc_index = self.tab_widget.addTab(self.tab_sarc, 'SARC')
        self.tab_image_index = self.tab_widget.addTab(self.tab_image, 'Image')
        self.tab_adf_index = self.tab_widget.addTab(self.tab_adf, 'ADF')
        self.tab_adf_gdc_index = self.tab_widget.addTab(self.tab_adf_gdc, 'ADF/GDC')
        self.tab_rtpc_index = self.tab_widget.addTab(self.tab_rtpc, 'RTPC')
        self.tab_obc_index = self.tab_widget.addTab(self.tab_obc, 'OBC')

        self.tab_widget.setEnabled(False)
        self.tab_widget.setTabEnabled(self.tab_info_index, True)
        self.tab_widget.setTabEnabled(self.tab_raw_index, False)
        self.tab_widget.setTabEnabled(self.tab_text_index, False)
        self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
        self.tab_widget.setTabEnabled(self.tab_image_index, False)
        self.tab_widget.setTabEnabled(self.tab_adf_index, False)
        self.tab_widget.setTabEnabled(self.tab_adf_gdc_index, False)
        self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
        self.tab_widget.setTabEnabled(self.tab_obc_index, False)

        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size.setVerticalStretch(1)
        self.tab_widget.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tab_widget)
        self.setLayout(self.main_layout)

    def data_source_set(self, data_source: IVfsViewSrc):
        self.data_source = data_source
        self.data_source.signal_selection_changed.connect(self.vnode_selection_changed)
        self.tab_sarc.signal_archive_open.connect(self.data_source.archive_open)

    def vnode_selection_changed(self):
        print('DataViewWidget:vnode_selection_changed')

    def vnode_2click_selected(self, uids: List[int]):
        vfs: VfsProcessor = self.data_source.vfs_get()
        vnodes = [vfs.node_where_uid(uid) for uid in uids]

        for uid, vnode in zip(uids, vnodes):
            print(f'DataViewWidget:vnode_2click_selected: {uid}: {vnode}')

        vnode = vnodes[0]

        self.tab_widget.setEnabled(True)
        
        self.tab_widget.setTabEnabled(self.tab_info_index, True)
        self.tab_info.vnode_process(vfs, vnode)

        self.tab_widget.setTabEnabled(self.tab_raw_index, True)
        self.tab_raw.vnode_process(vfs, vnode)

        self.tab_widget.setTabEnabled(self.tab_text_index, False)
        self.tab_widget.setTabEnabled(self.tab_sarc_index, False)
        self.tab_widget.setTabEnabled(self.tab_image_index, False)
        self.tab_widget.setTabEnabled(self.tab_adf_index, False)
        self.tab_widget.setTabEnabled(self.tab_adf_gdc_index, False)
        self.tab_widget.setTabEnabled(self.tab_rtpc_index, False)
        self.tab_widget.setTabEnabled(self.tab_obc_index, False)

        if vnode.file_type in {FTYPE_TXT}:
            self.tab_widget.setTabEnabled(self.tab_text_index, True)
            self.tab_text.vnode_process(vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_text_index)
        elif vnode.file_type in {FTYPE_SARC}:
            self.tab_widget.setTabEnabled(self.tab_sarc_index, True)
            self.tab_sarc.vnode_process(vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_sarc_index)
        elif vnode.file_type in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC, FTYPE_DDS, FTYPE_BMP}:
            self.tab_widget.setTabEnabled(self.tab_image_index, True)
            self.tab_image.vnode_process(vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_image_index)
        elif vnode.file_type in ftype_adf_family:
            # handle the case for GenZero where ADF files can be in the
            vnodes_adf = []
            vnodes_adfb = []

            for vnode in vnodes:
                if vnode.file_type == FTYPE_ADF_BARE:
                    vnodes_adfb.append(vnode)
                else:
                    vnodes_adf.append(vnode)

            if len(vnodes_adf) > 0:
                self.tab_widget.setTabEnabled(self.tab_adf_index, True)
                self.tab_adf.vnode_process(vfs, vnodes_adf[0])
                self.tab_widget.setCurrentIndex(self.tab_adf_index)
            if len(vnodes_adfb) > 0:
                self.tab_widget.setTabEnabled(self.tab_adf_gdc_index, True)
                self.tab_adf_gdc.vnode_process(vfs, vnodes_adfb[0])
                self.tab_widget.setCurrentIndex(self.tab_adf_index)

        elif vnode.file_type in {FTYPE_RTPC}:
            self.tab_widget.setTabEnabled(self.tab_rtpc_index, True)
            self.tab_rtpc.vnode_process(vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_rtpc_index)
        elif vnode.file_type in {FTYPE_OBC}:
            self.tab_widget.setTabEnabled(self.tab_obc_index, True)
            self.tab_obc.vnode_process(vfs, vnode)
            self.tab_widget.setCurrentIndex(self.tab_obc_index)
        else:
            self.tab_widget.setCurrentIndex(self.tab_raw_index)
