from PyQt5.QtCore import *

import itk
import itkExtras

# Custom Qt role that represents raw data
RAW_DATA_ROLE = 0x1000

class TubeTreeViewModel(QAbstractItemModel):
    def __init__(self, tubeGroup, *args, **kwargs):
        super(TubeTreeViewModel, self).__init__(*args, **kwargs)

        self.rootItem = TubeItem(tubeGroup)
        self.header = 'Tube Groups'

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.rootItem

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.rootItem

        return parentItem.childCount()

    def columnCount(self, parent):
        # always 1 column since we don't display other data.
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return repr(index.internalPointer())
        elif role == RAW_DATA_ROLE:
            return index.internalPointer().getRawData()

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header
        return None

class TubeItem(object):
    def __init__(self, tubeGroup, parent=None):
        self.tubeGroup = tubeGroup
        self.children = list()
        self.childMap = dict()
        self.parentItem = parent

        # assume we are handling only 3D spatial objects
        if tubeGroup is not None and \
                isinstance(tubeGroup, itk.GroupSpatialObject[3]):
            children = self.tubeGroup.GetChildren()
            for i in range(tubeGroup.GetNumberOfChildren()):
                self.addChild(itkExtras.down_cast(children[i]))

    def childCount(self):
        return len(self.children)

    def child(self, row):
        try:
            return self.children[row]
        except:
            return None

    def columnCount(self):
        return 1

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.children.index(self)
        return 0

    def __repr__(self):
        if isinstance(self.tubeGroup, itk.VesselTubeSpatialObject[3]):
            return 'Tube (%d points)' % self.tubeGroup.GetNumberOfPoints()
        elif isinstance(self.tubeGroup, itk.GroupSpatialObject[3]):
            name = 'Tube group'
            if self.tubeGroup.GetObjectName():
                name += ' (%s)' % self.tubeGroup.GetObjectName()
            return name
        else:
            return '????'

    def getRawData(self):
        return self.tubeGroup

    def addChild(self, tubeGroup):
        item = TubeItem(tubeGroup, self)
        self.children.append(item)
