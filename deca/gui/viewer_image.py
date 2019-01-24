from .viewer import *
from ..ff_avtx import Ddsc
import os
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QSizePolicy, QVBoxLayout, QComboBox
from deca.ff_types import *
from deca.file import ArchiveFile

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
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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
            npimp = self.ddsc.mips[v].data
            if npimp is not None:
                if npimp.shape[2] == 3:
                    frmt = QtGui.QImage.Format_RGB888
                elif npimp.shape[2] == 4:
                    frmt = QtGui.QImage.Format_RGBA8888
                else:
                    raise Exception('Unhandled byte counts for image')
                qimg = QtGui.QImage(npimp.data, npimp.shape[1], npimp.shape[0], npimp.shape[1] * npimp.shape[2], frmt)
                pixmap = QtGui.QPixmap.fromImage(qimg)
                self.image_display.setPhoto(pixmap)

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        self.ddsc = None
        self.select_dropdown.clear()

        if vnode.ftype == FTYPE_BMP:
            f_ddsc = vfs.file_obj_from(vnode)
            ddsc = Ddsc()
            ddsc.load_bmp(f_ddsc)
            self.ddsc = ddsc
        elif vnode.ftype == FTYPE_DDS:
            f_ddsc = vfs.file_obj_from(vnode)
            ddsc = Ddsc()
            ddsc.load_dds(f_ddsc)
            self.ddsc = ddsc
        elif vnode.ftype in {FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
            if vnode.vpath is None:
                f_ddsc = vfs.file_obj_from(vnode)
                ddsc = Ddsc()
                ddsc.load_ddsc(f_ddsc)
                self.ddsc = ddsc
            else:
                filename = os.path.splitext(vnode.vpath)
                if len(filename[1]) == 0 and vnode.ftype == FTYPE_AVTX:
                    filename_ddsc = vnode.vpath
                else:
                    filename_ddsc = filename[0] + b'.ddsc'

                if filename_ddsc in vfs.map_vpath_to_vfsnodes:
                    extras = [b'.hmddsc']
                    for i in range(1, 16):
                        extras.append('.atx{}'.format(i).encode('ascii'))
                    f_ddsc = vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_ddsc][0])
                    f_atxs = []
                    for extra in extras:
                        filename_atx = filename[0] + extra
                        if filename_atx in vfs.map_vpath_to_vfsnodes:
                            f_atxs.append(vfs.file_obj_from(vfs.map_vpath_to_vfsnodes[filename_atx][0]))
                    ddsc = Ddsc()
                    ddsc.load_ddsc(f_ddsc)
                    for atx in f_atxs:
                        ddsc.load_atx(atx)
                    self.ddsc = ddsc

        if self.ddsc is not None and self.ddsc.mips is not None:
            first_valid = None
            for i in range(len(self.ddsc.mips)):
                mip = self.ddsc.mips[i]
                if first_valid is None and mip.data is not None:
                    first_valid = i
                depth_info = ''
                if mip.depth_idx is not None and mip.depth_cnt is not None:
                    depth_info = 'd:{}/{} '.format(mip.depth_idx, mip.depth_cnt)
                self.select_dropdown.addItem('{}x{} {}({})'.format(mip.size_y, mip.size_x, depth_info, mip.itype))

            self.select_dropdown.setCurrentIndex(first_valid)
