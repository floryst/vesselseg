from PyQt4.QtCore import Qt, pyqtSignal
from PyQt4.QtGui import *

METADATA_TEMPLATE = \
'''
<strong>Image Properties</strong>
<div>Dimensions: %(dimX).1f x %(dimY).1f x %(dimZ).1f</div>
<div>Spacing: %(spacingX).3f x %(spacingY).3f x %(spacingZ).3f</div>
'''

class TubeTreeTab(QTreeView):
    '''Tube tree tab displays tubes in tree view.'''

    def __init__(self, parent=None):
        super(TubeTreeTab, self).__init__(parent)

class SegmentTab(QWidget):
    '''Segment tab holds parameter inputs for segmentation.'''

    # signal: scale input changed
    scaleChanged = pyqtSignal(float)
    # signal: segmentation enabled/disabled
    segmentEnabled = pyqtSignal(bool)

    SCALE_SIZES = [
        ('Custom', 1.0),
        ('Small', 0.5),
        ('Medium', 1.0),
        ('Large', 1.5),
        ('Large++', 2.0),
        ('Huge', 5.0),
    ]

    def __init__(self, parent=None):
        super(SegmentTab, self).__init__(parent)

        self.grid = QGridLayout(self)

        self.segmentBtn = QPushButton('Toggle segment', self)
        self.segmentBtn.setCheckable(True)
        self.grid.addWidget(self.segmentBtn, 0, 0)

        scaleLabel = QLabel('Scale:', self)
        scaleLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.grid.addWidget(scaleLabel, 1, 0, Qt.AlignRight)

        self.scaleInput = QLineEdit(self)
        # TODO set this from SegmentManager's default
        self.scaleInput.setPlaceholderText('2.0')
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.scaleInput.setValidator(validator)
        self.grid.addWidget(self.scaleInput, 1, 1)

        self.scaleCombo = QComboBox(self)
        for size, _ in self.SCALE_SIZES:
            self.scaleCombo.addItem(size)
        self.grid.addWidget(self.scaleCombo, 1, 2)

        spacer = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.grid.addItem(spacer, 2, 0)

        self.segmentBtn.clicked.connect(
                lambda: self.segmentEnabled.emit(self.segmentBtn.isChecked()))
        self.scaleInput.textChanged.connect(
                lambda s: self.scaleChanged.emit(float(s or 0)))
        self.scaleCombo.activated.connect(self.setScalePreset)

    def setScale(self, scale):
        '''Setter for scale.'''
        self.scaleInput.setText(str(scale))

    def setScalePreset(self, index):
        '''Sets the scale according to a preset.

        Args:
            index: the index into SCALE_SIZES
        '''
        preset, scale = self.SCALE_SIZES[index]
        # TODO handle enabled/disabled UI
        if preset == 'Custom':
            self.scaleInput.setEnabled(True)
        else:
            self.scaleInput.setEnabled(False)
            self.setScale(scale)

    def isSegmentEnabled(self):
        '''Checks if segmentation is enabled.'''
        return self.segmentBtn.isChecked()

class SelectionTab(QWidget):
    '''Shows tube selection.'''

    COUNT_LABEL = 'Number of selected tubes: %d'

    # signal: request deletion of current tube selection
    wantTubeSelectionDeleted = pyqtSignal()

    def __init__(self, parent=None):
        super(SelectionTab, self).__init__(parent)

        self.form = QFormLayout(self)

        self.countLabel = QLabel(self.COUNT_LABEL % 0)
        self.form.addWidget(self.countLabel)

        self.deleteBtn = QPushButton('Delete selection')
        self.form.addWidget(self.deleteBtn)

        self.deleteBtn.clicked.connect(self.wantTubeSelectionDeleted)

    def setTubeSelection(self, tubeSelection):
        '''Sets the count of tubes.

        Args:
            tubeSelection: an iterable of selected tubes.
        '''
        self.countLabel.setText(self.COUNT_LABEL % len(tubeSelection))

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
