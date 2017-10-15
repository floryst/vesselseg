# VesselSeg

This is an application for interactive vessel segmentation.

## Setup

A few prerequisites:

- Python 2.7
- pip
  - To install other dependencies
- CMake
  - To compile certain dependencies (until ITKTubeTK is available via pip)
- Qt
  - Version 5.7.1 or later
  - On Windows, you must get the binary from https://download.qt.io/archive/qt/5.7/5.7.1/
- PyQt5
  - On Windows, build PyQt5 using the Qt5.7.1 installation from above
  - Follow the directions at http://pyqt.sourceforge.net/Docs/PyQt5/installation.html
  - The installation of sip is as mentioned in those directions (no modifications)
  - Before configuring PyQt5, rename Qt5/include/QtNfc, see https://riverbankcomputing.com/pipermail/pyqt/2015-August/036222.html
  - When configuring PyQt5, give the argument --qmake `C:\Qt\Qt5.7.1\5.7\msvc2013_64\bin\qmake.exe`
- [VTK](https://github.com/kitware/vtk)
  - `CMAKE_BUILD_TYPE` should be Release
  - Might as well turn `BUILD_TESTING` off
  - Should be built with Python bindings (cmake variable `VTK_WRAP_PYTHON:BOOL=ON`)
  - Should be built with Qt (cmake variable `VTK_GROUP_QT:NOOL=ON`)
  - Set `QT_QMAKE_EXECUTABLE` to the appropriate path, e.g., `C:\Qt\Qt5.7.1\5.7\msvc2013_64\bin\qmake.exe`
  - Set `VTK_QT_VERSION=5`
  - Set `QT5_DIR` to the obscure dir `C:\Qt\Qt5.7.1\5.7\msvc2013_64\lib\cmake\Qt5`
- [ITK](https://github.com/insightsoftwareconsortium/itk)
  - `CMAKE_BUILD_TYPE` should be Release
   - Should be built with Python bindings (cmake variable `ITK_WRAP_PYTHON:BOOL=ON`)
- [ITKTubeTK](https://github.com/KitwareMedical/ITKTubeTK)
  - Note: This uses a custom build of ITKTubeTK, so be sure to clone from the link
    above rather than the primary ITKTubeTK repo.
  - `CMAKE_BUILD_TYPE` should be Release
  - Should be built using the ITK build from above (cmake variable `USE_SYSTEM_ITK:BOOL=ON`, then define `ITK_DIR`)
  - Should be built using the VTK build from above (cmake variable `USE_SYSTEM_VTK:BOOL=ON`, then define `VTK_DIR`)
- Set your PATH to include QT's bin directory (for Qt shared library access).
  - Could also set qt.conf file for python, per http://doc.qt.io/qt-5/qt-conf.html
