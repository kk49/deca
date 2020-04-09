import sys
import os
from deca.errors import *
from deca.db_processor import vfs_structure_new, vfs_structure_open, VfsNode
from deca.builder import Builder
from deca.util import Logger
from deca.cmds.tool_make_web_map import ToolMakeWebMap
from deca.export_import import nodes_export_raw, nodes_export_contents, nodes_export_processed, nodes_export_gltf
from .main_window import Ui_MainWindow
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog


window_title = 'decaGUI: v0.2.8'


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.vfs = None
        self.logger = Logger('./')

        self.builder = Builder()
        self.current_vnode = None
        self.current_vpaths = None
        self.filter_mask = b'^.*$'

        # Configure Actions
        self.ui.action_project_new.triggered.connect(self.project_new)
        self.ui.action_project_open.triggered.connect(self.project_open)
        self.ui.action_external_add.triggered.connect(self.external_add)
        self.ui.action_external_add.setEnabled(False)
        # self.ui.action_external_manage.triggered.connect(self.external_manage)
        self.ui.action_exit.triggered.connect(self.exit_app)
        self.ui.action_make_web_map.triggered.connect(self.tool_make_web_map)

        # Configure VFS Node table (all nodes)
        self.ui.vfs_node_widget.show_all_set(True)
        self.ui.vfs_node_widget.vnode_selection_changed = self.vnode_selection_changed
        self.ui.vfs_node_widget.vnode_2click_selected = self.vnode_2click_selected

        # Configure VFS Node table (non-mapped nodes)
        self.ui.vfs_node_widget_non_mapped.show_all_set(False)
        self.ui.vfs_node_widget_non_mapped.vnode_selection_changed = self.vnode_selection_changed
        self.ui.vfs_node_widget_non_mapped.vnode_2click_selected = self.vnode_2click_selected

        # Configure VFS dir table
        self.ui.vfs_dir_widget.vnode_selection_changed = self.vnode_selection_changed
        self.ui.vfs_dir_widget.vnode_2click_selected = self.vnode_2click_selected

        # filter
        self.ui.filter_edit.textChanged.connect(self.filter_text_changed)

        self.ui.vhash_to_vpath_in_edit.textChanged.connect(self.vhash_to_vpath_text_changed)

        self.ui.chkbx_export_raw_extract.setChecked(True)
        self.ui.chkbx_export_contents_extract.setChecked(False)
        self.ui.chkbx_export_text_extract.setChecked(False)
        self.ui.chkbx_export_processed_extract.setChecked(False)

        self.ui.chkbx_export_raw_mods.setChecked(True)
        self.ui.chkbx_export_contents_mods.setChecked(False)
        self.ui.chkbx_export_processed_mods.setChecked(False)

        self.ui.chkbx_export_save_to_one_dir.setChecked(False)

        self.ui.bt_extract.setEnabled(False)
        self.ui.bt_extract.clicked.connect(self.slot_extract_clicked)

        self.ui.bt_extract_gltf_3d.setEnabled(False)
        self.ui.bt_extract_gltf_3d.clicked.connect(self.slot_extract_gltf_clicked)

        self.ui.bt_mod_prep.setEnabled(False)
        self.ui.bt_mod_prep.clicked.connect(self.slot_mod_prep_clicked)

        self.ui.bt_mod_build.clicked.connect(self.slot_mod_build_clicked)

    def vfs_set(self, vfs):
        self.vfs = vfs
        self.setWindowTitle("{}: Archive: {}".format(window_title, vfs.game_info.game_dir))
        self.ui.statusbar.showMessage("LOAD COMPLETE")
        self.vfs_reload()
        self.ui.action_external_add.setEnabled(True)

    def vfs_reload(self):
        self.ui.vfs_node_widget.vfs_set(self.vfs)
        self.ui.vfs_node_widget_non_mapped.vfs_set(self.vfs)
        self.ui.vfs_dir_widget.vfs_set(self.vfs)
        self.ui.data_view.vfs_set(self.vfs)

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

    def vnode_selection_changed(self, vpaths):
        self.current_vpaths = vpaths
        if self.current_vpaths is None or len(self.current_vpaths) == 0:
            self.ui.bt_extract.setEnabled(False)
            self.ui.bt_extract_gltf_3d.setEnabled(False)
            self.ui.bt_mod_prep.setEnabled(False)
            str_vpaths = ''
        else:
            self.ui.bt_extract.setEnabled(True)
            self.ui.bt_extract_gltf_3d.setEnabled(True)
            self.ui.bt_mod_prep.setEnabled(True)

            if len(self.current_vpaths) == 1:
                if isinstance(vpaths[0], bytes):
                    str_vpaths = vpaths[0].decode('utf-8')
                else:
                    str_vpaths = vpaths[0]
            else:
                str_vpaths = '**MULTIPLE**'

        self.ui.bt_extract.setText('EXTRACT: {}'.format(str_vpaths))
        self.ui.bt_extract_gltf_3d.setText('EXTRACT 3D/GLTF2: {}'.format(str_vpaths))
        self.ui.bt_mod_prep.setText('PREP MOD: {}'.format(str_vpaths))

        self.ui.data_view.vnode_selection_changed(vpaths)

    def vnode_2click_selected(self, vnode: VfsNode):
        self.current_vnode = vnode
        self.ui.data_view.vnode_2click_selected(vnode)
        # if self.current_vnode is not None:
        #     self.ui.bt_extract.setText('EXTRACT: {}'.format(vnode.v_path))
        #     self.ui.bt_extract.setEnabled(True)

    def extract(self, eid, extract_dir, export_raw, export_contents, save_to_processed, save_to_text):
        if self.current_vpaths:
            try:
                if export_raw:
                    nodes_export_raw(self.vfs, self.current_vpaths, self.filter_mask, extract_dir)

                if export_contents:
                    nodes_export_contents(self.vfs, self.current_vpaths, self.filter_mask, extract_dir)

                nodes_export_processed(
                    self.vfs, self.current_vpaths, self.filter_mask, extract_dir,
                    allow_overwrite=False,
                    save_to_processed=save_to_processed,
                    save_to_text=save_to_text)

            except EDecaFileExists as exce:
                self.error_dialog('{} Canceled: File Exists: {}'.format(eid, exce.args))

    def extract_gltf(self, eid, extract_dir, save_to_one_dir):
        if self.current_vpaths:
            try:
                nodes_export_gltf(
                    self.vfs, self.current_vpaths, self.filter_mask, extract_dir,
                    allow_overwrite=False,
                    save_to_one_dir=save_to_one_dir)

            except EDecaFileExists as exce:
                self.error_dialog('{} Canceled: File Exists: {}'.format(eid, exce.args))

    def slot_extract_clicked(self, checked):
        self.extract(
            'Extraction', self.vfs.working_dir + 'extracted/',
            export_raw=self.ui.chkbx_export_raw_extract.isChecked(),
            export_contents=self.ui.chkbx_export_contents_extract.isChecked(),
            save_to_processed=self.ui.chkbx_export_processed_extract.isChecked(),
            save_to_text=self.ui.chkbx_export_text_extract.isChecked(),
        )

    def slot_extract_gltf_clicked(self, checked):
        self.extract_gltf(
            'GLTF2 / 3D', self.vfs.working_dir + 'gltf2_3d/',
            save_to_one_dir=self.ui.chkbx_export_save_to_one_dir.isChecked(),
        )

    def slot_mod_prep_clicked(self, checked):
        self.extract(
            'Mod Prep', self.vfs.working_dir + 'mod/',
            export_raw=self.ui.chkbx_export_raw_mods.isChecked(),
            export_contents=self.ui.chkbx_export_contents_mods.isChecked(),
            save_to_processed=self.ui.chkbx_export_processed_mods.isChecked(),
            save_to_text=False,
        )

    def slot_mod_build_clicked(self, checked):
        try:
            self.builder.build_dir(self.vfs, self.vfs.working_dir + 'mod/', self.vfs.working_dir + 'build/')
            self.dialog_good('BUILD SUCCESS')
        except EDecaFileExists as exce:
            self.error_dialog('Build Failed: File Exists: {}'.format(exce.args))
        except EDecaBuildError as exce:
            self.error_dialog('Build Failed: {}'.format(exce.args))

    def filter_text_changed(self):
        txt = self.ui.filter_edit.text()
        if len(txt) == 0:
            txt = '^.*$'
        else:
            if txt[0] != '^':
                txt = '^' + txt
            if txt[-1] != '$':
                txt = txt + '$'

        self.filter_mask = txt.encode('ascii')
        self.ui.vfs_dir_widget.filter_vfspath_set(txt)

    def vhash_to_vpath_text_changed(self):
        txt_in = self.vhash_to_vpath_in_edit.text()

        txt_out = ''
        if self.vfs is not None:
            try:
                val_in = int(txt_in, 0)
                nodes = self.vfs.nodes_where_v_hash(val_in)
                for node in nodes:
                    if len(node.v_path) > 0:
                        txt_out = node.v_path.decode('utf-8')
            except ValueError:
                pass

        self.vhash_to_vpath_out_edit.setText(txt_out)

    @Slot()
    def project_new(self, checked):
        if os.name == 'nt':
            game_loc = 'C:/Program Files(x86)/Steam/steamapps/common/'
        else:
            game_loc = os.path.expanduser('~/.steam/steamapps/common')

        filename = QFileDialog.getOpenFileName(self, 'Create Project ...', game_loc, 'Game EXE (*.exe *.EXE)')

        if filename is not None and len(filename[0]) > 0:
            vfs = vfs_structure_new(filename)
            if vfs is None:
                self.logger.log('Unknown Game {}'.format(filename))
            else:
                self.vfs_set(vfs)
        else:
            self.logger.log('Cannot Create {}'.format(filename))

    @Slot()
    def project_open(self, checked):
        filename = QFileDialog.getOpenFileName(self, 'Open Project ...', '../work', 'Project File (project.json)')
        if filename is not None and len(filename[0]) > 0:
            project_file = filename[0]
            vfs = vfs_structure_open(project_file)
            self.vfs_set(vfs)
        else:
            self.logger.log('Cannot Open {}'.format(filename))

    @Slot()
    def external_add(self, checked):
        filename = QFileDialog.getOpenFileName(self, 'Open External File ...', '.', 'Any File (*)')
        if filename is not None and len(filename[0]) > 0:
            filename = filename[0]
            self.vfs.external_file_add(filename)
            self.vfs_reload()
        else:
            self.logger.log('Cannot Open {}'.format(filename))

    @Slot()
    def exit_app(self, checked):
        self.close()

    @Slot()
    def tool_make_web_map(self, checked):
        tool = ToolMakeWebMap(self.vfs)
        tool.make_web_map(self.vfs.working_dir, True)


def main():
    # options = argparse.ArgumentParser()
    # options.add_argument("-f", "--file", type=str, required=True)
    # args = options.parse_args()

    # Qt Application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle(window_title)
    window.show()
    app.exec_()

    return window.vfs
