from PyQt4.QtGui import *
from PyQt4.QtCore import Qt, pyqtSignal

from tabs import InfoTab, SegmentTab
from vtkviewer import VTKViewer

class MainWindow(QMainWindow):

    # signal: file was selected for loading
    fileSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.ui = Ui(self)
        self.setCentralWidget(self.ui)

        self.createMenus()
        self.createActions()

        self.openAction.triggered.connect(self.openFileDialog)

    def createMenus(self):
        self.fileMenu = QMenu('&File', self)
        self.menuBar().addMenu(self.fileMenu)

    def createActions(self):
        self.openAction = QAction('&Open', self)
        self.openAction.setShortcut('Ctrl+O')
        self.fileMenu.addAction(self.openAction)

    def openFileDialog(self):
        '''Opens a file dialog prompt.'''
        fileDialog = QFileDialog(self)
        if fileDialog.exec_():
            filename = fileDialog.selectedFiles()[0]
            self.fileSelected.emit(filename)

    def popupMessage(self, message):
        '''Brings up a modal box with message for the user.'''
        msgbox = QMessageBox()
        msgbox.setText(message)
        msgbox.exec_()

    def show(self):
        '''Overridden show().

        Must init VTK renderers AFTER main window is shown.
        '''
        super(MainWindow, self).show()
        self.ui.initVTK()

    def vtkView(self):
        '''Getter for the VTKViewer.'''
        return self.ui.vtkview

    def infoTabView(self):
        '''Getter for info tab.'''
        return self.ui.infoTab

    def segmentTabView(self):
        '''Getter for segment tab.'''
        return self.ui.segmentTab

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
