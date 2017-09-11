from PyQt4.QtCore import Qt
from PyQt4.QtGui import *

class SegmentTab(QWidget):
    '''Segment tab holds parameter inputs for segmentation.'''

    def __init__(self, parent=None):
        super(SegmentTab, self).__init__(parent)

class InfoTab(QLabel):
    '''Info tab holds miscellaneous information.'''

    def __init__(self, parent=None):
        super(InfoTab, self).__init__(parent)

        self.setAlignment(Qt.AlignTop)
        self.setText('<strong>Properties</strong>')
