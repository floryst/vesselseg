import os
import math
import collections

from PyQt5.QtCore import QThread, QObject, pyqtSignal

import vtk
import itk
from vtk.util import keys

from segmenttubes import SegmentWorker, SegmentArgs, TubeIterator, GetTubePoints
from models import TubeTreeViewModel, RAW_DATA_ROLE

TUBE_ID_KEY = keys.MakeKey(keys.StringKey, 'tube.id', '')

VTK_ITK_TYPE_CONVERSION = {
    vtk.VTK_UNSIGNED_CHAR: itk.UC,
    vtk.VTK_UNSIGNED_INT: itk.UI,
    vtk.VTK_UNSIGNED_LONG: itk.UL,
    # set this as a signed short for now. The python bindings
    # don't have unsigned short :(
    vtk.VTK_UNSIGNED_SHORT: itk.SS,
    vtk.VTK_CHAR: itk.SC,
    vtk.VTK_INT: itk.SI,
    vtk.VTK_LONG: itk.SL,
    vtk.VTK_SHORT: itk.SS,
    vtk.VTK_FLOAT: itk.F,
    vtk.VTK_DOUBLE: itk.D,
}

def forwardSignal(source, dest, signal):
    '''Forwards a Qt signal from source to dest.

    Will throw exception if a property exists on dest has the same name
    as the signal.
    '''
    if not hasattr(source, signal):
        raise Exception(
                'Signal %s does not exist on %s' % (signal, repr(source)))
    if hasattr(dest, signal):
        raise Exception(
                'Property with name %s exists on %s' % (signal, repr(dest)))
    setattr(dest, signal, getattr(source, signal))

class ImageManager(QObject):
    '''Manager for the loaded image.'''

    # signal: image file read and opened
    imageLoaded = pyqtSignal(QObject)

    def __init__(self, parent=None):
        super(ImageManager, self).__init__(parent)

        self.filename = None
        self.vtkImage = None
        self.itkImage = None
        self.itkPixelType = None
        self.itkImageType = None
        self.dimension = 0

    def loadImage(self, filename):
        '''Tries to load a given file.

        Returns:
            Boolean if file was loaded successfully.
        '''
        self.filename = filename

        # open as VTK image
        reader = vtk.vtkImageReader2Factory.CreateImageReader2(filename)
        if reader is None:
            return False

        reader.SetFileName(filename)
        reader.Update()
        self.vtkImage = reader.GetOutput()

        # open as ITK image
        if self.vtkImage.GetScalarType() not in VTK_ITK_TYPE_CONVERSION:
            raise Exception(
                    'Image type %d is unknown' % self.vtkImage.GetScalarType())

        pixelType = VTK_ITK_TYPE_CONVERSION[self.vtkImage.GetScalarType()]
        dimension = self.vtkImage.GetDataDimension()
        imageType = itk.Image[pixelType, dimension]

        reader = itk.ImageFileReader[imageType].New()
        reader.SetFileName(filename)
        reader.Update()

        self.itkImage = reader.GetOutput()
        self.itkPixelType = pixelType
        self.dimension = dimension
        self.itkImageType = imageType

        self.imageLoaded.emit(self)
        return True

class TubeManager(QObject):
    '''Manager for segmented and imported tubes.'''

    # signal: stored tubes were updated
    tubesUpdated = pyqtSignal(itk.GroupSpatialObject[3])
    # signal: tube selection changed
    tubeSelectionChanged = pyqtSignal(set)

    def __init__(self, parent=None):
        super(TubeManager, self).__init__(parent)

        self._tubeGroup = None
        # segmentedGroup will be a child of tubeGroup
        self._segmentedGroup = None

        # map tubeId -> itk tube
        self.tubes = dict()
        self.tubeSelection = set()

        self.reset()

    def tubeGroup(self):
        '''Getter for tube group.'''
        return self._tubeGroup

    def loadTubes(self, filename):
        '''Tries to load a given tube file.

        Returns:
            Boolean if  the file was loaded successfully.
        '''
        dim = 3
        reader = itk.SpatialObjectReader[dim].New()
        reader.SetFileName(filename)
        try:
            reader.Update()
        except RuntimeError:
            pass
        else:
            tubeGroup = reader.GetGroup()
            if tubeGroup:
                # Set group name here so importTubeGroup() doesn't have to deal
                # with naming.
                basename = os.path.basename(filename)
                tubeGroup.SetObjectName('Imported tubes (%s)' % basename)
                self.importTubeGroup(tubeGroup)
                return True
        return False

    def addSegmentedTube(self, tube):
        '''Adds a segmented tube to the segmented tube set.'''
        self.tubes[str(hash(tube))] = tube
        group = tube.GetParent()

        # replace the current segment group with new one
        # also copy over transform info
        children = group.GetChildren()
        transform = group.GetObjectToWorldTransform()
        self._segmentedGroup.GetTreeNode().SetData(group)
        self._segmentedGroup.SetObjectToWorldTransform(transform)
        self._segmentedGroup.SetChildren(children)

        self.tubesUpdated.emit(self._tubeGroup)

    def importTubeGroup(self, group):
        '''Adds a whole tube group as imported tubes.'''
        for tube in TubeIterator(group):
            self.tubes[str(hash(tube))] = tube
        self._tubeGroup.AddSpatialObject(group)
        self.tubesUpdated.emit(self._tubeGroup)

    def reset(self):
        '''Resets the tube manager state.'''
        self.tubes.clear()
        self._tubeGroup = itk.GroupSpatialObject[3].New()
        self._segmentedGroup = itk.GroupSpatialObject[3].New()
        self._segmentedGroup.SetObjectName('Segmented Tubes')
        self._tubeGroup.AddSpatialObject(self._segmentedGroup)
        self.tubesUpdated.emit(self._tubeGroup)

    def toggleSelection(self, tubeId):
        '''Toggles the selection of a tube.

        Args:
            tubeId: the tube ID for which to toggle selection.
        '''
        # convert qstring to python str
        tubeId = str(tubeId)
        if tubeId in self.tubeSelection:
            self.tubeSelection.remove(tubeId)
        else:
            self.tubeSelection.add(tubeId)
        self.tubeSelectionChanged.emit(self.tubeSelection)

    def deleteSelection(self):
        '''Deletes the current tube selection.'''
        if len(self.tubeSelection) > 0:
            for tubeId in self.tubeSelection:
                tube = self.tubes[tubeId]
                tube.GetParent().RemoveSpatialObject(tube)
                del self.tubes[tubeId]
            self.tubeSelection.clear()

            self.tubesUpdated.emit(self._tubeGroup)
            self.tubeSelectionChanged.emit(self.tubeSelection)

    def clearSelection(self):
        '''Clears current tube selection.'''
        self.tubeSelection.clear()
        self.tubeSelectionChanged.emit(self.tubeSelection)

    def selectAllTubes(self):
        '''Selects all tubes.'''
        self.tubeSelection.update(self.tubes)
        self.tubeSelectionChanged.emit(self.tubeSelection)

class TubePolyManager(QObject):
    '''Manager for tube poly data.'''

    def __init__(self, parent=None):
        super(TubePolyManager, self).__init__(parent)

        # str(hash(tube)) -> vtkPolyData
        self.tubePolys = dict()
        # cached tube blocks
        self._tubeBlocks = None
        # determines if tube blocks need regeneration
        self._tubeBlocksModified = True

    def updatePolyData(self, tubeGroup):
        '''Updates the polygonal data.'''
        newTubePolys = dict()
        for tube in TubeIterator(tubeGroup):
            tubeId = str(hash(tube))
            if tubeId in self.tubePolys:
                newTubePolys[tubeId] = self.tubePolys[tubeId]
            else:
                newTubePolys[tubeId] = self._createTubePolyData(tube)
        self.tubePolys = newTubePolys
        self._tubeBlocksModified = True

    def tubeBlocks(self):
        '''Generates a tube vtkMultiBlockDataSet.'''
        if self._tubeBlocksModified:
            self._tubeBlocksModified = False
            blocks = vtk.vtkMultiBlockDataSet()
            for tubeId in self.tubePolys:
                poly = self.tubePolys[tubeId]
                curIndex = blocks.GetNumberOfBlocks()
                blocks.SetBlock(curIndex, poly)
                blocks.GetMetaData(curIndex).Set(TUBE_ID_KEY, tubeId)
            self._tubeBlocks = blocks
        return self._tubeBlocks

    def _createTubePolyData(self, tube):
        '''Generates polydata from an itk.VesselTubeSpatialObject.'''
        points = GetTubePoints(tube)

        # Convert points to world space.
        tube.ComputeObjectToWorldTransform()
        transform = tube.GetIndexToWorldTransform()
        # Get scaling vector from transform matrix diagonal.
        scaling = [transform.GetMatrix()(i,i) for i in range(3)]
        # Use average of scaling vector for scale since TubeFilter
        # doesn't seem to support ellipsoid.
        scale = sum(scaling) / len(scaling)

        for i in range(len(points)):
            pt, radius = points[i]
            pt = transform.TransformPoint(pt)
            points[i] = (pt, radius*scale)

        vpoints = vtk.vtkPoints()
        vpoints.SetNumberOfPoints(len(points))
        scalars = vtk.vtkFloatArray()
        scalars.SetNumberOfValues(len(points))
        scalars.SetName('Radii')

        minRadius = float('inf')
        maxRadius = float('-inf')
        for i, (pt, r) in enumerate(points):
            vpoints.SetPoint(i, pt)
            scalars.SetValue(i, r)
            minRadius = min(r, minRadius)
            maxRadius = max(r, maxRadius)

        pl = vtk.vtkPolyLine()
        pl.Initialize(len(points), range(len(points)), vpoints)

        ca = vtk.vtkCellArray()
        ca.InsertNextCell(pl)

        pd = vtk.vtkPolyData()
        pd.SetLines(ca)
        pd.SetPoints(vpoints)
        pd.GetPointData().SetScalars(scalars)
        pd.GetPointData().SetActiveScalars('Radii')

        tf = vtk.vtkTubeFilter()
        tf.SetInputData(pd)
        tf.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
        tf.SetRadius(minRadius)
        tf.SetRadiusFactor(maxRadius/minRadius)
        tf.SetNumberOfSides(20)
        tf.Update()

        return tf.GetOutput()

class ViewManager(QObject):
    '''Manager of the UI.'''

    def __init__(self, window, parent=None):
        super(ViewManager, self).__init__(parent)

        self.window = window
        self.tubePolyManager = TubePolyManager()

        # main window
        forwardSignal(window, self, 'fileSelected')
        forwardSignal(window.ui, self, 'viewedImageChanged')

        # vtk viewer
        forwardSignal(window.vtkView(), self, 'imageVoxelSelected')
        forwardSignal(window.vtkView(), self, 'tubeSelected')
        forwardSignal(window.vtkView(), self, 'windowLevelChanged')

        # segment tab
        forwardSignal(window.segmentTabView(), self, 'scaleChanged')

        # selection
        forwardSignal(window.selectionTabView(), self, 'deleteTubeSelClicked')
        forwardSignal(window.selectionTabView(), self, 'clearTubeSelClicked')
        forwardSignal(window.selectionTabView(), self, 'selectAllTubesClicked')

        # tube tree
        forwardSignal(window.tubeTreeTabView(), self, 'saveTubesClicked')

        # filters
        forwardSignal(window.filtersTabView(), self, 'windowLevelFilterEnabled')
        forwardSignal(window.filtersTabView(), self, 'medianFilterChanged')
        forwardSignal(window.filtersTabView(), self, 'medianFilterEnabled')
        forwardSignal(window.filtersTabView(), self, 'applyFiltersTriggered')

        # 3D view
        self.window.threeDTabView().scalarOpacityUnitDistChanged.connect(
                self.window.vtkView().setScalarOpacityUnitDist)

    def disableUi(self):
        self.setUiState(False)

    def enableUi(self):
        self.setUiState(True)

    def setUiState(self, state):
        '''Sets the Ui enabled/disabled state.'''
        self.window.ui.setEnabled(state)

    def displayImage(self, vtkImage, filename):
        '''Displays a VTK ImageData to the UI.'''
        self.window.vtkView().displayImage(vtkImage)
        self.window.infoTabView().showImageMetadata(vtkImage, filename)

        dims = vtkImage.GetDimensions()
        spacing = vtkImage.GetSpacing()

        scalarOpacityMax = math.sqrt(
                (dims[0]*spacing[0])**2 +
                (dims[1]*spacing[1])**2 +
                (dims[2]*spacing[2])**2)
        self.window.threeDTabView().setScalarOpacityRange(0, scalarOpacityMax)

    def displayTubes(self, tubeGroup):
        '''Display tubes in UI.'''
        self.tubePolyManager.updatePolyData(tubeGroup)
        # display tube tree
        self.window.tubeTreeTabView().setModel(TubeTreeViewModel(tubeGroup))
        # display tubes in 3D scene
        self.window.vtkView().showTubeBlocks(self.tubePolyManager.tubeBlocks())

    def alert(self, message):
        '''Alerts the user with some message.'''
        self.window.popupMessage(message)

    def makeProgressDialog(self, message):
        '''Returns an indeterminate progress bar.'''
        return self.window.makeProgressDialog(message)

    def setSegmentScale(self, scale):
        '''Updates view with scale.'''
        self.window.segmentTabView().setScale(scale)

    def isSegmentEnabled(self):
        '''Getter for segment button toggle state.'''
        return self.window.segmentTabView().isSegmentEnabled()

    def showJobCount(self, count):
        '''Shows segment job count.'''
        self.window.showJobCount(count)

    def showTubeSelection(self, selection):
        '''Shows a tube selection.

        Args:
            selection: an iterable of tube IDs.
        '''
        selectedTubeIndexes = list()
        # Eh, this is efficient enough. If performance issues
        # occur here, just make a datastructure mapping
        # (tubeId -> tube block index) inside TubePolyManager.tubeBlocks().
        it = self.tubePolyManager.tubeBlocks().NewTreeIterator()
        it.SetVisitOnlyLeaves(False)
        it.InitTraversal()
        while not it.IsDoneWithTraversal():
            tubeId = it.GetCurrentMetaData().Get(TUBE_ID_KEY)
            if tubeId in selection:
                selectedTubeIndexes.append(it.GetCurrentFlatIndex())
            it.GoToNextItem()

        self.window.vtkView().showTubeSelection(selectedTubeIndexes)
        self.window.selectionTabView().setTubeSelection(selection)

    def saveTubes(self, selection, filename):
        # TODO move to tube manager
        dim = 3
        model = self.window.tubeTreeTabView().model()
        tubes = [model.data(index, RAW_DATA_ROLE) for index in selection]

        if len(tubes) > 1:
            # create a tube group to hold the selection.
            group = itk.GroupSpatialObject[dim].New()
            for tube in tubes:
                group.AddSpatialObject(tube)
        else:
            group = tubes[0]

        writer = itk.SpatialObjectWriter[dim].New()
        writer.SetFileName(filename.toLatin1().data())
        writer.SetInput(group)
        writer.Update()

    def getViewedImageType(self):
        '''Gets the currently viewed image type.'''
        return self.window.ui.getViewedImageType()

class SegmentManager(QObject):
    '''Manager of tube segmentation.'''

    DEFAULT_SCALE = 2.0

    tubeSegmented = pyqtSignal(itk.VesselTubeSpatialObject[3])
    segmentationErrored = pyqtSignal(Exception)
    jobCountChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(SegmentManager, self).__init__(parent)

        self._scale = self.DEFAULT_SCALE
        self._jobCount = 0

        self.worker = SegmentWorker()
        self.workerThread = QThread()
        self.worker.moveToThread(self.workerThread)

        self.worker.terminated.connect(self.workerThread.quit)
        self.workerThread.started.connect(self.worker.run)

        self.worker.jobFinished.connect(self.processSegmentResult)
        self.worker.jobFailed.connect(self.segmentationFailed)

        self.workerThread.start()

    def stop(self):
        self.worker.stop()
        self.workerThread.quit()
        self.workerThread.wait()

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

    def setImage(self, image, pixelType, dimension):
        '''Sets segmenting image.'''
        self.worker.setImage(image, pixelType, dimension)

    def setWindowLevel(self, enabled, window, level):
        '''Sets window and level for image.'''
        self.worker.setWindowLevel(enabled, window, level)

    def setMedianParams(self, enabled, radius):
        '''Sets window and level for image.'''
        self.worker.setMedianParams(enabled, radius)

    def segmentTube(self, x, y, z):
        '''Segments a tube at (x, y, z).'''
        self._jobCount += 1
        self.jobCountChanged.emit(self._jobCount)

        args = SegmentArgs()
        args.scale = self.scale()
        args.coords = (x, y, z)
        self.worker.extractTube(args)

    def processSegmentResult(self, result):
        '''Handles segment results.'''
        self._jobCount -= 1
        self.jobCountChanged.emit(self._jobCount)
        if result.tube:
            self.tubeSegmented.emit(result.tube)

    def segmentationFailed(self, exc):
        '''Segmentation failed.'''
        self._jobCount -= 1
        self.jobCountChanged.emit(self._jobCount)
        self.segmentationErrored.emit(exc)

class FilterManager(QObject):
    '''Manages filter parameters.'''

    WINDOWLEVEL = 'Window/Level'
    MEDIAN = 'Median'

    # signal: is window/level filter enabled
    windowLevelEnabled = pyqtSignal(bool)
    # signal: Window/Level params changed
    windowLevelChanged = pyqtSignal(float, float)
    # signal: is median filter enabled
    medianFilterEnabled = pyqtSignal(bool)
    # signal: median filter params changed
    medianFilterChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(FilterManager, self).__init__(parent)

        self.itkImage = None
        self.pixelType = None
        self.dimension = None
        self.filteredImage = None

        # parameters
        self.window, self.level = 1, 0.5
        self.medianRadius = 0

        self.filters = collections.OrderedDict()
        self.enabled = dict()

    def setImage(self, itkImage, pixelType, dimension):
        '''Sets input itk image.'''
        self.itkImage = itkImage
        self.pixelType = pixelType
        self.dimension = dimension

        # setup the filters
        imageType = itk.Image[pixelType, dimension]
        self.filters = collections.OrderedDict([
            (self.WINDOWLEVEL,
                itk.IntensityWindowingImageFilter[imageType, imageType].New()),
            (self.MEDIAN,
                itk.MedianImageFilter[imageType, imageType].New()),
        ])
        self.enabled = {name: False for name in self.filters.keys()}

    def getOutput(self):
        '''Returns the filtered image, or original if no cached filter image.'''
        return self.filteredImage or self.itkImage

    def update(self):
        '''Updates filtered image.'''
        prevFilter = None
        curFilter = None
        for name in self.filters:
            if self.enabled[name]:
                curFilter = self.filters[name]
                if prevFilter is None:
                    curFilter.SetInput(self.itkImage)
                else:
                    prevFilter.Update()
                    curFilter.SetInput(prevFilter.GetOutput())
                prevFilter = curFilter

        if curFilter:
            curFilter.Update()
            self.filteredImage = curFilter.GetOutput()
            # Make sure filteredImage.Update() doesn't update the whole
            # pipeline. We only want explicit calls to self.update() to
            # update the pipeline.
            self.filteredImage.DisconnectPipeline()
        else:
            self.filteredImage = self.itkImage

    def getOutputType(self):
        '''Returns the pixel type and dimension of output image.'''
        return self.pixelType, self.dimension

    def setWindowLevelEnabled(self, enabled):
        '''Toggles window/level filter.'''
        self.enabled[self.WINDOWLEVEL] = enabled
        self.windowLevelEnabled.emit(enabled)

    def setWindowLevel(self, window, level):
        '''Sets window/level params.'''
        self.window = window
        self.level = level

        filter_ = self.filters[self.WINDOWLEVEL]

        minValue = itk.NumericTraits[self.pixelType].min()
        maxValue = itk.NumericTraits[self.pixelType].max()
        valRange = maxValue - minValue

        window = window*valRange + minValue
        level = level*valRange + minValue

        filter_.SetWindowLevel(
                int(min(maxValue, max(minValue, window))),
                int(min(maxValue, max(minValue, level))))
        filter_.SetOutputMinimum(minValue)
        filter_.SetOutputMaximum(maxValue)
        # tell Update() that something has changed
        filter_.Modified()

        self.windowLevelChanged.emit(self.window, self.level)

    def setMedianFilterEnabled(self, enabled):
        '''Toggles median filter.'''
        self.enabled[self.MEDIAN] = enabled
        self.medianFilterEnabled.emit(enabled)

    def setMedianParams(self, radius):
        '''Sets median filter state and params.'''
        self.medianRadius = radius

        filter_ = self.filters[self.MEDIAN]
        filter_.SetRadius(radius)

        self.medianFilterChanged.emit(radius)
