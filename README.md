# VesselSeg

This is an application for interactive vessel segmentation.

## Setup

A few prerequisites:

- PyQt5
- numpy
- [VTK](https://github.com/kitware/vtk)
  - Should be built with Python bindings (cmake variable `VTK_WRAP_PYTHON:BOOL=ON`)
- [ITKTubeTK](https://github.com/KitwareMedical/ITKTubeTK)

**TODO** ITKTubeTK should be set up with python threading support, which is not
enabled by default.
