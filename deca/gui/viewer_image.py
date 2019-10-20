from .viewer import *
from ..ff_avtx import Ddsc
import deca.ff_avtx
import os
from PySide2.QtCore import Qt, QPoint, QRectF, Signal
from PySide2.QtGui import QImage, QPixmap, QBrush, QColor
from PySide2.QtWidgets import \
    QGraphicsView, QSizePolicy, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QGraphicsScene, QGraphicsPixmapItem, \
    QFrame, QWidget, QToolButton, QLineEdit, QCheckBox
from deca.ff_types import *
from deca.file import ArchiveFile

# Initial version from
# https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview/35514531#35514531


class PhotoViewer(QGraphicsView):
    photoClicked = Signal(QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 0
        self._empty = True
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setFrameShape(QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
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
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QGraphicsView.NoDrag)
            self._photo.setPixmap(QPixmap())
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
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(QPoint(event.pos()))
        super(PhotoViewer, self).mousePressEvent(event)


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.viewer = PhotoViewer(self)

        # 'Load image' button
        self.btnLoad = QToolButton(self)
        self.btnLoad.setText('Load image')
        self.btnLoad.clicked.connect(self.loadImage)

        # Button to change from drag/pan to getting pixel info
        self.btnPixInfo = QToolButton(self)
        self.btnPixInfo.setText('Enter pixel info mode')
        self.btnPixInfo.clicked.connect(self.pixInfo)
        self.editPixInfo = QLineEdit(self)
        self.editPixInfo.setReadOnly(True)
        self.viewer.photoClicked.connect(self.photoClicked)

        # Arrange layout
        VBlayout = QVBoxLayout(self)
        VBlayout.addWidget(self.viewer)
        HBlayout = QHBoxLayout()
        HBlayout.setAlignment(Qt.AlignLeft)
        HBlayout.addWidget(self.btnLoad)
        HBlayout.addWidget(self.btnPixInfo)
        HBlayout.addWidget(self.editPixInfo)
        VBlayout.addLayout(HBlayout)

    def loadImage(self):
        self.viewer.setPhoto(QPixmap('image.jpg'))

    def pixInfo(self):
        self.viewer.toggleDragMode()

    def photoClicked(self, pos):
        if self.viewer.dragMode() == QGraphicsView.NoDrag:
            self.editPixInfo.setText('%d, %d' % (pos.x(), pos.y()))


class DataViewerImage(DataViewer):
    def __init__(self):
        DataViewer.__init__(self)

        self.ddsc = None

        self.image_display = PhotoViewer(self)
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.image_display.setSizePolicy(size)

        self.select_dropdown = QComboBox()
        self.select_dropdown.setEditable(False)
        self.select_dropdown.addItem('A')
        self.select_dropdown.addItem('B')
        self.select_dropdown.addItem('C')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.select_dropdown.setSizePolicy(size)
        self.select_dropdown.currentIndexChanged.connect(self.select_dropdown_current_index_changed)

        self.checkbox_opaque = QCheckBox(self)
        self.checkbox_opaque.setText('Opaque')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.checkbox_opaque.setSizePolicy(size)
        self.checkbox_opaque.setChecked(True)
        self.checkbox_opaque.clicked.connect(self.color_control_clicked)

        self.checkbox_show_r = QCheckBox(self)
        self.checkbox_show_r.setText('Red')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.checkbox_show_r.setSizePolicy(size)
        self.checkbox_show_r.setChecked(True)
        self.checkbox_show_r.clicked.connect(self.color_control_clicked)

        self.checkbox_show_g = QCheckBox(self)
        self.checkbox_show_g.setText('Green')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.checkbox_show_g.setSizePolicy(size)
        self.checkbox_show_g.setChecked(True)
        self.checkbox_show_g.clicked.connect(self.color_control_clicked)

        self.checkbox_show_b = QCheckBox(self)
        self.checkbox_show_b.setText('Blue')
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.checkbox_show_b.setSizePolicy(size)
        self.checkbox_show_b.setChecked(True)
        self.checkbox_show_b.clicked.connect(self.color_control_clicked)

        self.color_layout = QHBoxLayout()
        self.color_layout.addWidget(self.checkbox_opaque)
        self.color_layout.addWidget(self.checkbox_show_r)
        self.color_layout.addWidget(self.checkbox_show_g)
        self.color_layout.addWidget(self.checkbox_show_b)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.image_display)
        self.main_layout.addWidget(self.select_dropdown)
        self.main_layout.addLayout(self.color_layout)
        self.setLayout(self.main_layout)

        self.update_image()

    def update_image(self):
        v = self.select_dropdown.currentIndex()
        if self.ddsc is not None and 0 <= v < len(self.ddsc.mips):
            npimp = self.ddsc.mips[v].data
            if npimp is not None:
                npimp = npimp.copy()
                if self.checkbox_opaque.isChecked() and npimp.shape[2] == 4:
                    npimp[:, :, 3] = 0xFF
                if not self.checkbox_show_r.isChecked():
                    npimp[:, :, 0] = 0
                if not self.checkbox_show_g.isChecked():
                    npimp[:, :, 1] = 0
                if not self.checkbox_show_b.isChecked():
                    npimp[:, :, 2] = 0

                if npimp.shape[2] == 3:
                    frmt = QImage.Format_RGB888
                elif npimp.shape[2] == 4:
                    frmt = QImage.Format_RGBA8888
                else:
                    raise Exception('Unhandled byte counts for image')

                qimg = QImage(npimp.data, npimp.shape[1], npimp.shape[0], npimp.shape[1] * npimp.shape[2], frmt)
                pixmap = QPixmap.fromImage(qimg)
                self.image_display.setPhoto(pixmap)

    def select_dropdown_current_index_changed(self, v):
        self.update_image()

    def color_control_clicked(self, checked):
        self.update_image()

    def vnode_process(self, vfs: VfsStructure, vnode: VfsNode):
        self.ddsc = None
        self.select_dropdown.clear()

        if vnode.ftype in {FTYPE_BMP, FTYPE_DDS, FTYPE_AVTX, FTYPE_ATX, FTYPE_HMDDSC}:
            self.ddsc = deca.ff_avtx.image_load(vfs, vnode)

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
