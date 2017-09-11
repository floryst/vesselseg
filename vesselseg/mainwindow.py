from PyQt4.QtGui import *
from PyQt4.QtCore import Qt

from tabs import InfoTab, SegmentTab

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.ui = Ui(self)
        self.setCentralWidget(self.ui)

        self.createMenus()
        self.createActions()

    def createMenus(self):
        self.fileMenu = QMenu('&File', self)
        self.menuBar().addMenu(self.fileMenu)

    def createActions(self):
        self.openAction = QAction('Open', self)
        self.fileMenu.addAction(self.openAction)

class Ui(QSplitter):
    def __init__(self, parent=None):
        super(Ui, self).__init__(Qt.Horizontal, parent)

        self.tabs = QTabWidget(self)
        self.addWidget(self.tabs)

        self.tubeTreeTab = QTreeView(self)
        self.tabs.addTab(self.tubeTreeTab, 'Tubes')

        self.segmentTab = SegmentTab(self)
        self.tabs.addTab(self.segmentTab, 'Segment')

        self.infoTab = InfoTab(self)
        self.tabs.addTab(self.infoTab, 'Info')

        self.vtkview = QWidget(self)
        self.addWidget(self.vtkview)
