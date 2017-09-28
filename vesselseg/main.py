import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from mainwindow import MainWindow
from managers import *

class VesselSegApp(QObject):

    def __init__(self, parent=None):
        super(VesselSegApp, self).__init__(parent)

        self.qapp = QApplication(sys.argv)
        self.window = MainWindow()
        self.imageManager = ImageManager()
        self.tubeManager = TubeManager()
        self.viewManager = ViewManager(self.window)
        self.segmentManager = SegmentManager()
        self.filterManager = FilterManager()

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
        self.viewManager.wantAllTubesSelected.connect(
                self.tubeManager.selectAllTubes)
        self.viewManager.windowLevelChanged.connect(
                self.filterManager.setWindowLevel)
        self.viewManager.windowLevelFilterChanged.connect(
                self.filterManager.toggleWindowLevel)
        self.viewManager.medianFilterChanged.connect(
                self.filterManager.setMedianParams)
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
        self.filterManager.windowLevelChanged.connect(
                self.segmentManager.setWindowLevel)
        self.filterManager.medianParamsChanged.connect(
                self.segmentManager.setMedianParams)

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

    def loadFile(self, filename):
        # filename is passed as a unicode type, so make it str type
        filename = str(filename)
        progress = self.viewManager.makeProgressDialog('Loading image...')
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
