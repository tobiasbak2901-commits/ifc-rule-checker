# 3D VTK Viewer Implementation

## Overview
The IFC Rule Checker now includes a proper 3D VTK viewer that displays actual pipe geometry instead of just bounding boxes.

## Features

### Real Geometry Visualization
- **Actual Pipe Geometry**: Instead of showing just wireframe bounding boxes, the viewer now extracts and displays the full 3D mesh geometry from the IFC file
- **Proper Color Coding**: 
  - Group A elements: Red
  - Group B elements: Blue
  - Clash bounding boxes: Yellow (when applicable)
- **Interactive 3D View**: Full mouse-based 3D rotation, zoom, and pan using VTK's trackball camera

### Seamless Integration
- The 3D viewer replaces the static image preview
- Automatically loads and displays geometry when an issue is selected
- Maintains all existing functionality (clash detection, BCF export, JSON export)

## Architecture

### VTK3DViewer Class
New Qt widget that wraps VTK rendering components:

```python
class VTK3DViewer(QtWidgets.QWidget):
    - clear(): Remove all actors from scene
    - add_geometry_from_shape(): Add IFC geometry mesh
    - add_bounding_box(): Add wireframe box for reference
    - fit_to_view(): Auto-focus camera on all geometry
    - render(): Trigger renderer update
```

### Geometry Processing
1. **Shape Extraction**: Uses IfcOpenShell's `create_shape()` to extract geometry
2. **Vertex Processing**: Converts geometry vertices to VTK points
3. **Face Conversion**: Maps IFC faces to VTK cells (triangles)
4. **Mesh Creation**: Creates `vtkPolyData` from points and cells
5. **Visualization**: Maps data through `vtkPolyDataMapper` to actors

## Usage

### Selecting an Issue
1. Run a clash check to generate issues
2. Click on an issue in the "Issues / Clashes" list
3. The 3D viewer automatically loads and displays both conflicting elements

### Interacting with the 3D View
- **Look around (head rotate)**: Right-click and drag
- **Select**: Left-click
- **Zoom**: Scroll wheel or pinch
- **Pan**: Middle-click and drag
- **Reset View**: Automatically done when selecting a new issue

## Dependencies
- **VTK** (9.0+): 3D visualization
- **IfcOpenShell**: IFC geometry extraction
- **PySide6**: Qt GUI framework
- **NumPy**: Numerical operations

## Installation
```bash
pip install vtk ifcopenshell PySide6 numpy matplotlib
```

## Technical Details

### Fallback Behavior
If actual geometry extraction fails, the viewer will attempt to display a bounding box wireframe as a fallback, ensuring something is always visible.

### Performance
- Geometry is only loaded when an issue is selected
- Viewers are cleared before loading new geometry to minimize memory usage
- VTK handles efficient rendering of complex meshes

### Future Enhancements
Possible improvements:
- Transparency/opacity slider for overlapping geometry
- Edge highlighting for intersection detection
- Clipping planes to explore internal geometry
- Measurement tools
- Export 3D views as images or models
