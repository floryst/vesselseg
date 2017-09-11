import sys

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt4.QtGui import QApplication
from mainwindow import MainWindow

def main():
    app = QApplication(sys.argv)

    m = MainWindow()
    m.show()

    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
