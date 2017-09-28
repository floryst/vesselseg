from PyQt4.QtCore import Qt, pyqtSignal, QPoint
from PyQt4.QtGui import *

METADATA_TEMPLATE = \
'''
<strong>Image Properties</strong>
<div>Dimensions: %(dimX).1f x %(dimY).1f x %(dimZ).1f</div>
<div>Spacing: %(spacingX).3f x %(spacingY).3f x %(spacingZ).3f</div>
'''

class TubeTreeTab(QTreeView):
    '''Tube tree tab displays tubes in tree view.'''

    # signal: defer tube saving to a non-view componetn
    wantSaveTubes = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super(TubeTreeTab, self).__init__(parent)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.saveAction = QAction('Save tube(s)...', self)

        self.contextMenu = QMenu(self)
        self.contextMenu.addAction(self.saveAction)

        self.saveAction.triggered.connect(self.saveTubes)

    def contextMenuEvent(self, event):
        '''Opens a context menu.'''
        index = self.indexAt(QPoint(event.x(), event.y()))
        if index.isValid():
            self.contextMenu.exec_(QPoint(event.globalX(), event.globalY()))

    def saveTubes(self):
        '''Save selected tubes.'''
        selection = self.selectionModel().selectedIndexes()
        if len(selection):
            ext = '.tre'
            filename = QFileDialog.getSaveFileName(
                    self, 'Save File', '', ext)
            if filename:
                self.wantSaveTubes.emit(selection, str(filename + ext))

class FiltersTab(QWidget):
    '''Filters tab holds options for preprocessing the segment image.'''

    # signal: window/level filter changed (enabled)
    windowLevelFilterChanged = pyqtSignal(bool)
    # signal: median filter state changed (enabled, radius)
    medianFilterChanged = pyqtSignal(bool, int)

    def __init__(self, parent=None):
        super(FiltersTab, self).__init__(parent)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.windowLevelCheckbox = QCheckBox('Window/Level filter', self)
        self.layout.addWidget(self.windowLevelCheckbox)

        self.medianCheckbox = QCheckBox('Median filter', self)
        self.layout.addWidget(self.medianCheckbox)

        # median filter parameters
        self.medianFilterParams = QWidget(self)
        self.medianFilterForm = QFormLayout(self.medianFilterParams)
        self.medianFilterParams.setLayout(self.medianFilterForm)
        self.medianRadiusInput = QSpinBox(self)
        self.medianFilterForm.addRow('Radius:', self.medianRadiusInput)

        self.medianFilterParams.setEnabled(False)
        self.layout.addWidget(self.medianFilterParams)

        spacer = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        self.windowLevelCheckbox.stateChanged.connect(
                self.windowLevelStateChanged)
        self.medianCheckbox.stateChanged.connect(
                self.toggleMedianFilter)
        self.medianRadiusInput.valueChanged.connect(
                self.emitMedianFilterChanged)

    def windowLevelStateChanged(self, state):
        self.windowLevelFilterChanged.emit(bool(state))

    def toggleMedianFilter(self, state):
        self.medianFilterParams.setEnabled(bool(state))
        self.emitMedianFilterChanged()

    def setMedianRadius(self, _):
        self.emitMedianFilterChanged()

    def emitMedianFilterChanged(self):
        self.medianFilterChanged.emit(
                self.medianCheckbox.isChecked(),
                self.medianRadiusInput.value())

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

        self.segmentBtn.clicked.connect(self.onSegmentBtnClicked)
        self.scaleInput.textChanged.connect(self.onScaleInputChanged)
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

    def onSegmentBtnClicked(self):
        self.segmentEnabled.emit(self.segmentBtn.isChecked())

    def onScaleInputChanged(self, text):
        self.scaleChanged.emit(float(text or 0))

    def isSegmentEnabled(self):
        '''Checks if segmentation is enabled.'''
        return self.segmentBtn.isChecked()

class SelectionTab(QWidget):
    '''Shows tube selection.'''

    COUNT_LABEL = 'Number of selected tubes: %d'

    # signal: request deletion of current tube selection
    wantTubeSelectionDeleted = pyqtSignal()
    # signal: request clearing of current tube selection
    wantTubeSelectionCleared = pyqtSignal()
    # signal: request selecting of all tubes
    wantAllTubesSelected = pyqtSignal()

    def __init__(self, parent=None):
        super(SelectionTab, self).__init__(parent)

        self.form = QFormLayout(self)

        self.countLabel = QLabel(self.COUNT_LABEL % 0)
        self.form.addWidget(self.countLabel)

        self.selAllBtn = QPushButton('Select All')
        self.form.addWidget(self.selAllBtn)

        self.deleteBtn = QPushButton('Delete selection')
        self.form.addWidget(self.deleteBtn)

        self.clearBtn = QPushButton('Clear selection')
        self.form.addWidget(self.clearBtn)

        self.selAllBtn.clicked.connect(self.wantAllTubesSelected)
        self.deleteBtn.clicked.connect(self.wantTubeSelectionDeleted)
        self.clearBtn.clicked.connect(self.wantTubeSelectionCleared)

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
