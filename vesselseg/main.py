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

        self.viewManager.fileSelected.connect(self.loadFile)
        self.viewManager.imageVoxelSelected.connect(self.segmentTube)
        self.viewManager.scaleChanged.connect(self.segmentManager.setScale)
        self.viewManager.tubeSelected.connect(self.tubeManager.toggleSelection)
        self.viewManager.wantTubeSelectionDeleted.connect(
                self.tubeManager.deleteSelection)
        self.imageManager.imageLoaded.connect(self.viewManager.displayImage)
        self.imageManager.imageLoaded.connect(self.setSegmentImage)
        self.imageManager.imageLoaded.connect(
                lambda _: self.tubeManager.reset())
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

    def loadFile(self, qfilename):
        filename = qfilename.toLatin1().data()
        if self.imageManager.loadImage(filename):
            return
        elif self.tubeManager.loadTubes(filename):
            return
        else:
            self.viewManager.alert('File %s could not opened' % filename)

    def setSegmentImage(self, vtkImageData):
        '''Sets the segment image and displays a progress modal.'''
        self.viewManager.showProgress('Prepping image for segmentation...')
        self.segmentManager.setImage(vtkImageData)
        self.viewManager.closeProgress()

    def segmentTube(self, x, y, z):
        if self.viewManager.isSegmentEnabled():
            self.segmentManager.segmentTube(x, y, z)

if __name__ == '__main__':
    app = VesselSegApp()
    sys.exit(app.run())
