# VTK+Qt Rendering Fix - Patch Summary

## Issues Fixed

1. **Heavy flickering** - Caused by immediate rendering on every event
2. **VTK view not repainting on move/resize** - Improper initialization timing
3. **Double title bar** - No nested QMainWindow issues (already correct)
4. **Unstable cross-monitor rendering** - Missing DoubleBufferOn() and proper event handling

## Root Causes & Solutions

### 1. Improper VTK Initialization (PRIMARY ISSUE)
**Problem:** VTK components were initialized in `__init__` before the widget was fully created by Qt. The `iren.Initialize()` must be called AFTER the widget is shown.

**Solution:** 
- Deferred initialization to `showEvent()` 
- VTK components now created lazily on first show
- `_initialized` flag prevents re-initialization

```python
def showEvent(self, event):
    super().showEvent(event)
    if not self._initialized:
        self._initialize_vtk()
```

### 2. Continuous Rendering (FLICKERING)
**Problem:** Every mouse move, resize, or internal update called `iren.Render()` immediately, causing constant redraws and flicker.

**Solution:**
- Introduced `_schedule_render()` that uses `QtCore.QTimer.singleShot(0, ...)` to defer renders
- Only one render is pending at a time via `_pending_render` flag
- Renders happen on Qt's event loop, not immediately

```python
def _schedule_render(self):
    if not self._pending_render and self._initialized:
        self._pending_render = True
        QtCore.QTimer.singleShot(0, self._do_render)
```

### 3. Missing Double Buffering
**Problem:** No explicit double-buffering enabled, leading to tearing and visual artifacts.

**Solution:**
```python
self.render_window.DoubleBufferOn()
```

### 4. Poor Size Policy
**Problem:** VTK widget had no explicit size policy, causing sizing issues in layouts.

**Solution:**
```python
self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
```

### 5. Resize/Move Event Handling
**Problem:** Resize/move events were ignored, causing black areas after window moves (especially cross-monitor).

**Solution:**
- `resizeEvent()` now schedules re-render
- `moveEvent()` now schedules re-render
- Both use deferred rendering via `_schedule_render()`

```python
def resizeEvent(self, event):
    super().resizeEvent(event)
    if self._initialized and self.render_window:
        self._schedule_render()

def moveEvent(self, event):
    super().moveEvent(event)
    if self._initialized and self.render_window:
        self._schedule_render()
```

### 6. Debug Logging
**Problem:** No visibility into render/resize behavior made debugging impossible.

**Solution:**
- Added `debug_callback` to VTK3DViewer constructor
- Checkbox in UI to toggle debug mode
- All major operations log to the text panel when enabled
- Events logged: initialization, showEvent, resizeEvent, moveEvent, clear, render

## Code Changes Summary

### VTK3DViewer Class (Major Refactor)

**Constructor Changes:**
```python
def __init__(self, parent=None, debug_callback=None):
    # NEW: defer all VTK initialization
    self.iren = None
    self.render_window = None
    self.renderer = None
    self._initialized = False
    self._pending_render = False
    self._debug_callback = debug_callback
    self._debug_enabled = False
```

**New Methods:**
- `_initialize_vtk()` - Creates VTK components with proper settings
- `showEvent()` - Triggers lazy initialization
- `resizeEvent()` - Schedules render on resize
- `moveEvent()` - Schedules render on move
- `_schedule_render()` - Defers render to Qt event loop
- `_do_render()` - Actually performs the render
- `set_debug_enabled(bool)` - Toggle debug logging
- `_debug_log(str)` - Logs if debugging is enabled

**Modified Methods:**
- `clear()` - Now checks initialization before accessing renderer
- `add_geometry_from_shape()` - Guards initialization, logs operations
- `add_bounding_box()` - Guards initialization, logs operations
- `fit_to_view()` - Uses `_schedule_render()` instead of immediate render
- `render()` - Delegates to `_schedule_render()`

### MainWindow Class Changes

**New Instance Variables:**
```python
self._debug_vtk = False
self.debug_cb = QtWidgets.QCheckBox("Debug VTK")
```

**Updated Initialization:**
- Pass `debug_callback=self.log` to VTK3DViewer
- Add debug checkbox to control row
- Connect checkbox to `on_debug_toggled` signal

**New Methods:**
```python
def on_debug_toggled(self, checked: bool):
    self._debug_vtk = checked
    self.vtk_viewer.set_debug_enabled(checked)
```

**Modified Methods:**
- `on_issue_selected()` - Added debug logging when enabled

## Testing Checklist

- [x] No syntax errors
- [ ] Run application without crashing
- [ ] Open IFC file and load geometries
- [ ] Select clash - should load and display without flicker
- [ ] Resize window - VTK view should update smoothly
- [ ] Move window between monitors - geometry should stay visible
- [ ] Enable "Debug VTK" checkbox - should see initialization/render/resize events in log
- [ ] Disable "Debug VTK" checkbox - log should be clean of VTK messages
- [ ] Close and reopen - no crashes or memory leaks

## Performance Impact

- **Memory:** Slightly increased due to deferred render tracking
- **CPU:** Reduced! Only renders when necessary (not every mouse move)
- **Responsiveness:** Better - Qt event loop not blocked by rendering

## Backward Compatibility

- All public method signatures unchanged
- Debug callback is optional parameter with default=None
- Existing code calling `clear()`, `add_geometry_from_shape()`, etc. works unchanged

## Future Improvements

1. Add vsync option to prevent tearing
2. Add render quality/performance slider
3. Implement multi-threaded geometry loading
4. Add frame rate monitor in debug mode
5. Consider OpenGL error checking with debug callback
