from PyQt4.QtCore import Qt
from PyQt4.QtGui import *

METADATA_TEMPLATE = \
'''
<strong>Image Properties</strong>
<div>Dimensions: %(dimX).1f x %(dimY).1f x %(dimZ).1f</div>
<div>Spacing: %(spacingX).3f x %(spacingY).3f x %(spacingZ).3f</div>
'''

class SegmentTab(QWidget):
    '''Segment tab holds parameter inputs for segmentation.'''

    def __init__(self, parent=None):
        super(SegmentTab, self).__init__(parent)

class InfoTab(QLabel):
    '''Info tab holds miscellaneous information.'''

    def __init__(self, parent=None):
        super(InfoTab, self).__init__(parent)

        self.setAlignment(Qt.AlignTop)

    def showImageMetadata(self, vtkImageData):
        '''Shows the image metadata.'''
        dims = vtkImageData.GetDimensions()
        spacing = vtkImageData.GetSpacing()
        props = {
            'dimX': dims[0],
            'dimY': dims[1],
            'dimZ': dims[2],
            'spacingX': spacing[0],
            'spacingY': spacing[1],
            'spacingZ': spacing[2],
        }
        self.setText(METADATA_TEMPLATE % props)
