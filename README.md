# VesselSeg

This is an application for interactive vessel segmentation.

## Setup

A few prerequisites:

- pip
  - To install other dependencies
- CMake
  - To compile certain dependencies (until ITKTubeTK is available via pip)
- Qt
  - Version 5.7.1 or later
  - On Windows, you must get the binary from https://download.qt.io/archive/qt/5.7/5.7.1/
- PyQt5
  - On Windows, you must follow the instructions at: https://github.com/pyqt/python-qt5
- numpy
- [VTK](https://github.com/kitware/vtk)
  - `CMAKE_BUILD_TYPE` should be Release
  - Might as well turn `BUILD_TESTING` off
  - Should be built with Python bindings (cmake variable `VTK_WRAP_PYTHON:BOOL=ON`)
  - Should be built with Qt (cmake variable `VTK_GROUP_QT:NOOL=ON`)
  - Set `QT_QMAKE_EXECUTABLE` to the appropriate path (e.g., `C:/src/qt5/5.7.1/5.7/msvc2013_64/bin/qmake.exe`)
  - Set `VTK_QT_VERSION=5`
  - Set `QT5_DIR` to the obscure dir `C:/src/qt5/5.7.1/5.7/msvc2013_64/lib/cmake/Qt5`
- [ITKTubeTK](https://github.com/floryst/ITKTubeTK)
  - Note: This uses a custom build of ITKTubeTK, so be sure to clone from the link
    above rather than the primary ITKTubeTK repo.
