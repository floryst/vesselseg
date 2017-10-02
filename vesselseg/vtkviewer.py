from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from managers import TUBE_ID_KEY

class SliceSlider(QWidget):
    '''Represents the slice control widget.'''

    # signal: slice position changed
    slicePosChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(SliceSlider, self).__init__(parent)

        self.vbox = QVBoxLayout(self)

        self.sliceSlider = QSlider(Qt.Vertical, self)
        self.sliceSlider.setTickInterval(1)
        self.sliceSlider.setRange(0, 0)
        self.vbox.addWidget(self.sliceSlider)

        self.sliceLabel = QLabel('-', self)
        self.sliceLabel.setAlignment(Qt.AlignHCenter)
        self.vbox.addWidget(self.sliceLabel)

        self.sliceSlider.valueChanged.connect(self.updateSlicePosition)

    def updateSlicePosition(self, pos):
        '''Notifies of current slice position.'''
        self.setSliceLabel(pos)
        self.slicePosChanged.emit(pos)

    def setPosition(self, pos):
        '''Sets the current position.'''
        self.sliceSlider.setValue(pos)
        self.setSliceLabel(pos)

    def setRange(self, vmin, vmax):
        '''Sets range of slider.'''
        self.sliceSlider.setRange(vmin, vmax)

    def setSliceLabel(self, pos):
        '''Sets slice label.'''
        self.sliceLabel.setText(str(pos))

class VTKViewer(QWidget):
    '''Renders the VTK slice and controls.'''

    # signal: image voxel selected at given coord
    imageVoxelSelected = pyqtSignal(float, float, float)
    # signal: a tube was selected
    tubeSelected = pyqtSignal(str)
    # signal: window/level changed. Values are between [0,1]
    windowLevelChanged = pyqtSignal(float, float)

    class ClickInteractorStyleImage(vtk.vtkInteractorStyleImage):
        '''Listens for click events and invokes LeftButtonClickEvent.'''

        def __init__(self):
            self.clickX, self.clickY = (0, 0)

            self.AddObserver('LeftButtonPressEvent', self.onLeftButtonDown)
            self.AddObserver('LeftButtonReleaseEvent', self.onLeftButtonUp)

        def onLeftButtonDown(self, istyle, event):
            self.clickX, self.clickY = istyle.GetInteractor().GetEventPosition()
            self.OnLeftButtonDown()

        def onLeftButtonUp(self, istyle, event):
            evX, evY = istyle.GetInteractor().GetEventPosition()
            vec = QPoint(evX-self.clickX, evY-self.clickY)
            if vec.manhattanLength() < 3:
                self.InvokeEvent('LeftButtonClickEvent')
            self.OnLeftButtonUp()

    class ClickInteractorStyleTrackball(vtk.vtkInteractorStyleTrackballCamera):
        '''Listens for click events and invokes LeftButtonClickEvent.'''

        def __init__(self):
            self.clickX, self.clickY = (0, 0)

            self.AddObserver('LeftButtonPressEvent', self.onLeftButtonDown)
            self.AddObserver('LeftButtonReleaseEvent', self.onLeftButtonUp)

        def onLeftButtonDown(self, istyle, event):
            self.clickX, self.clickY = istyle.GetInteractor().GetEventPosition()
            self.OnLeftButtonDown()

        def onLeftButtonUp(self, istyle, event):
            evX, evY = istyle.GetInteractor().GetEventPosition()
            vec = QPoint(evX-self.clickX, evY-self.clickY)
            if vec.manhattanLength() < 3:
                self.InvokeEvent('LeftButtonClickEvent')
            self.OnLeftButtonUp()

    def __init__(self, parent=None):
        super(VTKViewer, self).__init__(parent)

        self.slicePosition = 0
        self.tubeBlocks = None

        self.hbox = QHBoxLayout(self)

        self.sliceView = QVTKRenderWindowInteractor(self)
        self.hbox.addWidget(self.sliceView)

        self.sliceSlider = SliceSlider(self)
        self.hbox.addWidget(self.sliceSlider)

        self.volumeView = QVTKRenderWindowInteractor(self)
        self.hbox.addWidget(self.volumeView)

        self.sliceSlider.slicePosChanged.connect(self.updateSlice)

        # vtk-producers and filters
        self.producer = vtk.vtkTrivialProducer()
        self.reslice = vtk.vtkImageReslice()
        self.image2worldTransform = vtk.vtkTransform()
        self.tubeProducer = vtk.vtkTrivialProducer()
        self.tubeMapper = vtk.vtkCompositePolyDataMapper2()
        self.tubeActor = vtk.vtkActor()

    def initRenderers(self):
        self.sliceRenderer = vtk.vtkRenderer()
        self.sliceView.GetRenderWindow().AddRenderer(self.sliceRenderer)

        self.volumeRenderer = vtk.vtkRenderer()
        self.volumeView.GetRenderWindow().AddRenderer(self.volumeRenderer)

        irenSlice = self.sliceRenderer.GetRenderWindow().GetInteractor()
        irenVolume = self.volumeRenderer.GetRenderWindow().GetInteractor()

        # set volume picker, since we need to have a pick list
        volumePicker = vtk.vtkCellPicker()
        volumePicker.SetPickFromList(True)
        irenVolume.SetPicker(volumePicker)

        istyleSlice = self.ClickInteractorStyleImage()
        irenSlice.SetInteractorStyle(istyleSlice)

        istyleVolume = self.ClickInteractorStyleTrackball()
        irenVolume.SetInteractorStyle(istyleVolume)

        irenSlice.Initialize()
        irenVolume.Initialize()
        irenSlice.Start()
        irenVolume.Start()

        istyleSlice.AddObserver('LeftButtonClickEvent', self.onSliceClicked)
        # window level is changed after mouse is released
        istyleSlice.AddObserver('LeftButtonReleaseEvent',
                self.onWindowLevelChange)
        istyleVolume.AddObserver('LeftButtonClickEvent', self.onVolumeClicked)

        # set up tube actor
        self.tubeMapper.SetInputConnection(self.tubeProducer.GetOutputPort())
        cdsa = vtk.vtkCompositeDataDisplayAttributes()
        cdsa.SetBlockColor(0, (1,0,0))
        self.tubeMapper.SetCompositeDataDisplayAttributes(cdsa)
        self.tubeActor.SetMapper(self.tubeMapper)

        picker = self.volumeRenderer.GetRenderWindow().GetInteractor() \
                .GetPicker()
        picker.AddPickList(self.tubeActor)

    def onSliceClicked(self, istyle, event):
        '''Slice click callback'''
        clickX, clickY = istyle.GetInteractor().GetEventPosition()
        picker = vtk.vtkCellPicker()
        if picker.Pick(clickX, clickY, 0, self.sliceRenderer):
            point = picker.GetPickedPositions().GetPoint(0)
            # set z coord to be current slice location
            self.imageVoxelSelected.emit(point[0], point[1], self.slicePosition)

    def onVolumeClicked(self, istyle, event):
        '''Volume click callback'''
        clickX, clickY = istyle.GetInteractor().GetEventPosition()
        picker = istyle.GetInteractor().GetPicker()
        if picker.Pick(clickX, clickY, 0, self.volumeRenderer):
            self.pickTubeBlock(picker.GetFlatBlockIndex())

    def onWindowLevelChange(self, istyle, event):
        '''Callback when the VTK image window level changes.'''
        imageProp = istyle.GetCurrentImageProperty()
        if imageProp:
            # TODO handle case when user pressing "R/r" resets the window/level
            window, level = imageProp.GetColorWindow(), imageProp.GetColorLevel()
            window = min(1.0, max(0.0, window/255.0))
            level = min(1.0, max(0.0, level/255.0))
            self.windowLevelChanged.emit(window, level)

    def pickTubeBlock(self, blockIndex):
        '''Picks out the clicked tube.'''
        if self.tubeBlocks:
            it = self.tubeBlocks.NewTreeIterator()
            it.SetVisitOnlyLeaves(False)
            it.InitTraversal()
            while not it.IsDoneWithTraversal():
                if blockIndex == it.GetCurrentFlatIndex():
                    tubeId = it.GetCurrentMetaData().Get(TUBE_ID_KEY)
                    self.tubeSelected.emit(tubeId)
                    break
                it.GoToNextItem()

    def displayImage(self, vtkImageData):
        '''Updates viewer with a new image.'''
        # show slice and volume
        self.showSlice(vtkImageData)
        self.showVolume(vtkImageData)

        # compute transformation
        self.image2worldTransform.Identity()
        self.image2worldTransform.PreMultiply()
        self.image2worldTransform.Translate(vtkImageData.GetOrigin())
        self.image2worldTransform.Scale(vtkImageData.GetSpacing())

        # set z slice
        _, _, _, _, zmin, zmax = vtkImageData.GetExtent()
        slicePos = int((zmax+zmin)/2.0)
        self.sliceSlider.setRange(zmin, zmax)
        self.sliceSlider.setPosition(slicePos)
        self.updateSlice(slicePos)

    def showSlice(self, vtkImageData):
        '''Shows slice of image.'''
        self.producer.SetOutput(vtkImageData)
        self.reslice.SetInputConnection(self.producer.GetOutputPort())
        self.reslice.SetResliceAxesDirectionCosines((1,0,0), (0,1,0), (0,0,1))
        self.reslice.SetOutputDimensionality(2)
        self.reslice.SetInterpolationModeToLinear()

        # create lookup table for intensity -> color
        table = vtk.vtkLookupTable()
        table.SetRange(vtkImageData.GetScalarRange())
        table.SetValueRange(0, 1)
        # no saturation
        table.SetSaturationRange(0, 0)
        table.SetRampToLinear()
        table.Build()

        # map lookup table to colors
        colors = vtk.vtkImageMapToColors()
        colors.SetLookupTable(table)
        colors.SetInputConnection(self.reslice.GetOutputPort())

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(colors.GetOutputPort())

        self.sliceRenderer.RemoveAllViewProps()
        self.sliceRenderer.AddActor(actor)

        self.sliceRenderer.ResetCamera()
        # Don't actually render slice, since setting the slice position will
        # force render. If we render here, there will be a flicker of the slice.

    def showVolume(self, vtkImageData):
        '''Shows volume of image.'''
        mapper = vtk.vtkSmartVolumeMapper()
        mapper.SetInputData(vtkImageData)

        scalarRange = vtkImageData.GetScalarRange()

        opacity = vtk.vtkPiecewiseFunction()
        opacity.AddPoint(scalarRange[0], 0.2)
        opacity.AddPoint(scalarRange[1], 0.9)

        color = vtk.vtkColorTransferFunction()
        color.AddRGBPoint(scalarRange[0], 0, 0, 0)
        color.AddRGBPoint(scalarRange[1], 1, 1, 1)

        prop = vtk.vtkVolumeProperty()
        prop.ShadeOff()
        prop.SetInterpolationType(vtk.VTK_LINEAR_INTERPOLATION)
        prop.SetColor(color)
        prop.SetScalarOpacity(opacity)
        # sets scalar opacity unit distance according to image spacing.
        avgSpacing = sum(vtkImageData.GetSpacing()) / 3.0
        prop.SetScalarOpacityUnitDistance(15 * avgSpacing)

        volume = vtk.vtkVolume()
        volume.SetMapper(mapper)
        volume.SetProperty(prop)

        self.volumeRenderer.RemoveAllViewProps()
        self.volumeRenderer.AddViewProp(volume)

        self.volumeRenderer.ResetCamera()
        self.volumeView.GetRenderWindow().Render()

    def showTubeBlocks(self, tubeBlocks):
        '''Shows tube blocks in scene.'''
        self.tubeBlocks = tubeBlocks

        # make sure tube actor is in the scene
        if not self.volumeRenderer.HasViewProp(self.tubeActor):
            self.volumeRenderer.AddActor(self.tubeActor)

        self.tubeProducer.SetOutput(tubeBlocks)
        self.tubeProducer.Update()
        self.volumeRenderer.ResetCamera()
        self.volumeView.GetRenderWindow().Render()

    def showTubeSelection(self, tubeSelection):
        '''Shows tube selections.

        Args:
            tubeSelection: an iterable of tube block indexes.
        '''
        cdda = vtk.vtkCompositeDataDisplayAttributes()
        # default red
        cdda.SetBlockColor(0, (1,0,0))
        for index in tubeSelection:
            cdda.SetBlockColor(index, (1,1,1))
        self.tubeMapper.SetCompositeDataDisplayAttributes(cdda)
        self.volumeView.GetRenderWindow().Render()

    def updateSlice(self, pos):
        '''Re-renders the slice with a new position.'''
        # z slice
        coords = (0, 0, pos)
        transformed = self.image2worldTransform.TransformPoint(coords)
        self.slicePosition = transformed[2]

        self.reslice.SetResliceAxesOrigin(0, 0, self.slicePosition)
        self.reslice.Update()
        self.sliceView.GetRenderWindow().Render()
