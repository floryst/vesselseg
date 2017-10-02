import copy
import Queue
import collections
from math import ceil, floor
from StringIO import StringIO

import vtk
import itk
import itkTypes
import itkExtras

from PyQt5.QtCore import *

from tomviz import itkutils

VTK_ITK_TYPE_CONVERSION = {
    vtk.VTK_UNSIGNED_CHAR: itkTypes.UC,
    vtk.VTK_UNSIGNED_INT: itkTypes.UI,
    vtk.VTK_UNSIGNED_LONG: itkTypes.UL,
    # set this as a signed short for now. The python bindings
    # don't have unsigned short :(
    vtk.VTK_UNSIGNED_SHORT: itkTypes.SS,
    vtk.VTK_CHAR: itkTypes.SC,
    vtk.VTK_INT: itkTypes.SI,
    vtk.VTK_LONG: itkTypes.SL,
    vtk.VTK_SHORT: itkTypes.SS,
    vtk.VTK_FLOAT: itkTypes.F,
    vtk.VTK_DOUBLE: itkTypes.D,
}


class BusyException(Exception):
    pass

class SegmentArgs(object):
    '''Wrapper for segmentation arguments.'''
    scale = 2.0
    coords = (0, 0, 0)

class SegmentResult(object):
    '''Wraps segment result.'''
    def __init__(self, tube):
        self.tube = tube

class SegmentWorker(QObject):
    '''Threaded worker to perform tube segmentation.'''

    SEGMENT, WINDOWLEVEL, MEDIAN = range(3)

    # signal: segmentation job finished
    jobFinished = pyqtSignal(SegmentResult)
    # signal: segmentation job threw exception
    jobFailed = pyqtSignal(Exception)
    # signal: segment worker terminated
    terminated = pyqtSignal()

    def __init__(self, parent=None):
        super(SegmentWorker, self).__init__(parent)

        self.jobQueue = Queue.Queue()
        self.stopFlag = False
        self.busyFlag = False
        self.clearFlag = False
        self.segmenter = SegmentTubes()

    def run(self):
        while not self.stopFlag:
            if self.clearFlag:
                self.jobQueue = Queue.Queue()
                self.clearFlag = False
            try:
                action, args = self.jobQueue.get(True, 0.5)
            except Queue.Empty:
                pass
            else:
                if action == self.SEGMENT:
                    self.busyFlag = True
                    self._extractTube(args)
                elif action == self.WINDOWLEVEL:
                    enabled, window, level = args
                    filter_ = self.segmenter.getFilter()
                    if filter_:
                        filter_.setWindowLevel(enabled, window, level)
                elif action == self.MEDIAN:
                    enabled, radius = args
                    filter_ = self.segmenter.getFilter()
                    if filter_:
                        filter_.setMedianParams(enabled, radius)
                self.busyFlag = not self.jobQueue.empty()

        # tell main thread that this worker has terminated
        self.terminated.emit()

    def _extractTube(self, args):
        if self.segmenter:
            self.segmenter.scale = args.scale
            try:
                tube = self.segmenter.extractTube(args.coords)
            except Exception as e:
                self.jobFailed.emit(e)
            else:
                self.jobFinished.emit(SegmentResult(tube))

    def extractTube(self, args):
        '''Queue up a segment job.

        This is meant to be called by code in a different thread.
        '''
        # make deepcopy to prevent modification via references
        self.jobQueue.put((self.SEGMENT, copy.deepcopy(args)))

    def setWindowLevel(self, enabled, window, level):
        '''Sets window/level for image.'''
        self.jobQueue.put((self.WINDOWLEVEL, (enabled, window, level)))

    def setMedianParams(self, enabled, radius):
        '''Sets window/level for image.'''
        self.jobQueue.put((self.MEDIAN, (enabled, radius)))

    def stop(self):
        '''Tell this worker to stop when possible.'''
        self.stopFlag = True

    def clearJobs(self):
        '''Tell this worker to clear all jobs when possible.'''
        self.clearFlag = True

    def isBusy(self):
        '''Flag if worker is busy.'''
        return self.busyFlag

    def setImage(self, vtkImage):
        '''Sets the image to process.

        Args:
            vtkImage: input VTK image.

        Raises:
            segment_worker.BusyException: Cannot set input if currently busy.
        '''
        if self.isBusy():
            raise BusyException()
        self.segmenter.setImage(vtkImage)

    def getTubeGroup(self):
        '''Gets the extracted tube group, if any.

        Returns:
            Extracted tube group as a itk.VesselTubeSpatialObject, otherwise
            None if no tube group was found.
        '''
        return self.segmenter.getTubeGroup()

class SegmentImageFilter(object):
    '''Constructs image filter.'''

    WINDOWLEVEL = 'Window/Level'
    MEDIAN = 'Median'

    def __init__(self, image, imageType, pixelType):
        self.inputImage = image
        self.imageType = imageType
        self.pixelType = pixelType

        # filters are processed in list order
        self.filters = collections.OrderedDict([
            (self.WINDOWLEVEL,
                itk.IntensityWindowingImageFilter[imageType, imageType].New()),
            (self.MEDIAN,
                itk.MedianImageFilter[imageType, imageType].New()),
        ])
        self.enabled = {name: False for name in self.filters.keys()}

    def getOutput(self):
        '''Returns the filtered image.'''
        prevFilter = None
        curFilter = None
        for name in self.filters:
            if self.enabled[name]:
                curFilter = self.filters[name]
                if prevFilter is None:
                    curFilter.SetInput(self.inputImage)
                else:
                    prevFilter.Update()
                    curFilter.SetInput(prevFilter.GetOutput())
                prevFilter = curFilter

        if curFilter:
            curFilter.Update()
            return curFilter.GetOutput()
        else:
            return self.inputImage

    def setWindowLevel(self, enabled, window, level):
        '''Sets window/level params.

        Args:
            enabled: Bool dictating if window/level filter is enabled
            window: Must be between 0 and 1
            level: Must be between 0 and 1
        '''
        self.enabled[self.WINDOWLEVEL] = enabled
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

    def setMedianParams(self, enabled, radius):
        self.enabled[self.MEDIAN] = enabled
        filter_ = self.filters[self.MEDIAN]
        filter_.SetRadius(radius)

class SegmentTubes(object):
    '''Holds logic to segment tubes from an image.'''

    def __init__(self):
        '''Creates a SegmentTubes object.

        The tube segmentation scale is set to default 2.0.
        '''
        self.itkImage = None
        self.pixelType = None
        self.dimension = None
        self.imageType = None
        self.tubeGroup = None
        self.segTubes = None
        self.scale = 2.0
        self.filter = None

    def setImage(self, vtkImage):
        '''Sets the input image.

        Args:
            vtkImage: a vtkImageData image object.

        Raises:
            Exception: could not convert VTK image to ITK image.
        '''
        # convert vtkimage to itkimage
        if vtkImage.GetScalarType() not in VTK_ITK_TYPE_CONVERSION:
            raise Exception(
                    'Image type %d is unknown' % vtkImage.GetScalarType())

        pixelType = VTK_ITK_TYPE_CONVERSION[vtkImage.GetScalarType()]
        dimension = vtkImage.GetDataDimension()
        itkImage = itkutils.convert_vtk_to_itk_image(vtkImage, pixelType)

        self.itkImage = itkImage
        self.pixelType = pixelType
        self.dimension = dimension
        self.imageType = itk.Image[pixelType, dimension]

        self.filter = SegmentImageFilter(itkImage, self.imageType, pixelType)

    def extractTube(self, coords):
        '''Tries to extract a tube at coordinates.

        Args:
            coords: 3D coordinates in the image.

        Raises:
            Exception: no image supplied as input.
        '''
        if self.itkImage is None:
            raise Exception('No input image provided!')

        # create a new segment tubes every extraction so we get an updated
        # image to segment on.
        self.segTubes = itk.TubeTKITK.SegmentTubes[self.imageType].New()
        self.segTubes.SetInputImage(self.filter.getOutput())

        self.tubeGroup = self.segTubes.GetTubeGroup()

        seedPoint = itk.Point[itkTypes.D, self.dimension]()
        for idx, c in enumerate(coords):
            seedPoint[idx] = c

        index = self.itkImage \
                .TransformPhysicalPointToContinuousIndex(seedPoint)

        scaleNorm = self.itkImage.GetSpacing()[0]
        if self.scale/scaleNorm < 0.3:
            raise Exception('scale/scaleNorm < 0.3')
        self.segTubes.SetRadius(self.scale/scaleNorm)

        self.segTubes.SetDebug(True)

        tube = self.segTubes.ExtractTube(index, 0, True)
        if tube:
            self.segTubes.AddTube(tube)

            scaleVector = self.itkImage.GetSpacing()
            offsetVector = self.itkImage.GetOrigin()

            self.segTubes.GetTubeGroup().ComputeObjectToParentTransform()
            self.segTubes.GetTubeGroup().ComputeObjectToWorldTransform()
            tube.ComputeObjectToWorldTransform()

            self.segTubes.GetTubeGroup().GetObjectToParentTransform() \
                    .SetScale(scaleVector)
            self.segTubes.GetTubeGroup().GetObjectToParentTransform() \
                    .SetOffset(offsetVector)
            self.segTubes.GetTubeGroup().GetObjectToParentTransform() \
                    .SetMatrix(self.itkImage.GetDirection())
            self.segTubes.GetTubeGroup().ComputeObjectToWorldTransform()
        return tube

    def getTubeGroup(self):
        '''Gets the extracted tube group, if any.

        Returns:
            Extracted tube group as a itk.VesselTubeSpatialObject, otherwise
            None if no tube group was found.
        '''
        return self.tubeGroup

    def getFilter(self):
        '''Getter for image filter.'''
        return self.filter

def DowncastToVesselTubeSOPoint(soPoint):
    '''Hacky way to downcast SpatialObjectPoint.'''
    buf = StringIO()
    print >> buf, soPoint
    buf.seek(0)
    props = buf.read().split("\n")

    dim = len(soPoint.GetPosition())
    vesselTubePoint = itk.VesselTubeSpatialObjectPoint[dim]()

    vesselTubePoint.SetID(soPoint.GetID())
    vesselTubePoint.SetPosition(*soPoint.GetPosition())
    vesselTubePoint.SetBlue(soPoint.GetBlue())
    vesselTubePoint.SetGreen(soPoint.GetGreen())
    vesselTubePoint.SetRed(soPoint.GetRed())
    vesselTubePoint.SetAlpha(soPoint.GetAlpha())

    radius = float(props[3].strip()[len("R: "):])
    vesselTubePoint.SetRadius(radius)

    tangent = list(map(float, props[5].strip()[len("T: ["):-1].split(",")))
    vesselTubePoint.SetTangent(*tangent)

    normal1 = list(map(float, props[6].strip()[len("Normal1: ["):-1].split(",")))
    normal2 = list(map(float, props[7].strip()[len("Normal2: ["):-1].split(",")))
    vesselTubePoint.SetNormal1(*normal1)
    vesselTubePoint.SetNormal2(*normal2)

    medialness = float(props[8].strip()[len("Medialness: "):])
    vesselTubePoint.SetMedialness(medialness)

    ridgeness = float(props[9].strip()[len("Ridgeness: "):])
    vesselTubePoint.SetRidgeness(ridgeness)

    alpha1 = float(props[10].strip()[len("Alpha1: "):])
    alpha2 = float(props[11].strip()[len("Alpha2: "):])
    alpha3 = float(props[12].strip()[len("Alpha3: "):])
    vesselTubePoint.SetAlpha1(alpha1)
    vesselTubePoint.SetAlpha2(alpha2)
    vesselTubePoint.SetAlpha3(alpha3)

    mark = float(props[13].strip()[len("Mark: "):])
    vesselTubePoint.SetMark(bool(mark))

    return vesselTubePoint

def GetTubePoints(tube):
    '''Gets the points and radii associated with the tube.'''
    points = list()
    for j in range(tube.GetNumberOfPoints()):
        point = tube.GetPoint(j)
        point = DowncastToVesselTubeSOPoint(point)

        radius = point.GetRadius()
        pos = point.GetPosition()

        # I think I need to extract the values otherwise corruption occurs
        # on the itkPointD3 objects.
        points.append(((pos[0], pos[1], pos[2]), radius))
    return points

def TubeIterator(tubeGroup):
    '''Iterates over all tubes in a tube group.'''
    obj = itkExtras.down_cast(tubeGroup)
    if isinstance(obj, itk.VesselTubeSpatialObject[3]):
        yield obj

    # otherwise, `obj` is a GroupSpatialObject
    children = obj.GetChildren()
    for i in range(obj.GetNumberOfChildren()):
        for tube in TubeIterator(children[i]):
            yield tube
