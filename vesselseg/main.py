import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QObject
from mainwindow import MainWindow
from managers import ImageManager, ViewManager

class VesselSegApp(QObject):

    def __init__(self, parent=None):
        super(VesselSegApp, self).__init__(parent)

        self.qapp = QApplication(sys.argv)
        self.window = MainWindow()
        self.imageManager = ImageManager()
        self.viewManager = ViewManager(self.window)

        self.viewManager.fileSelected.connect(self.loadFile)

    def run(self):
        '''Runs the application.

        Returns:
            An integer representing the termination state.
        '''
        self.window.show()
        return self.qapp.exec_()

    def loadFile(self, qfilename):
        filename = qfilename.toLatin1().data()
        if self.imageManager.loadImage(filename):
            return

if __name__ == '__main__':
    app = VesselSegApp()
    sys.exit(app.run())
