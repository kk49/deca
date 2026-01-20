import re
import sys
import os
from typing import Optional, List
from deca.errors import *
from deca.db_core import VfsNode
from deca.db_processor import VfsProcessor, vfs_structure_new, vfs_structure_open, vfs_structure_empty
from deca.db_view import VfsView
from deca.builder import Builder
from deca.path import UniPath
from deca.util import Logger, to_unicode, deca_root
from deca.cmds.tool_make_web_map import ToolMakeWebMap
from deca.export_import import \
    nodes_export_raw, nodes_export_contents, nodes_export_processed, nodes_export_gltf, nodes_export_map
from .main_window import Ui_MainWindow
from .deca_interfaces import IVfsViewSrc
from .vfsdirwidget import VfsDirWidget
from .vfsnodetablewidget import VfsNodeTableWidget
from PySide6.QtCore import Slot, QUrl, Signal, QEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QTabBar, QMessageBox, QFileDialog, QStyle
from PySide6.QtGui import QDesktopServices, QKeyEvent

window_title = 'decaGUI: v0.2.19rc'


class MainWindowDataSource(IVfsViewSrc):
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window: MainWindow = main_window

    def vfs_get(self) -> Optional[VfsProcessor]:
        return self.main_window.vfs_view_current().vfs()

    def vfs_view_get(self) -> Optional[VfsView]:
        return self.main_window.vfs_view_current()

    def archive_open(self, selection):
        return self.main_window.slot_archive_open(selection)


class MainWindow(QMainWindow):
    signal_visible_changed = Signal(VfsView)
    signal_selection_changed = Signal(VfsView)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.data_source = MainWindowDataSource(self)

        self.vfs: Optional[VfsProcessor] = None
        self.logger = Logger('./')

        self.builder = Builder()
        self.current_uids = None
        self.vfs_view_root: Optional[VfsView] = None

        self.tab_nodes_deletable = set()

        self.signal_visible_changed.connect(self.slot_visible_changed)
        self.signal_selection_changed.connect(self.slot_selection_changed)

        # Configure Actions
        self.ui.action_project_new.triggered.connect(self.project_new)
        self.ui.action_project_open.triggered.connect(self.project_open)
        self.ui.action_file_gz_open.triggered.connect(self.file_gz_open)
        self.ui.action_external_add.triggered.connect(self.external_add)
        self.ui.action_external_add.setEnabled(False)

        # self.ui.action_external_manage.triggered.connect(self.external_manage)
        self.ui.action_exit.triggered.connect(self.exit_app)
        self.ui.action_make_web_map.triggered.connect(self.tool_make_web_map)
        self.ui.action_make_web_map.setEnabled(False)

        # filter
        self.ui.filter_edit.textChanged.connect(self.filter_text_changed)
        self.ui.filter_edit.installEventFilter(self)
        self.ui.filter_set_bt.clicked.connect(self.filter_text_accepted)
        self.ui.filter_clear_bt.clicked.connect(self.filter_text_cleared)

        self.ui.vhash_to_vpath_in_edit.textChanged.connect(self.vhash_to_vpath_text_changed)

        self.ui.chkbx_export_raw_extract.setChecked(True)
        self.ui.chkbx_export_contents_extract.setChecked(False)
        self.ui.chkbx_export_text_extract.setChecked(False)
        self.ui.chkbx_export_processed_extract.setChecked(False)

        self.ui.chkbx_export_raw_mods.setChecked(True)
        self.ui.chkbx_export_contents_mods.setChecked(False)
        self.ui.chkbx_export_processed_mods.setChecked(False)

        self.ui.chkbx_mod_build_subset.setChecked(False)
        self.ui.chkbx_mod_build_subset.clicked.connect(self.slot_mod_build_subset_clicked)

        self.ui.chkbx_export_save_to_one_dir.setChecked(False)

        self.ui.bt_extract.setEnabled(False)
        self.ui.bt_extract.clicked.connect(self.slot_extract_clicked)

        self.ui.bt_extract_folder_show.setEnabled(False)
        self.ui.bt_extract_folder_show.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.ui.bt_extract_folder_show.clicked.connect(self.slot_folder_show_clicked)

        self.ui.bt_extract_gltf_3d.setEnabled(False)
        self.ui.bt_extract_gltf_3d.clicked.connect(self.slot_extract_gltf_clicked)

        self.ui.bt_extract_gltf_3d_folder_show.setEnabled(False)
        self.ui.bt_extract_gltf_3d_folder_show.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.ui.bt_extract_gltf_3d_folder_show.clicked.connect(self.slot_folder_show_clicked)

        self.ui.bt_mod_prep.setEnabled(False)
        self.ui.bt_mod_prep.clicked.connect(self.slot_mod_prep_clicked)

        self.ui.bt_mod_folder_show.setEnabled(False)
        self.ui.bt_mod_folder_show.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.ui.bt_mod_folder_show.clicked.connect(self.slot_folder_show_clicked)

        self.ui.bt_mod_build_folder_show.setEnabled(False)
        self.ui.bt_mod_build_folder_show.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.ui.bt_mod_build_folder_show.clicked.connect(self.slot_folder_show_clicked)

        self.ui.bt_mod_build.setEnabled(False)
        self.ui.bt_mod_build.clicked.connect(self.slot_mod_build_clicked)

        self.ui.tabs_nodes.tabCloseRequested.connect(self.slot_nodes_tab_close)
        self.ui.tabs_nodes.currentChanged.connect(self.slot_nodes_tab_current_changed)

        self.ui.data_view.data_source_set(self.data_source)

        self.update_ui_state()

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyRelease and source is self.ui.filter_edit:
            self.filter_text_key_release(source, event)

        return super().eventFilter(source, event)

    def error_dialog(self, s):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setWindowTitle("DECA: ERROR")
        msg.setText(s)
        # msg.setInformativeText("This is additional information")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()

    def dialog_good(self, s):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)

        msg.setWindowTitle("DECA")
        msg.setText(s)
        # msg.setInformativeText("This is additional information")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()

    def vfs_view_create(self, *args, **kwargs):
        vfs_view = VfsView(*args, **kwargs)
        vfs_view.signal_visible_changed.connect(
            self, lambda x: x.signal_visible_changed.emit(vfs_view))
        vfs_view.signal_selection_changed.connect(
            self, lambda x: x.signal_selection_changed.emit(vfs_view))

        return vfs_view

    def vfs_set(self, vfs):
        self.vfs = vfs
        self.vfs_view_root = self.vfs_view_create(vfs, None, b'^.*$')

        # Configure VFS dir table
        widget = self.tab_nodes_add(VfsDirWidget, self.vfs_view_root, 'Directory')

        # Configure VFS Node table (non-mapped nodes)
        widget = self.tab_nodes_add(VfsNodeTableWidget, self.vfs_view_root, 'Non-Mapped List')
        widget.show_all_set(False)

        # Configure VFS Node table (all nodes)
        widget = self.tab_nodes_add(VfsNodeTableWidget, self.vfs_view_root, 'Raw List')
        widget.show_all_set(True)

        self.update_ui_state()

        self.ui.statusbar.showMessage("LOAD COMPLETE")

    def vfs_view_current(self) -> Optional[VfsView]:
        widget = self.ui.tabs_nodes.currentWidget()
        if widget is None:
            return None
        return widget.vfs_view_get()

    def tab_nodes_add(self, widget_class, vfs_view, name, deletable=False):
        # self.tab_extract = QtWidgets.QWidget()
        # self.tab_extract.setObjectName("tab_extract")
        # self.gridLayout = QtWidgets.QGridLayout(self.tab_extract)
        # self.gridLayout.setObjectName("gridLayout")
        widget = widget_class(vfs_view, self.ui.tabs_nodes)
        tabIndex = self.ui.tabs_nodes.addTab(widget, name)
        widget.vnode_2click_selected = self.vnode_2click_selected

        if deletable:
            self.tab_nodes_deletable.add(widget)
        else:
            self.ui.tabs_nodes.tabBar().setTabButton(tabIndex, QTabBar.RightSide, None)

        return widget

    def slot_archive_open(self, vnode: VfsNode):
        if vnode is not None:
            vfs_view = self.vfs_view_create(self.vfs_view_current(), parent_id=vnode.uid)
            self.tab_nodes_add(VfsDirWidget, vfs_view, to_unicode(vnode.v_path), True)

    def slot_nodes_tab_close(self, index):
        widget = self.ui.tabs_nodes.widget(index)
        if widget in self.tab_nodes_deletable:
            self.tab_nodes_deletable.remove(widget)
            if widget is not None:
                widget.deleteLater()
            self.ui.tabs_nodes.removeTab(index)

    def slot_nodes_tab_current_changed(self, index):
        widget = self.ui.tabs_nodes.widget(index)
        self.setWindowTitle("{}: Archive: {}".format(window_title, self.vfs_view_current().vfs().game_info.game_dir))
        self.update_select_state(self.vfs_view_current())

    def slot_visible_changed(self, vfs_view: VfsView):
        self.update_select_state(vfs_view)

    def slot_selection_changed(self, vfs_view: VfsView):
        self.update_select_state(vfs_view)

    def update_ui_state(self):
        if self.vfs_view_current() is None:
            self.ui.bt_mod_build_folder_show.setEnabled(False)
            self.ui.bt_mod_build.setEnabled(False)
            self.ui.action_external_add.setEnabled(False)
            self.ui.action_make_web_map.setEnabled(False)
            self.ui.tab_extract.setEnabled(False)
            self.ui.tab_modding.setEnabled(False)
            self.ui.tab_3d_gltf2.setEnabled(False)
            self.ui.tab_utils.setEnabled(False)
        else:
            self.ui.bt_mod_build_folder_show.setEnabled(True)
            self.ui.bt_mod_build.setEnabled(True)
            self.ui.action_external_add.setEnabled(True)
            self.ui.action_make_web_map.setEnabled(True)
            self.ui.tab_extract.setEnabled(True)
            self.ui.tab_modding.setEnabled(True)
            self.ui.tab_3d_gltf2.setEnabled(True)
            self.ui.tab_utils.setEnabled(True)
        self.filter_text_changed()

    def update_select_state(self, vfs_view):
        if vfs_view == self.vfs_view_current():
            any_selected = vfs_view.capture_count() > 0

            if not self.ui.filter_edit.hasFocus():
                self.ui.filter_edit.setText(to_unicode(vfs_view.mask))

            self.ui.bt_extract.setEnabled(any_selected)
            self.ui.bt_extract_gltf_3d.setEnabled(any_selected)
            self.ui.bt_mod_prep.setEnabled(any_selected)
            self.ui.bt_extract_folder_show.setEnabled(any_selected)
            self.ui.bt_extract_gltf_3d_folder_show.setEnabled(any_selected)
            self.ui.bt_mod_folder_show.setEnabled(any_selected)

            str_vpaths = self.vfs_view_current().capture_path_summary_str()
            self.ui.bt_extract.setText('EXTRACT: {}'.format(str_vpaths))
            self.ui.bt_extract_gltf_3d.setText('EXTRACT 3D/GLTF2: {}'.format(str_vpaths))
            self.ui.bt_mod_prep.setText('PREP MOD: {}'.format(str_vpaths))

            if self.ui.chkbx_mod_build_subset.isChecked():
                self.ui.bt_mod_build.setText('BUILD MOD SUBSET: {}'.format(str_vpaths))
                self.ui.bt_mod_build.setEnabled(any_selected)
            else:
                self.ui.bt_mod_build.setText('BUILD MOD ALL')

    def vnode_2click_selected(self, uids: List[int]):
        self.current_uids = uids
        self.ui.data_view.vnode_2click_selected(uids)

    def extract(
            self, eid, extract_dir, export_raw, export_contents, save_to_processed, save_to_text,
            export_map_full, export_map_tiles):
        if self.vfs_view_current() and self.vfs_view_current().node_selected_count() > 0:
            try:
                if export_raw:
                    nodes_export_raw(self.vfs_view_current().vfs(), self.vfs_view_current(), extract_dir)

                if export_contents:
                    nodes_export_contents(self.vfs_view_current().vfs(), self.vfs_view_current(), extract_dir)

                if export_map_full or export_map_tiles:
                    nodes_export_map(self.vfs_view_current().vfs(), self.vfs_view_current(), extract_dir, export_map_full, export_map_tiles)

                nodes_export_processed(
                    self.vfs_view_current().vfs(), self.vfs_view_current(), extract_dir,
                    allow_overwrite=False,
                    save_to_processed=save_to_processed,
                    save_to_text=save_to_text)

            except EDecaFileExists as exce:
                self.error_dialog('{} Canceled: File Exists: {}'.format(eid, exce.args))

    def extract_gltf(self, eid, extract_dir, save_to_one_dir, include_skeleton, texture_format):
        if self.vfs_view_current() and self.vfs_view_current().node_selected_count() > 0:
            try:
                nodes_export_gltf(
                    self.vfs_view_current().vfs(), self.vfs_view_current(), extract_dir,
                    allow_overwrite=False,
                    save_to_one_dir=save_to_one_dir,
                    include_skeleton=include_skeleton,
                    texture_format=texture_format)

            except EDecaFileExists as exce:
                self.error_dialog('{} Canceled: File Exists: {}'.format(eid, exce.args))

    def slot_folder_show_clicked(self, checked):
        if self.vfs_view_current() is not None:

            root = None
            path_required = False

            if self.sender() == self.ui.bt_extract_folder_show:
                root = UniPath.join(self.vfs_view_current().vfs().working_dir, 'extracted')
                path_required = True
            elif self.sender() == self.ui.bt_extract_gltf_3d_folder_show:
                root = UniPath.join(self.vfs_view_current().vfs().working_dir, 'gltf2_3d')
                path_required = True
            elif self.sender() == self.ui.bt_mod_folder_show:
                root = UniPath.join(self.vfs_view_current().vfs().working_dir, 'mod')
                path_required = True
            elif self.sender() == self.ui.bt_mod_build_folder_show:
                root = UniPath.join(self.vfs_view_current().vfs().working_dir, 'build')
                path_required = False

            if root:
                if path_required and (self.vfs_view_current().capture_count() > 0):
                    path = self.vfs_view_current().capture_path_common_prefix()
                    path = UniPath.join(root, path)
                    if not UniPath.isdir(path):
                        path = UniPath.dirname(path)
                else:
                    path = root

                #self.logger.log(f'View folder: {path}')

                if UniPath.isdir(path):
                    QDesktopServices.openUrl(QUrl(f'{path}'))
                else:
                    self.error_dialog(f'You must extract or process the files before you can use them. Directory does not exist: {path}')
                    self.logger.warning(f'Directory does not exist: {path}')
            else:
                self.logger.warning(f'There is no directory specified.')
        else:
            self.logger.warning(f'There is no VFS.')

    def slot_extract_clicked(self, checked):
        if self.vfs_view_current():
            self.extract(
                'Extraction', UniPath.join(self.vfs_view_current().vfs().working_dir, 'extracted'),
                export_raw=self.ui.chkbx_export_raw_extract.isChecked(),
                export_contents=self.ui.chkbx_export_contents_extract.isChecked(),
                save_to_processed=self.ui.chkbx_export_processed_extract.isChecked(),
                save_to_text=self.ui.chkbx_export_text_extract.isChecked(),
                export_map_full=self.ui.cmbbx_map_format.currentText().find('Full') > -1,
                export_map_tiles=self.ui.cmbbx_map_format.currentText().find('Tiles') > -1)

    def slot_extract_gltf_clicked(self, checked):
        if self.vfs_view_current():
            self.extract_gltf(
                'GLTF2 / 3D', UniPath.join(self.vfs_view_current().vfs().working_dir, 'gltf2_3d'),
                save_to_one_dir=self.ui.chkbx_export_save_to_one_dir.isChecked(),
                include_skeleton=self.ui.chkbx_export_3d_include_skeleton.isChecked(),
                texture_format=self.ui.cmbbx_texture_format.currentText())

    def slot_mod_build_subset_clicked(self, checked):
        if self.vfs_view_current():
            self.update_select_state(self.vfs_view_current())

    def slot_mod_prep_clicked(self, checked):
        if self.vfs_view_current():
            self.extract(
                'Mod Prep', UniPath.join(self.vfs_view_current().vfs().working_dir, 'mod'),
                export_raw=self.ui.chkbx_export_raw_mods.isChecked(),
                export_contents=self.ui.chkbx_export_contents_mods.isChecked(),
                save_to_processed=self.ui.chkbx_export_processed_mods.isChecked(),
                save_to_text=False,
                export_map_full=False,
                export_map_tiles=False)

    def slot_mod_build_clicked(self, checked):
        try:
            subset = None
            if self.ui.chkbx_mod_build_subset.isChecked():
                subset = self.vfs_view_current().nodes_selected_uids_get()

            self.builder.build_dir(
                self.vfs_view_current().vfs(),
                UniPath.join(self.vfs_view_current().vfs().working_dir, 'mod'),
                UniPath.join(self.vfs_view_current().vfs().working_dir, 'build'),
                subset=subset,
                symlink_changed_file=False,
                do_not_build_archive=self.ui.chkbx_mod_do_not_build_archives.isChecked()
            )
            self.dialog_good('BUILD SUCCESS')
        except EDecaFileExists as ex:
            self.error_dialog('Build Failed: File Exists: {}'.format(ex.args))
        except EDecaBuildError as ex:
            self.error_dialog('Build Failed: {}'.format(ex.args))

    def filter_text_get(self):
        txt = self.ui.filter_edit.text()

        if len(txt) == 0:
            txt = '^.*$'
        else:
            if txt[0] != '^':
                txt = '^' + txt
            if txt[-1] != '$':
                txt = txt + '$'

        return txt

    def filter_text_changed(self):
        txt = self.filter_text_get()
        
        valid = False
        changed = False
        has_vfs = self.vfs_view_current() is not None

        try:
            valid = True
            re.compile(txt)  # test compile
        except re.error as err:
            valid = False

        if self.vfs_view_current():
            changed = txt != to_unicode(self.vfs_view_current().mask)

        if not valid:
            ss = 'QLineEdit {background-color: red;}'
        elif not changed:
            ss = ''
        else:
            ss = 'QLineEdit {background-color: yellow;}'

        self.ui.filter_edit.setStyleSheet(ss)
        self.ui.filter_edit.setEnabled(has_vfs)
        self.ui.filter_set_bt.setEnabled(has_vfs and valid and changed)
        self.ui.filter_clear_bt.setEnabled(has_vfs and changed)

    def filter_text_key_release(self, source, event: QKeyEvent):
        if event.text() == '\r':
            if self.ui.filter_set_bt.isEnabled():
                self.filter_text_accepted(True)
        elif event.text() == '\x1b':
            self.filter_text_cleared(True)

    def filter_text_accepted(self, checked):
        if self.vfs_view_current():
            txt = self.filter_text_get()
            self.vfs_view_current().mask_set(txt.encode('ascii'))
            self.filter_text_changed()

    def filter_text_cleared(self, checked):
        if self.vfs_view_current():
            txt = to_unicode(self.vfs_view_current().mask)
        else:
            txt = '^.*$'
        self.ui.filter_edit.setText(txt)

    def vhash_to_vpath_text_changed(self):
        txt_in = self.ui.vhash_to_vpath_in_edit.text()

        txt_out = ''
        if self.vfs_view_current() is not None:
            try:
                val_in = int(txt_in, 0)
                strings = self.vfs_view_current().vfs().hash_string_match(hash32=val_in)
                for s in strings:
                    if len(s) > 0:
                        txt_out = s[1].decode('utf-8')
            except ValueError:
                pass

        self.ui.vhash_to_vpath_out_edit.setText(txt_out)

    @Slot()
    def project_new(self, checked):
        if os.name == 'nt':
            game_loc = 'C:/Program Files (x86)/Steam/steamapps/common/'
        else:
            game_loc = UniPath.expanduser('~/.steam/steamapps/common')

        filename = QFileDialog.getOpenFileName(self, 'Create Project ...', game_loc, 'Game EXE (*.exe *.EXE)')

        if filename is not None and len(filename[0]) > 0:
            vfs = vfs_structure_new(filename)
            if vfs is None:
                self.logger.log('Unknown Game {}'.format(filename))
            else:
                self.vfs_set(vfs)
                
        else:
            self.logger.log('No game executable file selected')

    @Slot()
    def project_open(self, checked):

        filename = QFileDialog.getOpenFileName(self, 'Open Project ...', UniPath.join(deca_root(), '..', 'work'),
                                               'Project File (project.json)')
        if filename is not None and len(filename[0]) > 0:
            project_file = filename[0]
            vfs = vfs_structure_open(project_file)
            self.vfs_set(vfs)
        else:
            self.logger.log('No project file selected')

    @Slot()
    def external_add(self, checked):
        filenames, selected_filter = QFileDialog.getOpenFileNames(self, 'Open External File ...', '.', 'Any File (*)')
        if filenames:
            for filename in filenames:
                if len(filename) > 0:
                    self.vfs_view_current().vfs().external_file_add(filename)
        else:
            self.logger.log('No file selected')

    @Slot()
    def file_gz_open(self, checked):
        filenames, selected_filter = QFileDialog.getOpenFileNames(self, 'Open GZ File ...',
                                                                  UniPath.join(deca_root(), '..', 'work'),
                                                                  'Any File (*)')

        if filenames and len(filenames[0]) > 0:
            path, _ = UniPath.split(filenames[0])
            vfs = vfs_structure_empty(path, 'GenerationZero')
            self.vfs_set(vfs)
            for filename in filenames:
                if len(filename) > 0:
                    self.vfs_view_current().vfs().external_file_add(filename)
        else:
            self.logger.log('No GenZero file selected')

    @Slot()
    def exit_app(self, checked):
        self.close()

    @Slot()
    def tool_make_web_map(self, checked):
        tool = ToolMakeWebMap(self.vfs_view_current().vfs())
        tool.make_web_map(self.vfs_view_current().vfs().working_dir, True)


def main():
    # options = argparse.ArgumentParser()
    # options.add_argument("-f", "--file", type=str, required=True)
    # args = options.parse_args()

    deca_root()

    # Qt Application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle(window_title)
    window.show()
    app.exec_()

    return window.vfs
