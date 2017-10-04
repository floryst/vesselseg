import itk
import vtk
import vtk.util.numpy_support as np_s
import vtk.numpy_interface.dataset_adapter as dsa

# Copied and modified from the Tomviz project
def itkToVtkImage(itkImage):
    '''Converts an ITK image to a VTK image.'''
    vtkImage = vtk.vtkImageData()

    buf = itk.PyBuffer[type(itkImage)].GetArrayFromImage(itkImage).copy()
    arr = buf.ravel(order='A')
    if buf.flags.f_contiguous:
        vtkshape = buf.shape
    else:
        vtkshape = buf.shape[::-1]

    minextent = vtkImage.GetExtent()[::2]
    sameindex = list(minextent) == list(vtkImage.GetExtent()[::2])
    sameshape = list(vtkshape) == list(vtkImage.GetDimensions())
    if not sameindex or not sameshape:
        extent = 6*[0]
        extent[::2] = minextent
        extent[1::2] = \
            [x + y - 1 for (x, y) in zip(minextent, vtkshape)]
        vtkImage.SetExtent(extent)

    # Now replace the scalars array with the new array.
    vtkarray = np_s.numpy_to_vtk(arr)
    vtkarray.Association = dsa.ArrayAssociation.POINT
    do = dsa.WrapDataObject(vtkImage)
    oldscalars = do.PointData.GetScalars()
    arrayname = "Scalars"
    if oldscalars is not None:
        arrayname = oldscalars.GetName()
    del oldscalars
    do.PointData.append(arr, arrayname)
    do.PointData.SetActiveScalars(arrayname)

    return vtkImage
