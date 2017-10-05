import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# set vtk renderwindow base class to QGLWidget
import vtk.qt
vtk.qt.QVTKRWIBase = 'QGLWidget'

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from mainwindow import MainWindow
from mainwindow import IMAGE_ORIGINAL, IMAGE_PREPROCESSED
from managers import *
import utils

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
        self.viewManager.disableUi()

        # main window
        self.window.closed.connect(self.teardown)

        # view manager
        self.viewManager.fileSelected.connect(self.loadFile)
        self.viewManager.imageVoxelSelected.connect(self.segmentTube)
        self.viewManager.scaleChanged.connect(self.segmentManager.setScale)
        self.viewManager.tubeSelected.connect(self.tubeManager.toggleSelection)
        self.viewManager.deleteTubeSelClicked.connect(
                self.tubeManager.deleteSelection)
        self.viewManager.clearTubeSelClicked.connect(
                self.tubeManager.clearSelection)
        self.viewManager.selectAllTubesClicked.connect(
                self.tubeManager.selectAllTubes)
        self.viewManager.windowLevelChanged.connect(
                self.filterManager.setWindowLevel)
        self.viewManager.windowLevelFilterEnabled.connect(
                self.filterManager.setWindowLevelEnabled)
        self.viewManager.medianFilterChanged.connect(
                self.filterManager.setMedianParams)
        self.viewManager.medianFilterEnabled.connect(
                self.filterManager.setMedianFilterEnabled)
        self.viewManager.viewedImageChanged.connect(
                self.changeViewedImage)
        self.viewManager.applyFiltersTriggered.connect(
                self.applyImageFilters)

        # image manager
        self.imageManager.imageLoaded.connect(self.onImageLoaded)

        # segment manager
        self.segmentManager.tubeSegmented.connect(
                self.tubeManager.addSegmentedTube)
        self.segmentManager.jobCountChanged.connect(
                self.viewManager.showJobCount)

        # tube manager
        self.tubeManager.tubesUpdated.connect(self.viewManager.displayTubes)
        self.tubeManager.tubeSelectionChanged.connect(
                self.viewManager.showTubeSelection)

        # filter manager

    def run(self):
        '''Runs the application.

        Returns:
            An integer representing the termination state.
        '''
        self.window.show()
        if len(sys.argv) == 2:
            self.loadFile(sys.argv[1])

        return self.qapp.exec_()

    def teardown(self):
        '''Tear down application.'''
        self.segmentManager.stop()

    def loadFile(self, filename):
        # filename is passed as a unicode type, so make it str type
        filename = str(filename)
        progress = self.viewManager.makeProgressDialog('Loading image...')
        if self.imageManager.loadImage(filename) or \
                self.tubeManager.loadTubes(filename):
            self.viewManager.enableUi()
        else:
            self.viewManager.alert('File %s could not opened' % filename)
        progress.close()

    def onImageLoaded(self, imageManager):
        '''Callback for when image is loaded.'''
        self.viewManager.displayImage(
                imageManager.vtkImage, imageManager.filename)
        self.segmentManager.setImage(
                imageManager.itkImage,
                imageManager.itkPixelType,
                imageManager.dimension)
        self.filterManager.setImage(
                imageManager.itkImage,
                imageManager.itkPixelType,
                imageManager.dimension)
        self.resetTubeManager()

    def changeViewedImage(self, imageType):
        img = None
        if imageType == IMAGE_ORIGINAL:
            img = self.imageManager.vtkImage
        elif imageType == IMAGE_PREPROCESSED:
            img = utils.itkToVtkImage(self.filterManager.getOutput())
        else:
            raise Exception('Invalid image type to view: %s' % imageType)
        self.viewManager.displayImage(img, self.imageManager.filename, True)

    def applyImageFilters(self):
        '''Updates filtered image'''
        self.filterManager.update()
        if self.viewManager.getViewedImageType() == IMAGE_PREPROCESSED:
            # trigger display image again
            self.changeViewedImage(IMAGE_PREPROCESSED)

    def segmentTube(self, x, y, z):
        if self.viewManager.isSegmentEnabled():
            self.segmentManager.setImage(
                    self.filterManager.getOutput(),
                    *self.filterManager.getOutputType())
            self.segmentManager.segmentTube(x, y, z)

    def resetTubeManager(self):
        '''Resets tube manager.'''
        self.tubeManager.reset()

if __name__ == '__main__':
    app = VesselSegApp()
    sys.exit(app.run())
