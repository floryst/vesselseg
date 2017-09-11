from PyQt4.QtGui import *
from PyQt4.QtCore import Qt

from tabs import InfoTab, SegmentTab
from vtkviewer import VTKViewer

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

    def show(self):
        '''Overridden show().

        Must init VTK renderers AFTER main window is shown.
        '''
        super(MainWindow, self).show()
        self.ui.initVTK()

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

        self.vtkview = VTKViewer(self)
        self.addWidget(self.vtkview)

    def initVTK(self):
        '''Initializes the VTK renderers.'''
        self.vtkview.initRenderers()
