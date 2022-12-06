from PySide2.QtGui import QColor


def used_color_calc(level):
    return QColor(0x00, max(0x10, 0xff - 0x20 * level), 0x00, 0xff)







