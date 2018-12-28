import os
from deca_gui_viewer import *
from deca.ff_avtx import Ddsc
from deca.file import ArchiveFile
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QSizePolicy, QVBoxLayout, QComboBox

# Initial version from
# https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview/35514531#35514531


class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(QtCore.QPoint(event.pos()))
        super(PhotoViewer, self).mousePressEvent(event)


class Window(QtWidgets.QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.viewer = PhotoViewer(self)
        # 'Load image' button
        self.btnLoad = QtWidgets.QToolButton(self)
        self.btnLoad.setText('Load image')
        self.btnLoad.clicked.connect(self.loadImage)
        # Button to change from drag/pan to getting pixel info
        self.btnPixInfo = QtWidgets.QToolButton(self)
        self.btnPixInfo.setText('Enter pixel info mode')
        self.btnPixInfo.clicked.connect(self.pixInfo)
        self.editPixInfo = QtWidgets.QLineEdit(self)
        self.editPixInfo.setReadOnly(True)
        self.viewer.photoClicked.connect(self.photoClicked)
        # Arrange layout
        VBlayout = QtWidgets.QVBoxLayout(self)
        VBlayout.addWidget(self.viewer)
        HBlayout = QtWidgets.QHBoxLayout()
        HBlayout.setAlignment(QtCore.Qt.AlignLeft)
        HBlayout.addWidget(self.btnLoad)
        HBlayout.addWidget(self.btnPixInfo)
        HBlayout.addWidget(self.editPixInfo)
        VBlayout.addLayout(HBlayout)

    def loadImage(self):
        self.viewer.setPhoto(QtGui.QPixmap('image.jpg'))

    def pixInfo(self):
        self.viewer.toggleDragMode()

    def photoClicked(self, pos):
        if self.viewer.dragMode() == QtWidgets.QGraphicsView.NoDrag:
            self.editPixInfo.setText('%d, %d' % (pos.x(), pos.y()))


class DataViewerImage(DataViewer):
    def __init__(self):
        DataViewer.__init__(self)

        self.ddsc = None

        self.select_dropdown = QComboBox()
        self.select_dropdown.setEditable(False)
        self.select_dropdown.currentIndexChanged.connect(self.select_dropdown_current_index_changed)
        self.select_dropdown.addItem('A')
        self.select_dropdown.addItem('B')
        self.select_dropdown.addItem('C')
        size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.select_dropdown.setSizePolicy(size)

        self.image_display = PhotoViewer(self)
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.image_display.setSizePolicy(size)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.image_display)
        self.main_layout.addWidget(self.select_dropdown)
        self.setLayout(self.main_layout)

    def select_dropdown_current_index_changed(self, v):
        if self.ddsc is not None and 0 <= v < len(self.ddsc.mips):
            mip = self.ddsc.mips[v][3]
            if mip is not None:
                qimg = QtGui.QImage(mip.data, mip.shape[1], mip.shape[0], QtGui.QImage.Format_RGBA8888)
                pixmap = QtGui.QPixmap.fromImage(qimg)
                self.image_display.setPhoto(pixmap)

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        self.ddsc = None
        self.select_dropdown.clear()

        if vnode.v_path is None:
            f_ddsc = vfs.file_obj_from(vnode)
            ddsc = Ddsc()
            ddsc.load_ddsc(f_ddsc)

            self.ddsc = ddsc
            for mip in self.ddsc.mips:
                self.select_dropdown.addItem('{}x{} ({})'.format(mip[0], mip[1], mip[2]))
        else:
            filename = os.path.splitext(vnode.v_path)
            filename_ddsc = filename[0] + b'.ddsc'

            if filename_ddsc in vfs.map_vpath_to_vfsnodes:
                f_ddsc = vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_ddsc][0])
                f_atxs = []
                for i in range(1, 16):
                    filename_atx = filename[0] + '.atx{}'.format(i).encode('ascii')
                    if filename_atx in vfs.map_vpath_to_vfsnodes:
                        f_atxs.append(vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_atx][0]))
                    else:
                        break

                ddsc = Ddsc()
                ddsc.load_ddsc(f_ddsc)
                for atx in f_atxs:
                    ddsc.load_atx(atx)

                self.ddsc = ddsc

                for mip in self.ddsc.mips:
                    self.select_dropdown.addItem('{}x{} ({})'.format(mip[0], mip[1], mip[2]))
