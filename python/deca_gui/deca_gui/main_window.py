# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QStatusBar, QTabWidget,
    QVBoxLayout, QWidget)

from .dataviewwidget import DataViewWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(960, 600)
        self.action_project_new = QAction(MainWindow)
        self.action_project_new.setObjectName(u"action_project_new")
        self.action_project_open = QAction(MainWindow)
        self.action_project_open.setObjectName(u"action_project_open")
        self.action_external_add = QAction(MainWindow)
        self.action_external_add.setObjectName(u"action_external_add")
        self.action_exit = QAction(MainWindow)
        self.action_exit.setObjectName(u"action_exit")
        self.action_make_web_map = QAction(MainWindow)
        self.action_make_web_map.setObjectName(u"action_make_web_map")
        self.action_file_gz_open = QAction(MainWindow)
        self.action_file_gz_open.setObjectName(u"action_file_gz_open")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget_layout = QVBoxLayout(self.centralwidget)
        self.centralwidget_layout.setObjectName(u"centralwidget_layout")
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(7)
        self.splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.vertical_layout = QVBoxLayout(self.layoutWidget)
        self.vertical_layout.setObjectName(u"vertical_layout")
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_nodes = QTabWidget(self.layoutWidget)
        self.tabs_nodes.setObjectName(u"tabs_nodes")
        self.tabs_nodes.setTabsClosable(True)

        self.vertical_layout.addWidget(self.tabs_nodes)

        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.setObjectName(u"horizontal_layout")
        self.horizontal_layout.setContentsMargins(1, 1, 1, 1)
        self.filter_label = QLabel(self.layoutWidget)
        self.filter_label.setObjectName(u"filter_label")

        self.horizontal_layout.addWidget(self.filter_label)

        self.filter_edit = QLineEdit(self.layoutWidget)
        self.filter_edit.setObjectName(u"filter_edit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filter_edit.sizePolicy().hasHeightForWidth())
        self.filter_edit.setSizePolicy(sizePolicy)

        self.horizontal_layout.addWidget(self.filter_edit)

        self.filter_set_bt = QPushButton(self.layoutWidget)
        self.filter_set_bt.setObjectName(u"filter_set_bt")

        self.horizontal_layout.addWidget(self.filter_set_bt)

        self.filter_clear_bt = QPushButton(self.layoutWidget)
        self.filter_clear_bt.setObjectName(u"filter_clear_bt")

        self.horizontal_layout.addWidget(self.filter_clear_bt)

        self.horizontal_layout.setStretch(1, 1)

        self.vertical_layout.addLayout(self.horizontal_layout)

        self.tabs_control = QTabWidget(self.layoutWidget)
        self.tabs_control.setObjectName(u"tabs_control")
        self.tab_extract = QWidget()
        self.tab_extract.setObjectName(u"tab_extract")
        self.grid_layout_1 = QGridLayout(self.tab_extract)
        self.grid_layout_1.setObjectName(u"grid_layout_1")
        self.cmbbx_map_format = QComboBox(self.tab_extract)
        self.cmbbx_map_format.addItem("")
        self.cmbbx_map_format.addItem("")
        self.cmbbx_map_format.addItem("")
        self.cmbbx_map_format.setObjectName(u"cmbbx_map_format")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.cmbbx_map_format.sizePolicy().hasHeightForWidth())
        self.cmbbx_map_format.setSizePolicy(sizePolicy1)
        self.cmbbx_map_format.setMinimumSize(QSize(96, 0))

        self.grid_layout_1.addWidget(self.cmbbx_map_format, 4, 1, 1, 2)

        self.chkbx_export_contents_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_contents_extract.setObjectName(u"chkbx_export_contents_extract")

        self.grid_layout_1.addWidget(self.chkbx_export_contents_extract, 2, 0, 1, 1)

        self.chkbx_export_text_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_text_extract.setObjectName(u"chkbx_export_text_extract")

        self.grid_layout_1.addWidget(self.chkbx_export_text_extract, 3, 0, 1, 1)

        self.chkbx_export_map = QCheckBox(self.tab_extract)
        self.chkbx_export_map.setObjectName(u"chkbx_export_map")

        self.grid_layout_1.addWidget(self.chkbx_export_map, 4, 0, 1, 1)

        self.chkbx_export_raw_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_raw_extract.setObjectName(u"chkbx_export_raw_extract")

        self.grid_layout_1.addWidget(self.chkbx_export_raw_extract, 0, 0, 1, 1)

        self.chkbx_export_processed_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_processed_extract.setObjectName(u"chkbx_export_processed_extract")

        self.grid_layout_1.addWidget(self.chkbx_export_processed_extract, 1, 0, 1, 1)

        self.bt_extract = QPushButton(self.tab_extract)
        self.bt_extract.setObjectName(u"bt_extract")

        self.grid_layout_1.addWidget(self.bt_extract, 0, 2, 1, 2)

        self.bt_extract_folder_show = QPushButton(self.tab_extract)
        self.bt_extract_folder_show.setObjectName(u"bt_extract_folder_show")
        sizePolicy1.setHeightForWidth(self.bt_extract_folder_show.sizePolicy().hasHeightForWidth())
        self.bt_extract_folder_show.setSizePolicy(sizePolicy1)

        self.grid_layout_1.addWidget(self.bt_extract_folder_show, 0, 1, 1, 1)

        self.tab_extract_hspacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.grid_layout_1.addItem(self.tab_extract_hspacer, 0, 4, 1, 1)

        self.grid_layout_1.setRowMinimumHeight(0, 24)
        self.grid_layout_1.setRowMinimumHeight(1, 24)
        self.grid_layout_1.setRowMinimumHeight(2, 24)
        self.grid_layout_1.setRowMinimumHeight(3, 24)
        self.grid_layout_1.setRowMinimumHeight(4, 24)
        self.tabs_control.addTab(self.tab_extract, "")
        self.tab_modding = QWidget()
        self.tab_modding.setObjectName(u"tab_modding")
        self.grid_layout_2 = QGridLayout(self.tab_modding)
        self.grid_layout_2.setObjectName(u"grid_layout_2")
        self.chkbx_export_processed_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_processed_mods.setObjectName(u"chkbx_export_processed_mods")

        self.grid_layout_2.addWidget(self.chkbx_export_processed_mods, 1, 0, 1, 1)

        self.chkbx_mod_build_subset = QCheckBox(self.tab_modding)
        self.chkbx_mod_build_subset.setObjectName(u"chkbx_mod_build_subset")

        self.grid_layout_2.addWidget(self.chkbx_mod_build_subset, 3, 0, 1, 1)

        self.bt_mod_folder_show = QPushButton(self.tab_modding)
        self.bt_mod_folder_show.setObjectName(u"bt_mod_folder_show")
        sizePolicy1.setHeightForWidth(self.bt_mod_folder_show.sizePolicy().hasHeightForWidth())
        self.bt_mod_folder_show.setSizePolicy(sizePolicy1)

        self.grid_layout_2.addWidget(self.bt_mod_folder_show, 0, 1, 1, 1)

        self.chkbx_export_raw_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_raw_mods.setObjectName(u"chkbx_export_raw_mods")

        self.grid_layout_2.addWidget(self.chkbx_export_raw_mods, 0, 0, 1, 1)

        self.bt_mod_prep = QPushButton(self.tab_modding)
        self.bt_mod_prep.setObjectName(u"bt_mod_prep")

        self.grid_layout_2.addWidget(self.bt_mod_prep, 0, 2, 1, 1)

        self.bt_mod_build = QPushButton(self.tab_modding)
        self.bt_mod_build.setObjectName(u"bt_mod_build")

        self.grid_layout_2.addWidget(self.bt_mod_build, 1, 2, 1, 1)

        self.chkbx_export_contents_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_contents_mods.setObjectName(u"chkbx_export_contents_mods")

        self.grid_layout_2.addWidget(self.chkbx_export_contents_mods, 2, 0, 1, 1)

        self.bt_mod_build_folder_show = QPushButton(self.tab_modding)
        self.bt_mod_build_folder_show.setObjectName(u"bt_mod_build_folder_show")
        sizePolicy1.setHeightForWidth(self.bt_mod_build_folder_show.sizePolicy().hasHeightForWidth())
        self.bt_mod_build_folder_show.setSizePolicy(sizePolicy1)

        self.grid_layout_2.addWidget(self.bt_mod_build_folder_show, 1, 1, 1, 1)

        self.chkbx_mod_do_not_build_archives = QCheckBox(self.tab_modding)
        self.chkbx_mod_do_not_build_archives.setObjectName(u"chkbx_mod_do_not_build_archives")

        self.grid_layout_2.addWidget(self.chkbx_mod_do_not_build_archives, 4, 0, 1, 3)

        self.tab_modding_hspacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.grid_layout_2.addItem(self.tab_modding_hspacer, 0, 3, 1, 1)

        self.grid_layout_2.setRowMinimumHeight(0, 24)
        self.grid_layout_2.setRowMinimumHeight(1, 24)
        self.grid_layout_2.setRowMinimumHeight(2, 24)
        self.grid_layout_2.setRowMinimumHeight(3, 24)
        self.grid_layout_2.setRowMinimumHeight(4, 24)
        self.tabs_control.addTab(self.tab_modding, "")
        self.tab_3d_gltf2 = QWidget()
        self.tab_3d_gltf2.setObjectName(u"tab_3d_gltf2")
        self.grid_layout_3 = QGridLayout(self.tab_3d_gltf2)
        self.grid_layout_3.setObjectName(u"grid_layout_3")
        self.chkbx_export_save_to_one_dir = QCheckBox(self.tab_3d_gltf2)
        self.chkbx_export_save_to_one_dir.setObjectName(u"chkbx_export_save_to_one_dir")

        self.grid_layout_3.addWidget(self.chkbx_export_save_to_one_dir, 0, 0, 1, 1)

        self.cmbbx_texture_format = QComboBox(self.tab_3d_gltf2)
        self.cmbbx_texture_format.addItem("")
        self.cmbbx_texture_format.addItem("")
        self.cmbbx_texture_format.addItem("")
        self.cmbbx_texture_format.setObjectName(u"cmbbx_texture_format")
        sizePolicy1.setHeightForWidth(self.cmbbx_texture_format.sizePolicy().hasHeightForWidth())
        self.cmbbx_texture_format.setSizePolicy(sizePolicy1)
        self.cmbbx_texture_format.setMinimumSize(QSize(64, 0))

        self.grid_layout_3.addWidget(self.cmbbx_texture_format, 4, 1, 1, 2)

        self.bt_extract_gltf_3d_folder_show = QPushButton(self.tab_3d_gltf2)
        self.bt_extract_gltf_3d_folder_show.setObjectName(u"bt_extract_gltf_3d_folder_show")
        sizePolicy1.setHeightForWidth(self.bt_extract_gltf_3d_folder_show.sizePolicy().hasHeightForWidth())
        self.bt_extract_gltf_3d_folder_show.setSizePolicy(sizePolicy1)

        self.grid_layout_3.addWidget(self.bt_extract_gltf_3d_folder_show, 0, 1, 1, 1)

        self.tab_3d_hspacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.grid_layout_3.addItem(self.tab_3d_hspacer, 0, 3, 1, 1)

        self.lbl_texture_format = QLabel(self.tab_3d_gltf2)
        self.lbl_texture_format.setObjectName(u"lbl_texture_format")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.lbl_texture_format.sizePolicy().hasHeightForWidth())
        self.lbl_texture_format.setSizePolicy(sizePolicy2)

        self.grid_layout_3.addWidget(self.lbl_texture_format, 4, 0, 1, 1)

        self.chkbx_export_3d_include_skeleton = QCheckBox(self.tab_3d_gltf2)
        self.chkbx_export_3d_include_skeleton.setObjectName(u"chkbx_export_3d_include_skeleton")

        self.grid_layout_3.addWidget(self.chkbx_export_3d_include_skeleton, 1, 0, 1, 1)

        self.bt_extract_gltf_3d = QPushButton(self.tab_3d_gltf2)
        self.bt_extract_gltf_3d.setObjectName(u"bt_extract_gltf_3d")

        self.grid_layout_3.addWidget(self.bt_extract_gltf_3d, 0, 2, 1, 1)

        self.tab_32_label_1 = QLabel(self.tab_3d_gltf2)
        self.tab_32_label_1.setObjectName(u"tab_32_label_1")
        sizePolicy2.setHeightForWidth(self.tab_32_label_1.sizePolicy().hasHeightForWidth())
        self.tab_32_label_1.setSizePolicy(sizePolicy2)

        self.grid_layout_3.addWidget(self.tab_32_label_1, 2, 0, 1, 1)

        self.tab_32_label_2 = QLabel(self.tab_3d_gltf2)
        self.tab_32_label_2.setObjectName(u"tab_32_label_2")
        sizePolicy2.setHeightForWidth(self.tab_32_label_2.sizePolicy().hasHeightForWidth())
        self.tab_32_label_2.setSizePolicy(sizePolicy2)

        self.grid_layout_3.addWidget(self.tab_32_label_2, 3, 0, 1, 1)

        self.grid_layout_3.setRowMinimumHeight(0, 24)
        self.grid_layout_3.setRowMinimumHeight(1, 24)
        self.grid_layout_3.setRowMinimumHeight(2, 24)
        self.grid_layout_3.setRowMinimumHeight(3, 24)
        self.grid_layout_3.setRowMinimumHeight(4, 24)
        self.tabs_control.addTab(self.tab_3d_gltf2, "")
        self.tab_utils = QWidget()
        self.tab_utils.setObjectName(u"tab_utils")
        self.grid_layout_4 = QGridLayout(self.tab_utils)
        self.grid_layout_4.setObjectName(u"grid_layout_4")
        self.vhash_to_vpath_out_edit = QLineEdit(self.tab_utils)
        self.vhash_to_vpath_out_edit.setObjectName(u"vhash_to_vpath_out_edit")
        self.vhash_to_vpath_out_edit.setReadOnly(True)

        self.grid_layout_4.addWidget(self.vhash_to_vpath_out_edit, 0, 2, 1, 1)

        self.vhash_to_vpath_label = QLabel(self.tab_utils)
        self.vhash_to_vpath_label.setObjectName(u"vhash_to_vpath_label")

        self.grid_layout_4.addWidget(self.vhash_to_vpath_label, 0, 0, 1, 1)

        self.vhash_to_vpath_in_edit = QLineEdit(self.tab_utils)
        self.vhash_to_vpath_in_edit.setObjectName(u"vhash_to_vpath_in_edit")

        self.grid_layout_4.addWidget(self.vhash_to_vpath_in_edit, 0, 1, 1, 1)

        self.tab_utils_vspacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.grid_layout_4.addItem(self.tab_utils_vspacer, 1, 0, 1, 1)

        self.grid_layout_4.setColumnStretch(2, 1)
        self.grid_layout_4.setRowMinimumHeight(0, 24)
        self.tabs_control.addTab(self.tab_utils, "")

        self.vertical_layout.addWidget(self.tabs_control)

        self.vertical_layout.setStretch(0, 1)
        self.splitter.addWidget(self.layoutWidget)
        self.data_view = DataViewWidget(self.splitter)
        self.data_view.setObjectName(u"data_view")
        self.splitter.addWidget(self.data_view)

        self.centralwidget_layout.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 960, 22))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        self.menu_Tools = QMenu(self.menubar)
        self.menu_Tools.setObjectName(u"menu_Tools")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menu_Tools.menuAction())
        self.menu_File.addAction(self.action_project_new)
        self.menu_File.addAction(self.action_project_open)
        self.menu_File.addAction(self.action_file_gz_open)
        self.menu_File.addAction(self.action_external_add)
        self.menu_File.addAction(self.action_exit)
        self.menu_Tools.addAction(self.action_make_web_map)

        self.retranslateUi(MainWindow)

        self.tabs_nodes.setCurrentIndex(-1)
        self.tabs_control.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"DECA Main Window", None))
        self.action_project_new.setText(QCoreApplication.translate("MainWindow", u"&New Project...", None))
        self.action_project_open.setText(QCoreApplication.translate("MainWindow", u"&Open Project...", None))
        self.action_external_add.setText(QCoreApplication.translate("MainWindow", u"&Add External...", None))
        self.action_exit.setText(QCoreApplication.translate("MainWindow", u"E&xit", None))
#if QT_CONFIG(shortcut)
        self.action_exit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.action_make_web_map.setText(QCoreApplication.translate("MainWindow", u"Make &Web Map...", None))
        self.action_file_gz_open.setText(QCoreApplication.translate("MainWindow", u"Open GenZero File...", None))
        self.filter_label.setText(QCoreApplication.translate("MainWindow", u"Filter (Python Expression Syntax)", None))
        self.filter_edit.setText("")
        self.filter_set_bt.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.filter_clear_bt.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.cmbbx_map_format.setItemText(0, QCoreApplication.translate("MainWindow", u"Full", None))
        self.cmbbx_map_format.setItemText(1, QCoreApplication.translate("MainWindow", u"Tiles", None))
        self.cmbbx_map_format.setItemText(2, QCoreApplication.translate("MainWindow", u"Full + Tiles", None))

        self.chkbx_export_contents_extract.setText(QCoreApplication.translate("MainWindow", u"Export Contents", None))
        self.chkbx_export_text_extract.setText(QCoreApplication.translate("MainWindow", u"Export As Text", None))
        self.chkbx_export_map.setText(QCoreApplication.translate("MainWindow", u"Export Map", None))
        self.chkbx_export_raw_extract.setText(QCoreApplication.translate("MainWindow", u"Export Raw Files", None))
        self.chkbx_export_processed_extract.setText(QCoreApplication.translate("MainWindow", u"Export As Processed", None))
        self.bt_extract.setText(QCoreApplication.translate("MainWindow", u"EXTRACT", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_extract), QCoreApplication.translate("MainWindow", u"Extract", None))
        self.chkbx_export_processed_mods.setText(QCoreApplication.translate("MainWindow", u"Export As Processed", None))
        self.chkbx_mod_build_subset.setText(QCoreApplication.translate("MainWindow", u"Build Subset", None))
        self.chkbx_export_raw_mods.setText(QCoreApplication.translate("MainWindow", u"Export Raw Files", None))
        self.bt_mod_prep.setText(QCoreApplication.translate("MainWindow", u"PREP MOD", None))
        self.bt_mod_build.setText(QCoreApplication.translate("MainWindow", u"BUILD MOD", None))
        self.chkbx_export_contents_mods.setText(QCoreApplication.translate("MainWindow", u"Export Contents", None))
        self.chkbx_mod_do_not_build_archives.setText(QCoreApplication.translate("MainWindow", u"Do Not Build Archives", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_modding), QCoreApplication.translate("MainWindow", u"Modding", None))
        self.chkbx_export_save_to_one_dir.setText(QCoreApplication.translate("MainWindow", u"Save To One Directory", None))
        self.cmbbx_texture_format.setItemText(0, QCoreApplication.translate("MainWindow", u"DDS", None))
        self.cmbbx_texture_format.setItemText(1, QCoreApplication.translate("MainWindow", u"DDSC", None))
        self.cmbbx_texture_format.setItemText(2, QCoreApplication.translate("MainWindow", u"PNG", None))

        self.lbl_texture_format.setText(QCoreApplication.translate("MainWindow", u"Texture Format", None))
        self.chkbx_export_3d_include_skeleton.setText(QCoreApplication.translate("MainWindow", u"Include Skeleton", None))
        self.bt_extract_gltf_3d.setText(QCoreApplication.translate("MainWindow", u"EXTRACT 3D/GLTF2", None))
        self.tab_32_label_1.setText("")
        self.tab_32_label_2.setText("")
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_3d_gltf2), QCoreApplication.translate("MainWindow", u"3D/GLTF2", None))
        self.vhash_to_vpath_label.setText(QCoreApplication.translate("MainWindow", u"VHash -> VPath", None))
        self.vhash_to_vpath_in_edit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_utils), QCoreApplication.translate("MainWindow", u"Utils", None))
        self.menu_File.setTitle(QCoreApplication.translate("MainWindow", u"&File", None))
        self.menu_Tools.setTitle(QCoreApplication.translate("MainWindow", u"&Tools", None))
    # retranslateUi

