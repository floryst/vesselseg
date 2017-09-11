from PyQt4.QtCore import *
from PyQt4.QtGui import *

import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class VTKViewer(QWidget):
    '''Renders the VTK slice and controls.'''

    def __init__(self, parent=None):
        super(VTKViewer, self).__init__(parent)

        self.wrapper = QHBoxLayout(self)

        self.frame = QFrame(self)
        self.wrapper.addWidget(self.frame)

        self.hbox = QHBoxLayout(self.frame)

        self.sliceView = QVTKRenderWindowInteractor(self.frame)
        self.hbox.addWidget(self.sliceView)

        self.sliderBox = QVBoxLayout(self)
        self.sliderBox.setAlignment(Qt.AlignHCenter)
        self.hbox.addLayout(self.sliderBox)

        self.sliceSlider = QSlider(Qt.Vertical, self)
        self.sliderBox.addWidget(self.sliceSlider)

        self.sliceLabel = QLabel('-', self)
        self.sliceLabel.setAlignment(Qt.AlignHCenter)
        self.sliderBox.addWidget(self.sliceLabel)

        self.volumeView = QVTKRenderWindowInteractor(self.frame)
        self.hbox.addWidget(self.volumeView)

        self.setLayout(self.wrapper)

    def initRenderers(self):
        self.sliceRenderer = vtk.vtkRenderer()
        self.sliceView.GetRenderWindow().AddRenderer(self.sliceRenderer)

        self.volumeRenderer = vtk.vtkRenderer()
        self.volumeView.GetRenderWindow().AddRenderer(self.volumeRenderer)

        irenSlice = self.sliceRenderer.GetRenderWindow().GetInteractor()
        irenVolume = self.volumeRenderer.GetRenderWindow().GetInteractor()

        irenSlice.Initialize()
        irenVolume.Initialize()
        irenSlice.Start()
        irenVolume.Start()
