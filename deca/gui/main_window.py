# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 5.14.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import (QCoreApplication, QMetaObject, QObject, QPoint,
    QRect, QSize, QUrl, Qt)
from PySide2.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont,
    QFontDatabase, QIcon, QLinearGradient, QPalette, QPainter, QPixmap,
    QRadialGradient)
from PySide2.QtWidgets import *

from .vfsnodetablewidget import VfsNodeTableWidget
from .vfsdirwidget import VfsDirWidget
from .dataviewwidget import DataViewWidget


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(617, 599)
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
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(-1, 0, 0, 0)
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setHandleWidth(16)
        self.splitter.setChildrenCollapsible(False)
        self.widget = QWidget(self.splitter)
        self.widget.setObjectName(u"widget")
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.tabs_nodes = QTabWidget(self.widget)
        self.tabs_nodes.setObjectName(u"tabs_nodes")
        self.tab_directory = QWidget()
        self.tab_directory.setObjectName(u"tab_directory")
        self.horizontalLayout = QHBoxLayout(self.tab_directory)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(6, 6, 6, 6)
        self.vfs_dir_widget = VfsDirWidget(self.tab_directory)
        self.vfs_dir_widget.setObjectName(u"vfs_dir_widget")

        self.horizontalLayout.addWidget(self.vfs_dir_widget)

        self.tabs_nodes.addTab(self.tab_directory, "")
        self.tab_non_mapped_list = QWidget()
        self.tab_non_mapped_list.setObjectName(u"tab_non_mapped_list")
        self.horizontalLayout_2 = QHBoxLayout(self.tab_non_mapped_list)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(6, 6, 6, 6)
        self.vfs_node_widget_non_mapped = VfsNodeTableWidget(self.tab_non_mapped_list)
        self.vfs_node_widget_non_mapped.setObjectName(u"vfs_node_widget_non_mapped")

        self.horizontalLayout_2.addWidget(self.vfs_node_widget_non_mapped)

        self.tabs_nodes.addTab(self.tab_non_mapped_list, "")
        self.tab_raw_list = QWidget()
        self.tab_raw_list.setObjectName(u"tab_raw_list")
        self.horizontalLayout_3 = QHBoxLayout(self.tab_raw_list)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(6, 6, 6, 6)
        self.vfs_node_widget = VfsNodeTableWidget(self.tab_raw_list)
        self.vfs_node_widget.setObjectName(u"vfs_node_widget")

        self.horizontalLayout_3.addWidget(self.vfs_node_widget)

        self.tabs_nodes.addTab(self.tab_raw_list, "")

        self.verticalLayout.addWidget(self.tabs_nodes)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.filter_label = QLabel(self.widget)
        self.filter_label.setObjectName(u"filter_label")

        self.horizontalLayout_4.addWidget(self.filter_label)

        self.filter_edit = QLineEdit(self.widget)
        self.filter_edit.setObjectName(u"filter_edit")

        self.horizontalLayout_4.addWidget(self.filter_edit)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.vhash_to_vpath_label = QLabel(self.widget)
        self.vhash_to_vpath_label.setObjectName(u"vhash_to_vpath_label")

        self.horizontalLayout_5.addWidget(self.vhash_to_vpath_label)

        self.vhash_to_vpath_in_edit = QLineEdit(self.widget)
        self.vhash_to_vpath_in_edit.setObjectName(u"vhash_to_vpath_in_edit")

        self.horizontalLayout_5.addWidget(self.vhash_to_vpath_in_edit)

        self.vhash_to_vpath_out_edit = QLineEdit(self.widget)
        self.vhash_to_vpath_out_edit.setObjectName(u"vhash_to_vpath_out_edit")
        self.vhash_to_vpath_out_edit.setReadOnly(True)

        self.horizontalLayout_5.addWidget(self.vhash_to_vpath_out_edit)

        self.horizontalLayout_5.setStretch(2, 2)

        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.tabs_control = QTabWidget(self.widget)
        self.tabs_control.setObjectName(u"tabs_control")
        self.tab_extract = QWidget()
        self.tab_extract.setObjectName(u"tab_extract")
        self.gridLayout = QGridLayout(self.tab_extract)
        self.gridLayout.setObjectName(u"gridLayout")
        self.chkbx_export_text_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_text_extract.setObjectName(u"chkbx_export_text_extract")

        self.gridLayout.addWidget(self.chkbx_export_text_extract, 1, 0, 1, 1)

        self.chkbx_export_contents_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_contents_extract.setObjectName(u"chkbx_export_contents_extract")

        self.gridLayout.addWidget(self.chkbx_export_contents_extract, 5, 0, 1, 1)

        self.bt_extract = QPushButton(self.tab_extract)
        self.bt_extract.setObjectName(u"bt_extract")

        self.gridLayout.addWidget(self.bt_extract, 0, 1, 1, 1)

        self.chkbx_export_raw_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_raw_extract.setObjectName(u"chkbx_export_raw_extract")

        self.gridLayout.addWidget(self.chkbx_export_raw_extract, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.chkbx_export_processed_extract = QCheckBox(self.tab_extract)
        self.chkbx_export_processed_extract.setObjectName(u"chkbx_export_processed_extract")

        self.gridLayout.addWidget(self.chkbx_export_processed_extract, 4, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 2, 1, 1)

        self.tabs_control.addTab(self.tab_extract, "")
        self.tab_modding = QWidget()
        self.tab_modding.setObjectName(u"tab_modding")
        self.gridLayout_3 = QGridLayout(self.tab_modding)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.chkbx_export_contents_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_contents_mods.setObjectName(u"chkbx_export_contents_mods")

        self.gridLayout_3.addWidget(self.chkbx_export_contents_mods, 2, 0, 1, 1)

        self.verticalSpacer_3 = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer_3, 3, 0, 1, 1)

        self.bt_mod_build = QPushButton(self.tab_modding)
        self.bt_mod_build.setObjectName(u"bt_mod_build")

        self.gridLayout_3.addWidget(self.bt_mod_build, 1, 1, 1, 1)

        self.chkbx_export_raw_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_raw_mods.setObjectName(u"chkbx_export_raw_mods")

        self.gridLayout_3.addWidget(self.chkbx_export_raw_mods, 0, 0, 1, 1)

        self.bt_mod_prep = QPushButton(self.tab_modding)
        self.bt_mod_prep.setObjectName(u"bt_mod_prep")

        self.gridLayout_3.addWidget(self.bt_mod_prep, 0, 1, 1, 1)

        self.chkbx_export_processed_mods = QCheckBox(self.tab_modding)
        self.chkbx_export_processed_mods.setObjectName(u"chkbx_export_processed_mods")

        self.gridLayout_3.addWidget(self.chkbx_export_processed_mods, 1, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_2, 0, 2, 1, 1)

        self.tabs_control.addTab(self.tab_modding, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_2 = QGridLayout(self.tab_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.chkbx_export_save_to_one_dir = QCheckBox(self.tab_2)
        self.chkbx_export_save_to_one_dir.setObjectName(u"chkbx_export_save_to_one_dir")

        self.gridLayout_2.addWidget(self.chkbx_export_save_to_one_dir, 0, 0, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_2, 1, 0, 1, 1)

        self.bt_extract_gltf_3d = QPushButton(self.tab_2)
        self.bt_extract_gltf_3d.setObjectName(u"bt_extract_gltf_3d")

        self.gridLayout_2.addWidget(self.bt_extract_gltf_3d, 0, 1, 1, 1)

        self.horizontalSpacer_3 = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_3, 0, 2, 1, 1)

        self.tabs_control.addTab(self.tab_2, "")

        self.verticalLayout.addWidget(self.tabs_control)

        self.verticalLayout.setStretch(0, 1)
        self.splitter.addWidget(self.widget)
        self.data_view = DataViewWidget(self.splitter)
        self.data_view.setObjectName(u"data_view")
        self.splitter.addWidget(self.data_view)

        self.verticalLayout_2.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 617, 22))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        self.menu_Edit = QMenu(self.menubar)
        self.menu_Edit.setObjectName(u"menu_Edit")
        self.menu_Tools = QMenu(self.menubar)
        self.menu_Tools.setObjectName(u"menu_Tools")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menu_Edit.menuAction())
        self.menubar.addAction(self.menu_Tools.menuAction())
        self.menu_File.addAction(self.action_project_new)
        self.menu_File.addAction(self.action_project_open)
        self.menu_File.addAction(self.action_external_add)
        self.menu_File.addAction(self.action_exit)
        self.menu_Tools.addAction(self.action_make_web_map)

        self.retranslateUi(MainWindow)

        self.tabs_nodes.setCurrentIndex(0)
        self.tabs_control.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.action_project_new.setText(QCoreApplication.translate("MainWindow", u"&New Project...", None))
        self.action_project_open.setText(QCoreApplication.translate("MainWindow", u"&Open Project...", None))
        self.action_external_add.setText(QCoreApplication.translate("MainWindow", u"&Add External...", None))
        self.action_exit.setText(QCoreApplication.translate("MainWindow", u"E&xit", None))
#if QT_CONFIG(shortcut)
        self.action_exit.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.action_make_web_map.setText(QCoreApplication.translate("MainWindow", u"Make &Web Map...", None))
        self.tabs_nodes.setTabText(self.tabs_nodes.indexOf(self.tab_directory), QCoreApplication.translate("MainWindow", u"Directory", None))
        self.tabs_nodes.setTabText(self.tabs_nodes.indexOf(self.tab_non_mapped_list), QCoreApplication.translate("MainWindow", u"Non-Mapped List", None))
        self.tabs_nodes.setTabText(self.tabs_nodes.indexOf(self.tab_raw_list), QCoreApplication.translate("MainWindow", u"Raw List", None))
        self.filter_label.setText(QCoreApplication.translate("MainWindow", u"Filter (Python Expression Syntax)", None))
        self.filter_edit.setText(QCoreApplication.translate("MainWindow", u".*", None))
        self.vhash_to_vpath_label.setText(QCoreApplication.translate("MainWindow", u"VHash -> VPath", None))
        self.vhash_to_vpath_in_edit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.chkbx_export_text_extract.setText(QCoreApplication.translate("MainWindow", u"Export As Text", None))
        self.chkbx_export_contents_extract.setText(QCoreApplication.translate("MainWindow", u"Export Contents", None))
        self.bt_extract.setText(QCoreApplication.translate("MainWindow", u"EXTRACT", None))
        self.chkbx_export_raw_extract.setText(QCoreApplication.translate("MainWindow", u"Export Raw Files", None))
        self.chkbx_export_processed_extract.setText(QCoreApplication.translate("MainWindow", u"Export As Processed", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_extract), QCoreApplication.translate("MainWindow", u"Extract", None))
        self.chkbx_export_contents_mods.setText(QCoreApplication.translate("MainWindow", u"Export Contents", None))
        self.bt_mod_build.setText(QCoreApplication.translate("MainWindow", u"Build Modded Files", None))
        self.chkbx_export_raw_mods.setText(QCoreApplication.translate("MainWindow", u"Export Raw Files", None))
        self.bt_mod_prep.setText(QCoreApplication.translate("MainWindow", u"Extract For Modding", None))
        self.chkbx_export_processed_mods.setText(QCoreApplication.translate("MainWindow", u"Export As Processed", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_modding), QCoreApplication.translate("MainWindow", u"Modding", None))
        self.chkbx_export_save_to_one_dir.setText(QCoreApplication.translate("MainWindow", u"Save To One Directory", None))
        self.bt_extract_gltf_3d.setText(QCoreApplication.translate("MainWindow", u"EXPORT 3D/GLTF2", None))
        self.tabs_control.setTabText(self.tabs_control.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"3d/GLTF2", None))
        self.menu_File.setTitle(QCoreApplication.translate("MainWindow", u"&File", None))
        self.menu_Edit.setTitle(QCoreApplication.translate("MainWindow", u"&Edit", None))
        self.menu_Tools.setTitle(QCoreApplication.translate("MainWindow", u"&Tools", None))
    # retranslateUi

