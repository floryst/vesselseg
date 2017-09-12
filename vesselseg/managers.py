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

    def __init__(self, window, parent=None):
        super(ViewManager, self).__init__(parent)

        self.window = window

        self.window.fileSelected.connect(self.fileSelected)

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
