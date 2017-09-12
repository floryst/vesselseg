from PyQt4.QtCore import QObject, pyqtSignal

import vtk

class ImageManager(QObject):
    '''Manager for the loaded image.'''

    # signal: image file read and opened
    imageLoaded = pyqtSignal(vtk.vtkImageData)

    def __init__(self, parent=None):
        super(ImageManager, self).__init__(parent)

        self.imageData = None

    def loadImage(self, filename):
        '''Tries to load a given file.

        Returns:
            Boolean if file was loaded successfully.
        '''
        reader = vtk.vtkImageReader2Factory.CreateImageReader2(filename)
        if reader is None:
            return False

        reader.SetFileName(filename)
        reader.Update()
        self.imageData = reader.GetOutput()

        self.imageLoaded.emit(self.imageData)
        return True

class ViewManager(QObject):
    '''Manager of the UI.'''

    # signal: file was selected for loading
    fileSelected = pyqtSignal(str)
    # signal: scale input changed
    scaleChanged = pyqtSignal(float)

    def __init__(self, window, parent=None):
        super(ViewManager, self).__init__(parent)

        self.window = window

        self.window.fileSelected.connect(self.fileSelected)
        self.window.segmentTabView().scaleChanged.connect(self.scaleChanged)

    def displayImage(self, vtkImage):
        '''Displays a VTK ImageData to the UI.'''
        self.window.vtkView().displayImage(vtkImage)
        self.window.infoTabView().showImageMetadata(vtkImage)

    def alert(self, message):
        '''Alerts the user with some message.'''
        self.window.popupMessage(message)

    def setSegmentScale(self, scale):
        '''Updates view with scale.'''
        self.window.segmentTabView().setScale(scale)

class SegmentManager(QObject):
    '''Manager of tube segmentation.'''

    DEFAULT_SCALE = 2.0

    def __init__(self, parent=None):
        super(SegmentManager, self).__init__(parent)

        self._scale = self.DEFAULT_SCALE

    def scale(self):
        '''Getter for scale.'''
        return self._scale

    def setScale(self, scale):
        '''Setter for scale.

        If scale is less than 0, then set to default.
        '''
        if scale <= 0.0:
            scale = self.DEFAULT_SCALE
        self._scale = scale
