# VesselSeg

This is an application for interactive vessel segmentation.

## Setup

A few prerequisites:

- PyQt5
- numpy
- [VTK](https://github.com/kitware/vtk)
  - Should be built with Python bindings (cmake variable `VTK_WRAP_PYTHON:BOOL=ON`)
- [ITKTubeTK](https://github.com/floryst/ITKTubeTK)
  - Note: This uses a custom build of ITKTubeTK, so be sure to clone from the link
    above rather than the primary ITKTubeTK repo.
