from PyQt4.QtCore import QThread, QObject, pyqtSignal

import vtk
import itk
from vtk.util import keys

from segmenttubes import SegmentWorker, SegmentArgs, TubeIterator, GetTubePoints
from models import TubeTreeViewModel

TUBE_ID_KEY = keys.MakeKey(keys.StringKey, 'tube.id', '')

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

class TubeManager(QObject):
    '''Manager for segmented and imported tubes.'''

    # signal: stored tubes were updated
    tubesUpdated = pyqtSignal(itk.GroupSpatialObject[3])
    # signal: tube selection changed
    tubeSelectionChanged = pyqtSignal(set)

    def __init__(self, parent=None):
        super(TubeManager, self).__init__(parent)

        self._tubeGroup = itk.GroupSpatialObject[3].New()
        # segmentedGroup will be a child of tubeGroup
        self._segmentedGroup = itk.GroupSpatialObject[3].New()
        self._segmentedGroup.SetObjectName('Segmented Tubes')

        self.tubeSelection = set()

    def tubeGroup(self):
        '''Getter for tube group.'''
        return self._tubeGroup

    def addSegmentedTube(self, tube):
        '''Adds a segmented tube to the segmented tube set.'''
        self._segmentedGroup.AddSpatialObject(tube)
        self.tubesUpdated.emit(self._tubeGroup)

    def reset(self):
        '''Resets the tube manager state.'''
        self._tubeGroup.Clear()
        self._segmentedGroup.Clear()
        self._tubeGroup.AddSpatialObject(self._segmentedGroup)

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

class TubePolyManager(QObject):
    '''Manager for tube poly data.'''

    def __init__(self, parent=None):
        super(TubePolyManager, self).__init__(parent)

        # str(hash(tube)) -> vtkPolyData
        self.tubePolys = dict()

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
        blocks = vtk.vtkMultiBlockDataSet()
        for tubeId in self.tubePolys:
            poly = self.tubePolys[tubeId]
            curIndex = blocks.GetNumberOfBlocks()
            blocks.SetBlock(curIndex, poly)
            blocks.GetMetaData(curIndex).Set(TUBE_ID_KEY, tubeId)
        return blocks

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

    # signal: file was selected for loading
    fileSelected = pyqtSignal(str)
    # signal: scale input changed
    scaleChanged = pyqtSignal(float)
    # signal: image voxel selected
    imageVoxelSelected = pyqtSignal(float, float, float)
    # signal: a tube was selected
    tubeSelected = pyqtSignal(str)

    def __init__(self, window, parent=None):
        super(ViewManager, self).__init__(parent)

        self.window = window
        self.tubePolyManager = TubePolyManager()

        self.window.fileSelected.connect(self.fileSelected)
        self.window.vtkView().imageVoxelSelected.connect(self.imageVoxelSelected)
        self.window.vtkView().volumeBlockSelected.connect(self.pickTubeBlock)
        self.window.segmentTabView().scaleChanged.connect(self.scaleChanged)

    def displayImage(self, vtkImage):
        '''Displays a VTK ImageData to the UI.'''
        self.window.vtkView().displayImage(vtkImage)
        self.window.infoTabView().showImageMetadata(vtkImage)

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

    def setSegmentScale(self, scale):
        '''Updates view with scale.'''
        self.window.segmentTabView().setScale(scale)

    def isSegmentEnabled(self):
        '''Getter for segment button toggle state.'''
        return self.window.segmentTabView().isSegmentEnabled()

    def pickTubeBlock(self, blockIndex):
        '''Picks out the clicked tube.'''
        it = self.tubePolyManager.tubeBlocks().NewTreeIterator()
        it.SetVisitOnlyLeaves(False)
        it.InitTraversal()
        while not it.IsDoneWithTraversal():
            if blockIndex == it.GetCurrentFlatIndex():
                tubeId = it.GetCurrentMetaData().Get(TUBE_ID_KEY)
                self.tubeSelected.emit(tubeId)
                break
            it.GoToNextItem()

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

class SegmentManager(QObject):
    '''Manager of tube segmentation.'''

    DEFAULT_SCALE = 2.0

    tubeSegmented = pyqtSignal(itk.VesselTubeSpatialObject[3])

    def __init__(self, parent=None):
        super(SegmentManager, self).__init__(parent)

        self._scale = self.DEFAULT_SCALE

        self.worker = SegmentWorker()
        self.workerThread = QThread()
        self.worker.moveToThread(self.workerThread)

        self.worker.terminated.connect(self.workerThread.quit)
        self.workerThread.started.connect(self.worker.run)

        self.worker.jobFinished.connect(self.processSegmentResult)

        self.workerThread.start()

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

    def setImage(self, vtkImageData):
        '''Sets segmenting image.'''
        self.worker.setImage(vtkImageData)

    def segmentTube(self, x, y, z):
        '''Segments a tube at (x, y, z).'''
        args = SegmentArgs()
        args.scale = self.scale()
        args.coords = (x, y, z)
        self.worker.extractTube(args)

    def processSegmentResult(self, result):
        '''Handles segment results.'''
        if result.tube:
            self.tubeSegmented.emit(result.tube)
