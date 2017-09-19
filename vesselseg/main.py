import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QObject
from mainwindow import MainWindow
from managers import ImageManager, ViewManager, SegmentManager, TubeManager

class VesselSegApp(QObject):

    def __init__(self, parent=None):
        super(VesselSegApp, self).__init__(parent)

        self.qapp = QApplication(sys.argv)
        self.window = MainWindow()
        self.imageManager = ImageManager()
        self.tubeManager = TubeManager()
        self.viewManager = ViewManager(self.window)
        self.segmentManager = SegmentManager()

        self.viewManager.setSegmentScale(self.segmentManager.scale())

        self.window.closed.connect(self.teardown)
        self.viewManager.fileSelected.connect(self.loadFile)
        self.viewManager.imageVoxelSelected.connect(self.segmentTube)
        self.viewManager.scaleChanged.connect(self.segmentManager.setScale)
        self.viewManager.tubeSelected.connect(self.tubeManager.toggleSelection)
        self.viewManager.wantTubeSelectionDeleted.connect(
                self.tubeManager.deleteSelection)
        self.viewManager.wantTubeSelectionCleared.connect(
                self.tubeManager.clearSelection)
        self.imageManager.imageLoaded.connect(self.viewManager.displayImage)
        self.imageManager.imageLoaded.connect(self.setSegmentImage)
        self.imageManager.imageLoaded.connect(self.resetTubeManager)
        self.segmentManager.tubeSegmented.connect(
                self.tubeManager.addSegmentedTube)
        self.segmentManager.jobCountChanged.connect(
                self.viewManager.showJobCount)
        self.tubeManager.tubesUpdated.connect(self.viewManager.displayTubes)
        self.tubeManager.tubeSelectionChanged.connect(
                self.viewManager.showTubeSelection)

    def run(self):
        '''Runs the application.

        Returns:
            An integer representing the termination state.
        '''
        self.window.show()
        return self.qapp.exec_()

    def teardown(self):
        '''Tear down application.'''
        self.segmentManager.stop()

    def loadFile(self, qfilename):
        progress = self.viewManager.makeProgressDialog('Loading image...')
        filename = qfilename.toLatin1().data()
        if self.imageManager.loadImage(filename):
            pass
        elif self.tubeManager.loadTubes(filename):
            pass
        else:
            self.viewManager.alert('File %s could not opened' % filename)
        progress.close()

    def setSegmentImage(self, vtkImageData):
        '''Sets the segment image and displays a progress modal.'''
        progress = self.viewManager.makeProgressDialog(
                'Prepping image for segmentation...')
        self.segmentManager.setImage(vtkImageData)
        progress.close()

    def segmentTube(self, x, y, z):
        if self.viewManager.isSegmentEnabled():
            self.segmentManager.segmentTube(x, y, z)

    def resetTubeManager(self, _):
        '''Resets tube manager.'''
        self.tubeManager.reset()

if __name__ == '__main__':
    app = VesselSegApp()
    sys.exit(app.run())
