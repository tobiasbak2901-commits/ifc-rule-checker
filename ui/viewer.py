from __future__ import annotations

from typing import Dict, List, Sequence, Tuple
import math

from PySide6 import QtCore, QtGui, QtWidgets
import numpy as np
from vtkmodules.vtkRenderingCore import vtkActor, vtkRenderer, vtkRenderWindow, vtkPolyDataMapper, vtkFollower
from vtkmodules.vtkRenderingFreeType import vtkVectorText
from vtkmodules.vtkCommonCore import vtkIdList, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray, vtkPlanes
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkLineSource, vtkSphereSource
from vtkmodules.vtkFiltersCore import vtkTubeFilter, vtkImplicitPolyDataDistance
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import vtkPropPicker
from vtkmodules.vtkRenderingOpenGL2 import vtkGenericOpenGLRenderWindow

import vtkmodules.qt

_use_generic_rw = False
vtkmodules.qt.QVTKRWIBase = "QWidget"
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from ui.theme import DARK_THEME, hex_to_rgb


class RmbOrbitInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, renderer, pivot_provider=None):
        super().__init__()
        self._renderer = renderer
        self._pivot_provider = pivot_provider
        self._active_mode = None
        self._navigation_mode = "orbit"

    def set_navigation_mode(self, mode: str):
        normalized = str(mode or "").strip().lower()
        if normalized in ("orbit", "pan", "zoom"):
            self._navigation_mode = normalized
        else:
            self._navigation_mode = "orbit"

    def OnLeftButtonDown(self):
        # Disable orbiting on left-click; selection is handled separately.
        pass

    def OnLeftButtonUp(self):
        pass

    def OnRightButtonDown(self):
        iren = self.GetInteractor()
        if not iren:
            return
        x, y = iren.GetEventPosition()
        self.FindPokedRenderer(x, y)
        self.GrabFocus(self.EventCallbackCommand)
        target_mode = "rotate"
        if iren.GetShiftKey():
            target_mode = "pan"
        elif iren.GetControlKey():
            target_mode = "dolly"
        elif self._navigation_mode == "pan":
            target_mode = "pan"
        elif self._navigation_mode == "zoom":
            target_mode = "dolly"

        self._active_mode = target_mode
        if self._active_mode == "pan":
            self.StartPan()
            return
        if self._active_mode == "dolly":
            self.StartDolly()
            return
        pivot = None
        if self._pivot_provider:
            pivot = self._pivot_provider(x, y)
        if pivot is None and self._renderer:
            cam = self._renderer.GetActiveCamera()
            if cam:
                pivot = cam.GetFocalPoint()
        if pivot is not None and self._renderer:
            cam = self._renderer.GetActiveCamera()
            if cam:
                cam.SetFocalPoint(float(pivot[0]), float(pivot[1]), float(pivot[2]))
        self.StartRotate()

    def OnRightButtonUp(self):
        if self._active_mode == "pan":
            self.EndPan()
        elif self._active_mode == "dolly":
            self.EndDolly()
        elif self._active_mode == "rotate":
            self.EndRotate()
        self._active_mode = None
        self.ReleaseFocus()

    def OnMiddleButtonDown(self):
        self._active_mode = "pan"
        self.StartPan()

    def OnMiddleButtonUp(self):
        if self._active_mode == "pan":
            self.EndPan()
        self._active_mode = None

    def OnMouseMove(self):
        super().OnMouseMove()


class VTK3DViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewerCard")
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._frame = QtWidgets.QFrame(self)
        self._frame.setObjectName("ViewerFrame")
        self._frame.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self._frame_layout = QtWidgets.QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._frame)

        self.iren = None
        self.render_window = None
        self.renderer = None
        self._initialized = False
        self._actors: List[vtkActor] = []
        self._actor_meta: Dict[vtkActor, dict] = {}
        self._pick_callback = None
        self._picker = None
        self._interactor_style = None
        self._selected_actor: vtkActor | None = None
        self._selected_actors: List[vtkActor] = []
        self._highlighted_actors: List[vtkActor] = []
        self._measurement_actors: List[vtkActor] = []
        self._manual_pivot: Tuple[float, float, float] | None = None
        self._double_click_callback = None
        self._context_menu_callback = None
        self._rmb_press_pos: Tuple[float, float] | None = None
        self._rmb_dragging = False
        self._rmb_drag_threshold = 4.0
        self._drag_callback = None
        self._drag_meta: dict | None = None
        self._drag_last_pos: Tuple[float, float] | None = None
        self._isolation_state: Dict[vtkActor, Tuple[int, float]] = {}
        self._surface_cache: Dict[str, dict] = {}
        self._section_clipping_planes: vtkPlanes | None = None
        self._section_box_bounds: Tuple[float, float, float, float, float, float] | None = None
        self._section_box_actor: vtkActor | None = None
        self._active_tool_id = "measure_select"
        self._navigation_mode = "orbit"
        self._scene_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._debug_helpers_visible = True
        self._debug_helper_actors: List[vtkActor] = []
        self._debug_cube_actor: vtkActor | None = None
        self._debug_render_mode = False
        self._colors = {
            "a": (1.0, 0.2, 0.2),
            "b": (0.2, 0.2, 1.0),
            "intersection": (1.0, 1.0, 0.0),
        }

    def _create_vtk(self):
        if self.iren is not None:
            return
        # Create the interactor directly under the frame to avoid native
        # reparenting quirks that can manifest as extra top-level windows.
        self.iren = QVTKRenderWindowInteractor(self._frame)
        self.render_window = self.iren.GetRenderWindow()
        self.render_window.SetMultiSamples(0)
        self._frame_layout.addWidget(self.iren)
        self.iren.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.iren.installEventFilter(self)

        self.renderer = vtkRenderer()
        self.renderer.SetGradientBackground(True)
        # Keep viewport in the same dark design language as the UI shell.
        bg = hex_to_rgb(DARK_THEME.colors.background)
        bg2 = hex_to_rgb(DARK_THEME.colors.panel)
        self.renderer.SetBackground(bg[0] / 255.0, bg[1] / 255.0, bg[2] / 255.0)
        self.renderer.SetBackground2(bg2[0] / 255.0, bg2[1] / 255.0, bg2[2] / 255.0)
        self.render_window.AddRenderer(self.renderer)
        self._interactor_style = RmbOrbitInteractorStyle(self.renderer, self._get_orbit_pivot)
        self.iren.SetInteractorStyle(self._interactor_style)
        self._interactor_style.set_navigation_mode(self._navigation_mode)
        self._apply_tool_cursor()
        self._setup_picking()

    def _init_vtk(self):
        if self._initialized:
            return
        if self.iren is None:
            self._create_vtk()
        self._initialized = True
        self.iren.Initialize()
        self._ensure_debug_helpers()
        self.render_window.Render()

    def showEvent(self, event):
        super().showEvent(event)
        self._create_vtk()
        self._init_vtk()
        QtCore.QTimer.singleShot(0, self._post_show_resize)

    def eventFilter(self, obj, event):
        if obj is self.iren:
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                if not self.iren:
                    return True
                pos = event.position()
                x = int(pos.x())
                y = int(pos.y())
                y = max(0, min(self.iren.height() - 1, y))
                self._handle_double_click(x, self.iren.height() - 1 - y)
                return True
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                pos = event.position()
                x = int(pos.x())
                y = int(pos.y())
                actor, _pick_pos = self._pick_actor_at(x, y)
                meta = self._actor_meta.get(actor) if actor else None
                if isinstance(meta, dict) and bool(meta.get("draggable")):
                    self._drag_meta = dict(meta)
                    self._drag_last_pos = (float(pos.x()), float(pos.y()))
                    return True
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.RightButton:
                pos = event.position()
                self._rmb_press_pos = (float(pos.x()), float(pos.y()))
                self._rmb_dragging = False
            elif event.type() == QtCore.QEvent.MouseMove:
                pos = event.position()
                if self._drag_meta and self._drag_last_pos:
                    dx = float(pos.x()) - float(self._drag_last_pos[0])
                    dy = float(pos.y()) - float(self._drag_last_pos[1])
                    if abs(dx) > 0.01 or abs(dy) > 0.01:
                        delta_world = self._screen_delta_to_world(dx, dy)
                        handled = False
                        if callable(self._drag_callback):
                            try:
                                handled = bool(self._drag_callback(dict(self._drag_meta), delta_world))
                            except Exception:
                                handled = False
                        self._drag_last_pos = (float(pos.x()), float(pos.y()))
                        if handled:
                            return True
                if self._rmb_press_pos:
                    dx = float(pos.x()) - self._rmb_press_pos[0]
                    dy = float(pos.y()) - self._rmb_press_pos[1]
                    if (dx * dx + dy * dy) >= (self._rmb_drag_threshold * self._rmb_drag_threshold):
                        self._rmb_dragging = True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                if self._drag_meta is not None:
                    self._drag_meta = None
                    self._drag_last_pos = None
                    return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.RightButton:
                if self._rmb_press_pos and not self._rmb_dragging:
                    mods = event.modifiers()
                    if not (mods & (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier)):
                        self._handle_context_menu(event)
                self._rmb_press_pos = None
                self._rmb_dragging = False
        return super().eventFilter(obj, event)

    def _post_show_resize(self):
        if not self.render_window or not self.iren:
            return
        if self._frame:
            self.iren.resize(self._frame.size())
        self.render_window.Render()

    def clear(self):
        if not self.renderer:
            return
        self.clear_highlight()
        self.clear_measurement()
        self.clear_section_box(render=False)
        for actor in self._actors:
            self.renderer.RemoveActor(actor)
        self._actors.clear()
        self._actor_meta.clear()
        self._surface_cache.clear()
        self._isolation_state.clear()
        self._manual_pivot = None
        self._scene_offset = (0.0, 0.0, 0.0)
        self.render_window.Render()

    def remove_actor(self, actor: vtkActor, *, render: bool = True):
        if not self.renderer or actor is None:
            return
        self.renderer.RemoveActor(actor)
        if actor in self._actors:
            self._actors.remove(actor)
        meta = self._actor_meta.pop(actor, None)
        if actor in self._highlighted_actors:
            self._highlighted_actors.remove(actor)
        if self._selected_actor is actor:
            self._selected_actor = None
        if actor in self._isolation_state:
            self._isolation_state.pop(actor, None)
        if meta:
            guid = meta.get("guid")
            if guid and guid in self._surface_cache:
                self._surface_cache.pop(guid, None)
        if render and self.render_window:
            self.render_window.Render()

    def clear_tagged_actors(self, scene_tag: str, *, render: bool = True) -> int:
        removed = 0
        tag = str(scene_tag or "")
        for actor in list(self._actors):
            meta = self._actor_meta.get(actor) or {}
            if str(meta.get("scene_tag") or "") != tag:
                continue
            self.remove_actor(actor, render=False)
            removed += 1
        if render and self.render_window:
            self.render_window.Render()
        return removed

    def count_tagged_actors(self, scene_tag: str) -> int:
        tag = str(scene_tag or "")
        return sum(
            1
            for actor in self._actors
            if str((self._actor_meta.get(actor) or {}).get("scene_tag") or "") == tag
        )

    def total_scene_children(self) -> int:
        if not self.renderer:
            return 0
        view_props = self.renderer.GetViewProps()
        if not view_props:
            return 0
        return int(view_props.GetNumberOfItems())

    def get_scene_offset(self) -> Tuple[float, float, float]:
        return self._scene_offset

    def set_scene_offset(self, offset: Tuple[float, float, float] | None):
        new_offset = (
            float((offset or (0.0, 0.0, 0.0))[0]),
            float((offset or (0.0, 0.0, 0.0))[1]),
            float((offset or (0.0, 0.0, 0.0))[2]),
        )
        old_offset = self._scene_offset
        if (
            abs(old_offset[0] - new_offset[0]) < 1e-12
            and abs(old_offset[1] - new_offset[1]) < 1e-12
            and abs(old_offset[2] - new_offset[2]) < 1e-12
        ):
            return
        delta = (
            old_offset[0] - new_offset[0],
            old_offset[1] - new_offset[1],
            old_offset[2] - new_offset[2],
        )
        for actor in list(self._actors):
            meta = self._actor_meta.get(actor) or {}
            if self._meta_apply_scene_offset(meta):
                actor.AddPosition((float(delta[0]), float(delta[1]), float(delta[2])))
        self._scene_offset = new_offset
        if self.render_window:
            self.render_window.Render()

    def world_to_scene_point(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        ox, oy, oz = self._scene_offset
        return (point[0] - ox, point[1] - oy, point[2] - oz)

    def world_to_screen_point(
        self,
        point: Tuple[float, float, float],
        *,
        apply_scene_offset: bool = True,
    ) -> Tuple[int, int, float, bool] | None:
        if not self.renderer or not self.iren:
            return None
        px, py, pz = float(point[0]), float(point[1]), float(point[2])
        if apply_scene_offset:
            px, py, pz = self.world_to_scene_point((px, py, pz))
        self.renderer.SetWorldPoint(px, py, pz, 1.0)
        self.renderer.WorldToDisplay()
        dx, dy, dz = self.renderer.GetDisplayPoint()
        x = int(round(float(dx)))
        y = int(round(float(self.iren.height()) - float(dy)))
        visible = (
            0 <= x < max(1, int(self.iren.width()))
            and 0 <= y < max(1, int(self.iren.height()))
            and 0.0 <= float(dz) <= 1.0
        )
        return (x, y, float(dz), bool(visible))

    def world_to_scene_bounds(self, bounds: Tuple[float, float, float, float, float, float]):
        minx, maxx, miny, maxy, minz, maxz = (
            float(bounds[0]),
            float(bounds[1]),
            float(bounds[2]),
            float(bounds[3]),
            float(bounds[4]),
            float(bounds[5]),
        )
        ox, oy, oz = self._scene_offset
        return (minx - ox, maxx - ox, miny - oy, maxy - oy, minz - oz, maxz - oz)

    def scene_to_world_bounds(self, bounds: Tuple[float, float, float, float, float, float]):
        minx, maxx, miny, maxy, minz, maxz = (
            float(bounds[0]),
            float(bounds[1]),
            float(bounds[2]),
            float(bounds[3]),
            float(bounds[4]),
            float(bounds[5]),
        )
        ox, oy, oz = self._scene_offset
        return (minx + ox, maxx + ox, miny + oy, maxy + oy, minz + oz, maxz + oz)

    def _meta_apply_scene_offset(self, meta: dict | None) -> bool:
        if not isinstance(meta, dict):
            return True
        return bool(meta.get("apply_scene_offset", True))

    def _create_line_actor(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        color: Tuple[float, float, float],
        *,
        line_width: float = 1.0,
        opacity: float = 1.0,
    ) -> vtkActor:
        points = vtkPoints()
        points.InsertNextPoint(float(p0[0]), float(p0[1]), float(p0[2]))
        points.InsertNextPoint(float(p1[0]), float(p1[1]), float(p1[2]))
        cells = vtkCellArray()
        ids = vtkIdList()
        ids.SetNumberOfIds(2)
        ids.SetId(0, 0)
        ids.SetId(1, 1)
        cells.InsertNextCell(ids)
        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(cells)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(float(opacity))
        actor.GetProperty().SetLineWidth(float(line_width))
        actor.PickableOff()
        return actor

    def _create_grid_actor(
        self,
        *,
        half_extent: float = 5.0,
        step: float = 1.0,
        color: Tuple[float, float, float] = (0.35, 0.38, 0.44),
    ) -> vtkActor:
        points = vtkPoints()
        cells = vtkCellArray()
        n = max(1, int(round(float(half_extent) / max(float(step), 1e-6))))
        for i in range(-n, n + 1):
            t = float(i) * float(step)
            for p0, p1 in (
                ((-half_extent, t, 0.0), (half_extent, t, 0.0)),
                ((t, -half_extent, 0.0), (t, half_extent, 0.0)),
            ):
                a = points.InsertNextPoint(float(p0[0]), float(p0[1]), float(p0[2]))
                b = points.InsertNextPoint(float(p1[0]), float(p1[1]), float(p1[2]))
                ids = vtkIdList()
                ids.SetNumberOfIds(2)
                ids.SetId(0, int(a))
                ids.SetId(1, int(b))
                cells.InsertNextCell(ids)
        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(cells)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(0.35)
        actor.GetProperty().SetLineWidth(1.0)
        actor.PickableOff()
        return actor

    def _ensure_debug_helpers(self):
        if not self.renderer or self._debug_helper_actors:
            return

        grid_actor = self._create_grid_actor()
        x_axis = self._create_line_actor((0.0, 0.0, 0.0), (1.5, 0.0, 0.0), (1.0, 0.2, 0.2), line_width=2.4)
        y_axis = self._create_line_actor((0.0, 0.0, 0.0), (0.0, 1.5, 0.0), (0.2, 1.0, 0.2), line_width=2.4)
        z_axis = self._create_line_actor((0.0, 0.0, 0.0), (0.0, 0.0, 1.5), (0.2, 0.6, 1.0), line_width=2.4)

        cube = vtkCubeSource()
        cube.SetCenter(0.0, 0.0, 0.125)
        cube.SetXLength(0.25)
        cube.SetYLength(0.25)
        cube.SetZLength(0.25)
        cube_mapper = vtkPolyDataMapper()
        cube_mapper.SetInputConnection(cube.GetOutputPort())
        cube_actor = vtkActor()
        cube_actor.SetMapper(cube_mapper)
        cube_actor.GetProperty().SetColor(1.0, 0.9, 0.18)
        cube_actor.GetProperty().SetOpacity(0.95)
        cube_actor.PickableOff()
        self._debug_cube_actor = cube_actor

        self._debug_helper_actors = [grid_actor, x_axis, y_axis, z_axis, cube_actor]
        for actor in self._debug_helper_actors:
            self.renderer.AddActor(actor)
            actor.SetVisibility(1 if self._debug_helpers_visible else 0)

    def set_debug_helpers_visible(self, enabled: bool):
        self._debug_helpers_visible = bool(enabled)
        self._ensure_debug_helpers()
        for actor in self._debug_helper_actors:
            actor.SetVisibility(1 if self._debug_helpers_visible else 0)
        if self.render_window:
            self.render_window.Render()

    def debug_helpers_visible(self) -> bool:
        return bool(self._debug_helpers_visible)

    def debug_cube_visible(self) -> bool:
        if self._debug_cube_actor is None:
            return False
        return bool(self._debug_cube_actor.GetVisibility())

    def set_debug_render_mode(self, enabled: bool):
        self._debug_render_mode = bool(enabled)
        for actor, meta in self._actor_meta.items():
            if actor in self._highlighted_actors:
                continue
            self._restore_actor_base_visual(actor, meta)
        if self.render_window:
            self.render_window.Render()

    def is_debug_render_mode(self) -> bool:
        return bool(self._debug_render_mode)

    def _restore_actor_base_visual(self, actor: vtkActor, meta: dict | None):
        if actor is None:
            return
        prop = actor.GetProperty()
        if self._debug_render_mode and isinstance(meta, dict) and meta.get("guid"):
            prop.SetColor(1.0, 0.65, 0.12)
            prop.SetOpacity(1.0)
            prop.BackfaceCullingOff()
            return
        if isinstance(meta, dict):
            base_color = meta.get("base_color")
            base_opacity = meta.get("base_opacity")
            if base_color:
                prop.SetColor(*base_color)
            if base_opacity is not None:
                prop.SetOpacity(float(base_opacity))
        prop.BackfaceCullingOff()

    def render(self):
        if self.render_window:
            self.render_window.Render()

    def add_geometry_from_shape(
        self,
        shape,
        color: Tuple[float, float, float],
        opacity: float = 1.0,
        translate: Tuple[float, float, float] | None = None,
        render: bool = True,
        meta: dict | None = None,
    ):
        self._init_vtk()
        verts_np = np.array(shape.geometry.verts).reshape(-1, 3)
        if translate:
            verts_np = verts_np + np.array(translate)
        vertices = tuple(float(v) for v in verts_np.reshape(-1))
        faces = shape.geometry.faces
        tris: List[Tuple[int, int, int]] = []
        n_verts = len(verts_np)
        if hasattr(faces, "shape") and len(getattr(faces, "shape", ())) == 2:
            faces_iter = faces.tolist()
            for face in faces_iter:
                if len(face) < 3:
                    continue
                idx = [int(v) for v in face]
                if any(v < 0 or v >= n_verts for v in idx):
                    continue
                for t in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[t], idx[t + 1]))
        elif len(faces) > 0 and isinstance(faces[0], (list, tuple)):
            for face in faces:
                if len(face) < 3:
                    continue
                idx = [int(v) for v in face]
                if any(v < 0 or v >= n_verts for v in idx):
                    continue
                for t in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[t], idx[t + 1]))
        else:
            i = 0
            ok = True
            while i < len(faces):
                n = int(faces[i])
                i += 1
                if n < 3 or i + n > len(faces):
                    ok = False
                    break
                idx = [int(v) for v in faces[i : i + n]]
                i += n
                if any(v < 0 or v >= n_verts for v in idx):
                    ok = False
                    break
                for t in range(1, n - 1):
                    tris.append((idx[0], idx[t], idx[t + 1]))
            if not ok or not tris:
                tris.clear()
                for j in range(0, len(faces) - 2, 3):
                    a = int(faces[j])
                    b = int(faces[j + 1])
                    c = int(faces[j + 2])
                    if 0 <= a < n_verts and 0 <= b < n_verts and 0 <= c < n_verts:
                        tris.append((a, b, c))
        indices = tuple(i for tri in tris for i in tri)
        return self.add_mesh_geometry(
            vertices=vertices,
            indices=indices,
            color=color,
            opacity=opacity,
            render=render,
            meta=meta,
        )

    def add_mesh_geometry(
        self,
        vertices: Sequence[float],
        indices: Sequence[int],
        color: Tuple[float, float, float],
        opacity: float = 1.0,
        render: bool = True,
        meta: dict | None = None,
    ):
        self._init_vtk()
        if not vertices or len(vertices) < 9 or (len(vertices) % 3) != 0:
            return None
        if not indices or len(indices) < 3:
            return None
        raw_indices = [int(v) for v in indices]
        points = vtkPoints()
        for i in range(0, len(vertices), 3):
            try:
                points.InsertNextPoint((float(vertices[i]), float(vertices[i + 1]), float(vertices[i + 2])))
            except Exception as exc:
                raise RuntimeError(f"InsertNextPoint failed at vertex {i // 3}: {exc}") from exc
        n_verts = len(vertices) // 3

        def _build_cells(index_values: Sequence[int]) -> vtkCellArray:
            local_cells = vtkCellArray()
            for j in range(0, len(index_values) - 2, 3):
                a = int(index_values[j])
                b = int(index_values[j + 1])
                c = int(index_values[j + 2])
                if a < 0 or b < 0 or c < 0 or a >= n_verts or b >= n_verts or c >= n_verts:
                    continue
                try:
                    ids = vtkIdList()
                    ids.SetNumberOfIds(3)
                    ids.SetId(0, int(a))
                    ids.SetId(1, int(b))
                    ids.SetId(2, int(c))
                    local_cells.InsertNextCell(ids)
                except Exception as exc:
                    raise RuntimeError(f"BuildCell failed for tri ({a}, {b}, {c}): {exc}") from exc
            return local_cells

        cells = _build_cells(raw_indices)
        if cells.GetNumberOfCells() <= 0:
            max_idx = max(raw_indices) if raw_indices else -1
            # Heuristic 1: IFC index stream sometimes references flattened coordinate indices.
            if max_idx >= n_verts and max_idx < len(vertices):
                coord_indices = [int(v) // 3 for v in raw_indices]
                cells = _build_cells(coord_indices)
            # Heuristic 2: one-based indexing.
            if cells.GetNumberOfCells() <= 0 and max_idx == n_verts:
                one_based = [int(v) - 1 for v in raw_indices]
                cells = _build_cells(one_based)
            # Heuristic 3: ignore index stream and fan out raw vertex triplets.
            if cells.GetNumberOfCells() <= 0 and n_verts >= 3:
                sequential = list(range(n_verts - (n_verts % 3)))
                cells = _build_cells(sequential)
        if cells.GetNumberOfCells() <= 0:
            return None
        try:
            polydata = vtkPolyData()
            polydata.SetPoints(points)
            polydata.SetPolys(cells)
        except Exception as exc:
            raise RuntimeError(f"PolyData assembly failed: {exc}") from exc
        try:
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(polydata)
        except Exception as exc:
            raise RuntimeError(f"Mapper setup failed: {exc}") from exc
        try:
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor((float(color[0]), float(color[1]), float(color[2])))
            actor.GetProperty().SetOpacity(float(opacity))
            actor.GetProperty().BackfaceCullingOff()
            self._apply_active_clipping(actor)
            self.renderer.AddActor(actor)
        except Exception as exc:
            raise RuntimeError(f"Actor setup failed: {exc}") from exc
        self._actors.append(actor)
        if meta is None:
            meta = {}
        meta["polydata"] = polydata
        self._actor_meta[actor] = meta
        if self._meta_apply_scene_offset(meta):
            try:
                actor.AddPosition(
                    (
                        float(-self._scene_offset[0]),
                        float(-self._scene_offset[1]),
                        float(-self._scene_offset[2]),
                    )
                )
            except Exception as exc:
                raise RuntimeError(f"Actor offset failed: {exc}") from exc
        self._restore_actor_base_visual(actor, meta)
        if render:
            self.render_window.Render()
        return actor

    def add_aabb(
        self,
        bounds: Tuple[float, float, float, float, float, float],
        color: Tuple[float, float, float],
        opacity: float = 0.2,
        render: bool = True,
        meta: dict | None = None,
    ):
        self._init_vtk()
        minx, miny, minz, maxx, maxy, maxz = (
            float(bounds[0]),
            float(bounds[1]),
            float(bounds[2]),
            float(bounds[3]),
            float(bounds[4]),
            float(bounds[5]),
        )
        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        cz = (minz + maxz) / 2.0
        cube = vtkCubeSource()
        cube.SetCenter((float(cx), float(cy), float(cz)))
        cube.SetXLength(float(max(maxx - minx, 1e-6)))
        cube.SetYLength(float(max(maxy - miny, 1e-6)))
        cube.SetZLength(float(max(maxz - minz, 1e-6)))
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor((float(color[0]), float(color[1]), float(color[2])))
        actor.GetProperty().SetOpacity(float(opacity))
        self._apply_active_clipping(actor)
        self.renderer.AddActor(actor)
        self._actors.append(actor)
        if meta:
            self._actor_meta[actor] = meta
        if self._meta_apply_scene_offset(meta):
            actor.AddPosition(
                (
                    float(-self._scene_offset[0]),
                    float(-self._scene_offset[1]),
                    float(-self._scene_offset[2]),
                )
            )
        self._restore_actor_base_visual(actor, meta)
        if render:
            self.render_window.Render()
        return actor

    def add_marker(
        self,
        point: Tuple[float, float, float],
        color: Tuple[float, float, float],
        radius: float = 0.05,
        pickable: bool = True,
    ):
        self._init_vtk()
        sphere = vtkSphereSource()
        sphere.SetCenter(point[0], point[1], point[2])
        sphere.SetRadius(radius)
        sphere.SetThetaResolution(16)
        sphere.SetPhiResolution(16)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.SetPickable(1 if pickable else 0)
        self._apply_active_clipping(actor)
        self.renderer.AddActor(actor)
        self._actors.append(actor)
        actor.AddPosition(-self._scene_offset[0], -self._scene_offset[1], -self._scene_offset[2])
        self.render_window.Render()
        return actor

    def add_line(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        color: Tuple[float, float, float],
        pickable: bool = True,
    ):
        self._init_vtk()
        points = vtkPoints()
        points.InsertNextPoint(p0[0], p0[1], p0[2])
        points.InsertNextPoint(p1[0], p1[1], p1[2])
        cells = vtkCellArray()
        ids = vtkIdList()
        ids.SetNumberOfIds(2)
        ids.SetId(0, 0)
        ids.SetId(1, 1)
        cells.InsertNextCell(ids)
        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(cells)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetLineWidth(3.0)
        actor.SetPickable(1 if pickable else 0)
        self._apply_active_clipping(actor)
        self.renderer.AddActor(actor)
        self._actors.append(actor)
        actor.AddPosition(-self._scene_offset[0], -self._scene_offset[1], -self._scene_offset[2])
        self.render_window.Render()
        return actor

    def add_text3d(
        self,
        point: Tuple[float, float, float],
        text: str,
        color: Tuple[float, float, float],
        scale: float = 0.08,
        pickable: bool = False,
    ):
        self._init_vtk()
        text_src = vtkVectorText()
        text_src.SetText(text)
        text_src.Update()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(text_src.GetOutputPort())
        actor = vtkFollower()
        actor.SetMapper(mapper)
        actor.SetPickable(1 if pickable else 0)
        actor.GetProperty().SetColor(*color)
        actor.SetScale(scale, scale, scale)
        if self.renderer:
            actor.SetCamera(self.renderer.GetActiveCamera())
        bounds = text_src.GetOutput().GetBounds()
        if bounds and len(bounds) == 6:
            width = bounds[1] - bounds[0]
            height = bounds[3] - bounds[2]
            actor.SetPosition(
                point[0] - (width * scale * 0.5),
                point[1] - (height * scale * 0.5),
                point[2],
            )
        else:
            actor.SetPosition(point[0], point[1], point[2])
        actor.RotateZ(0.0)
        self._apply_active_clipping(actor)
        self.renderer.AddActor(actor)
        self._actors.append(actor)
        actor.AddPosition(-self._scene_offset[0], -self._scene_offset[1], -self._scene_offset[2])
        self.render_window.Render()
        return actor

    def add_tube(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        radius: float,
        color: Tuple[float, float, float],
        opacity: float = 1.0,
        render: bool = True,
        meta: dict | None = None,
    ):
        self._init_vtk()
        line = vtkLineSource()
        line.SetPoint1(float(p0[0]), float(p0[1]), float(p0[2]))
        line.SetPoint2(float(p1[0]), float(p1[1]), float(p1[2]))
        tube = vtkTubeFilter()
        tube.SetInputConnection(line.GetOutputPort())
        tube.SetRadius(float(max(radius, 0.001)))
        tube.SetNumberOfSides(16)
        tube.CappingOn()
        tube.Update()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(tube.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(opacity)
        actor.GetProperty().BackfaceCullingOff()
        self._apply_active_clipping(actor)
        self.renderer.AddActor(actor)
        self._actors.append(actor)
        if meta is None:
            meta = {}
        meta["polydata"] = tube.GetOutput()
        self._actor_meta[actor] = meta
        if self._meta_apply_scene_offset(meta):
            actor.AddPosition(-self._scene_offset[0], -self._scene_offset[1], -self._scene_offset[2])
        self._restore_actor_base_visual(actor, meta)
        if render:
            self.render_window.Render()
        return actor

    def _apply_active_clipping(self, actor: vtkActor):
        if actor is None:
            return
        mapper = actor.GetMapper()
        if not mapper:
            return
        if self._section_clipping_planes is not None:
            mapper.SetClippingPlanes(self._section_clipping_planes)
        else:
            mapper.RemoveAllClippingPlanes()

    def _update_section_box_actor(self):
        if not self.renderer:
            return
        if self._section_box_actor is not None:
            self.renderer.RemoveActor(self._section_box_actor)
            self._section_box_actor = None
        if not self._section_box_bounds:
            return
        minx, maxx, miny, maxy, minz, maxz = self._section_box_bounds
        cube = vtkCubeSource()
        cube.SetCenter((minx + maxx) * 0.5, (miny + maxy) * 0.5, (minz + maxz) * 0.5)
        cube.SetXLength(max(maxx - minx, 1e-6))
        cube.SetYLength(max(maxy - miny, 1e-6))
        cube.SetZLength(max(maxz - minz, 1e-6))
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        actor.GetProperty().SetRepresentationToWireframe()
        actor.GetProperty().SetLineWidth(1.6)
        actor.GetProperty().SetColor(1.0, 0.28, 0.62)
        actor.GetProperty().SetOpacity(0.85)
        self.renderer.AddActor(actor)
        self._section_box_actor = actor

    def set_section_box(
        self,
        bounds: Tuple[float, float, float, float, float, float] | None,
        render: bool = True,
        apply_scene_offset: bool = True,
    ):
        self._init_vtk()
        if bounds and apply_scene_offset:
            bounds = self.world_to_scene_bounds(bounds)
        self._section_box_bounds = (
            (
                float(bounds[0]),
                float(bounds[1]),
                float(bounds[2]),
                float(bounds[3]),
                float(bounds[4]),
                float(bounds[5]),
            )
            if bounds
            else None
        )
        if self._section_box_bounds is None:
            self._section_clipping_planes = None
        else:
            planes = vtkPlanes()
            planes.SetBounds(*self._section_box_bounds)
            self._section_clipping_planes = planes
        for actor in self._actors:
            self._apply_active_clipping(actor)
        self._update_section_box_actor()
        if render and self.render_window:
            self.render_window.Render()

    def clear_section_box(self, render: bool = True):
        self._section_box_bounds = None
        self._section_clipping_planes = None
        for actor in self._actors:
            self._apply_active_clipping(actor)
        if self.renderer and self._section_box_actor is not None:
            self.renderer.RemoveActor(self._section_box_actor)
            self._section_box_actor = None
        if render and self.render_window:
            self.render_window.Render()

    def get_scene_bounds(self):
        bounds = None
        for actor in self._actors:
            if actor is None or not actor.GetVisibility():
                continue
            cur = actor.GetBounds()
            if not cur or len(cur) != 6 or any(v is None for v in cur):
                continue
            if bounds is None:
                bounds = [cur[0], cur[1], cur[2], cur[3], cur[4], cur[5]]
            else:
                bounds[0] = min(bounds[0], cur[0])
                bounds[1] = max(bounds[1], cur[1])
                bounds[2] = min(bounds[2], cur[2])
                bounds[3] = max(bounds[3], cur[3])
                bounds[4] = min(bounds[4], cur[4])
                bounds[5] = max(bounds[5], cur[5])
        return tuple(bounds) if bounds else None

    def set_pick_callback(self, callback):
        self._pick_callback = callback

    def set_double_click_callback(self, callback):
        self._double_click_callback = callback

    def set_context_menu_callback(self, callback):
        self._context_menu_callback = callback

    def set_drag_callback(self, callback):
        self._drag_callback = callback

    def set_manual_pivot(self, pivot: Tuple[float, float, float] | None):
        self._manual_pivot = pivot

    def _setup_picking(self):
        if self._picker is not None:
            return
        self._picker = vtkPropPicker()
        if self.iren:
            self.iren.AddObserver("LeftButtonPressEvent", self._on_left_click, 1.0)

    def set_navigation_mode(self, mode: str):
        normalized = str(mode or "").strip().lower()
        if normalized not in ("orbit", "pan", "zoom"):
            normalized = "orbit"
        self._navigation_mode = normalized
        if self._interactor_style:
            self._interactor_style.set_navigation_mode(normalized)
        if self._active_tool_id in ("orbit", "pan", "zoom"):
            self._active_tool_id = normalized
        self._apply_tool_cursor()

    def set_active_tool(self, tool_id: str):
        normalized = str(tool_id or "").strip().lower() or "measure_select"
        self._active_tool_id = normalized
        if normalized in ("orbit", "pan", "zoom"):
            self.set_navigation_mode(normalized)
            return
        self._apply_tool_cursor()

    def get_active_tool(self) -> str:
        return self._active_tool_id

    def _apply_tool_cursor(self):
        if not self.iren:
            return
        tool = self._active_tool_id
        if tool == "orbit":
            shape = QtCore.Qt.OpenHandCursor
        elif tool == "pan":
            shape = QtCore.Qt.SizeAllCursor
        elif tool == "zoom":
            shape = QtCore.Qt.SizeVerCursor
        elif tool == "measure_distance":
            shape = QtCore.Qt.CrossCursor
        elif tool in ("measure_clearance", "measure_min"):
            shape = QtCore.Qt.PointingHandCursor
        elif tool == "section_box":
            shape = QtCore.Qt.SizeAllCursor
        else:
            shape = QtCore.Qt.ArrowCursor
        self.iren.setCursor(QtGui.QCursor(shape))

    def _pick_actor_at(self, x: int, y: int):
        if not self._picker or not self.renderer or not self.iren:
            return None, None
        y = max(0, min(self.iren.height() - 1, y))
        y_vtk = self.iren.height() - 1 - y
        self._picker.Pick(int(x), int(y_vtk), 0, self.renderer)
        actor = self._picker.GetActor()
        pick_pos = self._picker.GetPickPosition() if actor else None
        return actor, pick_pos

    def _screen_delta_to_world(self, dx: float, dy: float) -> Tuple[float, float, float]:
        if not self.renderer or not self.iren:
            return (0.0, 0.0, 0.0)
        cam = self.renderer.GetActiveCamera()
        if not cam:
            return (0.0, 0.0, 0.0)
        view_h = max(float(self.iren.height()), 1.0)
        if cam.GetParallelProjection():
            world_per_pixel = (2.0 * float(cam.GetParallelScale())) / view_h
        else:
            pos = np.array(cam.GetPosition(), dtype=float)
            focal = np.array(cam.GetFocalPoint(), dtype=float)
            distance = float(np.linalg.norm(focal - pos))
            if distance <= 1e-9:
                distance = 1.0
            view_angle = math.radians(max(1e-3, float(cam.GetViewAngle())))
            world_per_pixel = (2.0 * distance * math.tan(view_angle * 0.5)) / view_h

        pos = np.array(cam.GetPosition(), dtype=float)
        focal = np.array(cam.GetFocalPoint(), dtype=float)
        up = np.array(cam.GetViewUp(), dtype=float)
        view_dir = focal - pos
        norm_view = float(np.linalg.norm(view_dir))
        if norm_view <= 1e-9:
            return (0.0, 0.0, 0.0)
        view_dir = view_dir / norm_view
        right = np.cross(view_dir, up)
        norm_right = float(np.linalg.norm(right))
        if norm_right <= 1e-9:
            return (0.0, 0.0, 0.0)
        right = right / norm_right
        up_dir = np.cross(right, view_dir)
        norm_up = float(np.linalg.norm(up_dir))
        if norm_up <= 1e-9:
            return (0.0, 0.0, 0.0)
        up_dir = up_dir / norm_up
        move = (right * float(dx) * world_per_pixel) + (up_dir * float(-dy) * world_per_pixel)
        return (float(move[0]), float(move[1]), float(move[2]))

    def _handle_context_menu(self, event):
        if not self._context_menu_callback or not self.iren:
            return
        pos = event.position()
        x = int(pos.x())
        y = int(pos.y())
        actor, pick_pos = self._pick_actor_at(x, y)
        meta = self._actor_meta.get(actor) if actor else None
        global_pos = self.iren.mapToGlobal(QtCore.QPoint(x, y))
        self._context_menu_callback(global_pos, meta, pick_pos)

    def _get_actor_center(self, actor: vtkActor | None):
        if actor is None:
            return None
        bounds = actor.GetBounds()
        if not bounds or len(bounds) != 6:
            return None
        minx, maxx, miny, maxy, minz, maxz = bounds
        if any(v is None for v in bounds):
            return None
        return ((minx + maxx) / 2.0, (miny + maxy) / 2.0, (minz + maxz) / 2.0)

    def _get_orbit_pivot(self, x: int, y: int):
        if self._manual_pivot:
            return self._manual_pivot
        if self._selected_actor:
            center = self._get_actor_center(self._selected_actor)
            if center:
                return center
        if self._picker and self.renderer:
            self._picker.Pick(x, y, 0, self.renderer)
            actor = self._picker.GetActor()
            if actor:
                return self._picker.GetPickPosition()
        if self.renderer:
            cam = self.renderer.GetActiveCamera()
            if cam:
                return cam.GetFocalPoint()
        return None

    def _handle_double_click(self, x: int, y: int):
        if not self._picker or not self.renderer:
            return
        self._picker.Pick(x, y, 0, self.renderer)
        actor = self._picker.GetActor()
        pick_pos = None
        if actor:
            pick_pos = self._picker.GetPickPosition()
        if pick_pos:
            self._manual_pivot = (float(pick_pos[0]), float(pick_pos[1]), float(pick_pos[2]))
            cam = self.renderer.GetActiveCamera()
            if cam:
                cam.SetFocalPoint(*self._manual_pivot)
                self.renderer.ResetCameraClippingRange()
        handled = False
        if self._double_click_callback:
            meta = self._actor_meta.get(actor) if actor else None
            handled = bool(self._double_click_callback(meta, pick_pos))
        if not handled and actor:
            bounds = actor.GetBounds()
            if bounds and len(bounds) == 6 and not any(v is None for v in bounds):
                self.focus_on_bounds(bounds, apply_scene_offset=False)

    def _on_left_click(self, obj, event):
        if not self._picker or not self.renderer or not self.iren:
            return
        x, y = self.iren.GetEventPosition()
        shift = bool(self.iren.GetShiftKey())
        self._picker.Pick(x, y, 0, self.renderer)
        actor = self._picker.GetActor()
        if actor and actor in self._actor_meta:
            self._highlight_actor(actor, additive=shift)
            if self._pick_callback:
                self._pick_callback(self._actor_meta[actor], self._picker.GetPickPosition(), shift)
        else:
            if self._pick_callback:
                self._pick_callback(None, None, shift)
            if not shift:
                self.clear_highlight()
        style = self.iren.GetInteractorStyle()
        if style:
            style.OnLeftButtonDown()

    def _highlight_actor(self, actor: vtkActor, additive: bool = False):
        if actor is None:
            return
        if additive and actor in self._highlighted_actors:
            self._remove_highlight(actor)
            if actor in self._selected_actors:
                self._selected_actors.remove(actor)
            if self._selected_actor is actor:
                self._selected_actor = self._selected_actors[-1] if self._selected_actors else None
            if self.render_window:
                self.render_window.Render()
            return
        if not additive:
            self.clear_highlight()
        self._selected_actor = actor
        if actor not in self._selected_actors:
            self._selected_actors.append(actor)
        self._apply_highlight(actor, (1.0, 0.85, 0.2))
        if self.render_window:
            self.render_window.Render()

    def _apply_highlight(self, actor: vtkActor, color):
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(1.0)
        actor.GetProperty().EdgeVisibilityOn()
        actor.GetProperty().SetEdgeColor(1.0, 0.6, 0.0)
        actor.GetProperty().SetLineWidth(2.0)
        self._highlighted_actors.append(actor)

    def _remove_highlight(self, actor: vtkActor):
        meta = self._actor_meta.get(actor, {})
        self._restore_actor_base_visual(actor, meta)
        actor.GetProperty().EdgeVisibilityOff()
        if actor in self._highlighted_actors:
            self._highlighted_actors.remove(actor)

    def clear_highlight(self):
        if not self._highlighted_actors:
            self._selected_actor = None
            self._selected_actors = []
            return
        for actor in self._highlighted_actors:
            meta = self._actor_meta.get(actor, {})
            self._restore_actor_base_visual(actor, meta)
            actor.GetProperty().EdgeVisibilityOff()
        self._highlighted_actors.clear()
        self._selected_actor = None
        self._selected_actors = []
        if self.render_window:
            self.render_window.Render()

    def get_actor_for_guid(self, guid: str):
        preferred = self.get_bounds_for_guid(guid, preferred_tags=("ifc",))
        if preferred is not None:
            for actor, meta in self._actor_meta.items():
                if meta.get("guid") != guid:
                    continue
                if str(meta.get("scene_tag") or "") == "ifc":
                    return actor
        for actor, meta in self._actor_meta.items():
            if meta.get("guid") == guid:
                return actor
        return None

    def get_bounds_for_guid(
        self,
        guid: str,
        *,
        preferred_tags: tuple[str, ...] | None = None,
    ) -> Tuple[float, float, float, float, float, float] | None:
        candidates: List[Tuple[vtkActor, dict]] = []
        for actor, meta in self._actor_meta.items():
            if str(meta.get("guid") or "") != str(guid or ""):
                continue
            candidates.append((actor, meta))
        if not candidates:
            return None

        if preferred_tags:
            tags = {str(tag) for tag in preferred_tags if str(tag).strip()}
            preferred = [
                (actor, meta)
                for actor, meta in candidates
                if str(meta.get("scene_tag") or "") in tags
            ]
            if preferred:
                candidates = preferred

        combined: List[float] | None = None
        for actor, _meta in candidates:
            b = actor.GetBounds()
            if not b or len(b) != 6:
                continue
            try:
                cur = [float(v) for v in b]
            except Exception:
                continue
            if any(not math.isfinite(v) for v in cur):
                continue
            if cur[1] < cur[0] or cur[3] < cur[2] or cur[5] < cur[4]:
                continue
            if combined is None:
                combined = cur
            else:
                combined[0] = min(combined[0], cur[0])
                combined[1] = max(combined[1], cur[1])
                combined[2] = min(combined[2], cur[2])
                combined[3] = max(combined[3], cur[3])
                combined[4] = min(combined[4], cur[4])
                combined[5] = max(combined[5], cur[5])
        return tuple(combined) if combined is not None else None

    def select_by_guids(self, guids: List[str]):
        if not guids:
            self.clear_highlight()
            return
        self.clear_highlight()
        for guid in guids:
            actor = self.get_actor_for_guid(guid)
            if not actor:
                continue
            if self._selected_actor is None:
                self._selected_actor = actor
            if actor not in self._selected_actors:
                self._selected_actors.append(actor)
            self._apply_highlight(actor, (1.0, 0.85, 0.2))
        if self.render_window:
            self.render_window.Render()

    def hide_guids(self, guids: List[str]):
        if not self.renderer:
            return
        self._init_vtk()
        self._store_isolation_state()
        for guid in list(guids or []):
            actor = self.get_actor_for_guid(str(guid or ""))
            if actor:
                actor.SetVisibility(0)
        if self.render_window:
            self.render_window.Render()

    def set_opacity_for_guids(self, guids: List[str], opacity: float):
        if not self.renderer:
            return
        self._init_vtk()
        self._store_isolation_state()
        safe_opacity = max(0.0, min(1.0, float(opacity)))
        for guid in list(guids or []):
            actor = self.get_actor_for_guid(str(guid or ""))
            if not actor:
                continue
            actor.SetVisibility(1)
            actor.GetProperty().SetOpacity(safe_opacity)
        if self.render_window:
            self.render_window.Render()

    def _store_isolation_state(self):
        for actor in self._actors:
            if actor not in self._isolation_state:
                self._isolation_state[actor] = (
                    int(actor.GetVisibility()),
                    float(actor.GetProperty().GetOpacity()),
                )

    def isolate_guids(self, guids: List[str], transparent: bool = False):
        if not self.renderer or not guids:
            return
        self._init_vtk()
        self._store_isolation_state()
        keep = set(guids)
        for actor in self._actors:
            meta = self._actor_meta.get(actor, {})
            guid = meta.get("guid")
            if guid in keep:
                actor.SetVisibility(1)
                if actor not in self._highlighted_actors:
                    base_opacity = meta.get("base_opacity")
                    if base_opacity is not None:
                        actor.GetProperty().SetOpacity(float(base_opacity))
            else:
                if transparent:
                    actor.SetVisibility(1)
                    base_opacity = meta.get("base_opacity")
                    if base_opacity is None:
                        base_opacity = actor.GetProperty().GetOpacity()
                    faded = max(0.04, min(float(base_opacity) * 0.15, 0.15))
                    actor.GetProperty().SetOpacity(faded)
                else:
                    actor.SetVisibility(0)
        if self.render_window:
            self.render_window.Render()

    def show_all(self):
        if not self.renderer:
            return
        if self._isolation_state:
            restored = set()
            for actor, (visible, opacity) in self._isolation_state.items():
                if actor:
                    actor.SetVisibility(int(visible))
                    actor.GetProperty().SetOpacity(float(opacity))
                    restored.add(actor)
            for actor in self._actors:
                if actor not in restored:
                    actor.SetVisibility(1)
            self._isolation_state.clear()
        else:
            for actor in self._actors:
                actor.SetVisibility(1)
                if actor not in self._highlighted_actors:
                    meta = self._actor_meta.get(actor, {})
                    base_opacity = meta.get("base_opacity")
                    if base_opacity is not None:
                        actor.GetProperty().SetOpacity(float(base_opacity))
        if self.render_window:
            self.render_window.Render()

    def get_polydata_for_guid(self, guid: str):
        for actor, meta in self._actor_meta.items():
            if meta.get("guid") == guid:
                polydata = meta.get("polydata")
                if polydata is not None:
                    return polydata
        return None

    def _get_surface_cache(self, guid: str):
        polydata = self.get_polydata_for_guid(guid)
        if not polydata:
            return None
        poly_id = id(polydata)
        cached = self._surface_cache.get(guid)
        if cached and cached.get("poly_id") == poly_id:
            return cached
        dist = vtkImplicitPolyDataDistance()
        dist.SetInput(polydata)
        points = polydata.GetPoints()
        entry = {
            "poly_id": poly_id,
            "polydata": polydata,
            "distance": dist,
            "points": points,
            "n_points": polydata.GetNumberOfPoints() if points else 0,
        }
        self._surface_cache[guid] = entry
        return entry

    def compute_surface_distance(self, guid_a: str, guid_b: str, early_stop: float = 1e-6):
        cache_a = self._get_surface_cache(guid_a)
        cache_b = self._get_surface_cache(guid_b)
        if not cache_a or not cache_b:
            return None
        if cache_a["n_points"] == 0 or cache_b["n_points"] == 0:
            return None

        min_dist = None
        best_a = None
        best_b = None
        overlap = False

        def scan(points, n_points, dist_func, source_is_a: bool):
            nonlocal min_dist, best_a, best_b, overlap
            for i in range(n_points):
                p = points.GetPoint(i)
                closest = [0.0, 0.0, 0.0]
                dist = dist_func.EvaluateFunctionAndGetClosestPoint(p, closest)
                if dist <= 0.0:
                    overlap = True
                dist_abs = abs(dist)
                if min_dist is None or dist_abs < min_dist:
                    min_dist = dist_abs
                    if source_is_a:
                        best_a = p
                        best_b = (closest[0], closest[1], closest[2])
                    else:
                        best_a = (closest[0], closest[1], closest[2])
                        best_b = p
                if min_dist is not None and min_dist <= early_stop:
                    return True
            return False

        n_a = cache_a["n_points"]
        n_b = cache_b["n_points"]
        if n_a <= n_b:
            if scan(cache_a["points"], n_a, cache_b["distance"], True):
                pass
            else:
                scan(cache_b["points"], n_b, cache_a["distance"], False)
        else:
            if scan(cache_b["points"], n_b, cache_a["distance"], False):
                pass
            else:
                scan(cache_a["points"], n_a, cache_b["distance"], True)

        if min_dist is None or best_a is None or best_b is None:
            return None
        return {
            "distance": float(min_dist),
            "p0": (float(best_a[0]), float(best_a[1]), float(best_a[2])),
            "p1": (float(best_b[0]), float(best_b[1]), float(best_b[2])),
            "overlap": overlap,
            "method": "Surface",
        }

    def clear_measurement(self):
        if not self._measurement_actors:
            return
        if self.renderer:
            for actor in self._measurement_actors:
                self.renderer.RemoveActor(actor)
                if actor in self._actors:
                    self._actors.remove(actor)
                self._actor_meta.pop(actor, None)
                self._isolation_state.pop(actor, None)
            self._measurement_actors.clear()
            if self.render_window:
                self.render_window.Render()

    def show_measurement(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        color: Tuple[float, float, float],
        marker_radius: float = 0.05,
        label: str | None = None,
    ):
        self.clear_measurement()
        line = self.add_line(p0, p1, color, pickable=False)
        m0 = self.add_marker(p0, color, radius=marker_radius, pickable=False)
        m1 = self.add_marker(p1, color, radius=marker_radius, pickable=False)
        self._measurement_actors = [line, m0, m1]
        if label:
            mid = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, (p0[2] + p1[2]) * 0.5)
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            dz = p1[2] - p0[2]
            length = (dx * dx + dy * dy + dz * dz) ** 0.5
            scale = max(length / 3.0, 1e-6)
            text_actor = self.add_text3d(
                mid,
                label,
                color,
                scale=scale,
            )
            self._measurement_actors.append(text_actor)

    def highlight_guids(self, guid_colors: Dict[str, Tuple[float, float, float]]):
        if not guid_colors:
            self.clear_highlight()
            return
        self.clear_highlight()
        for actor, meta in self._actor_meta.items():
            guid = meta.get("guid")
            if guid and guid in guid_colors:
                self._apply_highlight(actor, guid_colors[guid])
        if self.render_window:
            self.render_window.Render()

    def get_camera_state(self) -> Dict[str, object] | None:
        if not self.renderer:
            return None
        cam = self.renderer.GetActiveCamera()
        if not cam:
            return None
        position = cam.GetPosition()
        target = cam.GetFocalPoint()
        if not position or not target:
            return None
        zoom: float | None
        if cam.GetParallelProjection():
            zoom = float(cam.GetParallelScale())
        else:
            zoom = None
        return {
            "position": (float(position[0]), float(position[1]), float(position[2])),
            "target": (float(target[0]), float(target[1]), float(target[2])),
            "zoom": zoom,
        }

    def set_camera(self, position, direction, up, orthogonal=False, scale=None, apply_scene_offset: bool = True):
        if not self.renderer:
            return
        px, py, pz = position[0], position[1], position[2]
        if apply_scene_offset:
            px, py, pz = self.world_to_scene_point((px, py, pz))
        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(px, py, pz)
        focal = (
            px + direction[0],
            py + direction[1],
            pz + direction[2],
        )
        cam.SetFocalPoint(focal[0], focal[1], focal[2])
        cam.SetViewUp(up[0], up[1], up[2])
        cam.SetParallelProjection(bool(orthogonal))
        if orthogonal and scale:
            cam.SetParallelScale(scale)
        self.renderer.ResetCameraClippingRange()
        if self.render_window:
            self.render_window.Render()

    def set_camera_clipping(self, near_val: float, far_val: float):
        if not self.renderer:
            return
        cam = self.renderer.GetActiveCamera()
        near_clamp = max(0.01, float(near_val))
        far_clamp = max(near_clamp + 1.0, float(far_val))
        cam.SetClippingRange(near_clamp, far_clamp)
        if self.render_window:
            self.render_window.Render()

    def frame_bounds(
        self,
        bounds: Tuple[float, float, float, float, float, float],
        *,
        apply_scene_offset: bool = True,
        near_val: float | None = None,
        far_val: float | None = None,
    ):
        self._init_vtk()
        if not self.renderer:
            return
        bounds = (
            float(bounds[0]),
            float(bounds[1]),
            float(bounds[2]),
            float(bounds[3]),
            float(bounds[4]),
            float(bounds[5]),
        )
        if apply_scene_offset:
            bounds = self.world_to_scene_bounds(bounds)
        minx, maxx, miny, maxy, minz, maxz = bounds
        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        cz = (minz + maxz) / 2.0
        dx = maxx - minx
        dy = maxy - miny
        dz = maxz - minz
        diagonal = max(1e-9, (dx * dx + dy * dy + dz * dz) ** 0.5)
        unit = 1.0 / (3.0 ** 0.5)
        dist = max(diagonal * 1.2, 1.0)
        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(cx + unit * dist, cy + unit * dist, cz + unit * dist)
        cam.SetFocalPoint(cx, cy, cz)
        cam.SetViewUp(0, 0, 1)
        if near_val is not None and far_val is not None:
            self.set_camera_clipping(float(near_val), float(far_val))
        else:
            self.renderer.ResetCameraClippingRange()
        self._manual_pivot = (cx, cy, cz)
        self.render_window.Render()

    def focus_on_bounds(
        self,
        bounds: Tuple[float, float, float, float, float, float],
        *,
        apply_scene_offset: bool = True,
    ):
        self.frame_bounds(bounds, apply_scene_offset=apply_scene_offset)

    def focus_on_point(self, point: Tuple[float, float, float], radius: float = 1.0):
        x, y, z = point
        self.focus_on_bounds(
            (x - radius, x + radius, y - radius, y + radius, z - radius, z + radius),
            apply_scene_offset=True,
        )

    def flash_guid(self, guid: str, flashes: int = 3, interval_ms: int = 120):
        actor = self.get_actor_for_guid(guid)
        if not actor:
            return
        meta = self._actor_meta.get(actor, {})
        prop = actor.GetProperty()
        base_color = tuple(prop.GetColor())
        base_edge = int(prop.GetEdgeVisibility())
        base_line = float(prop.GetLineWidth())
        total_steps = max(1, int(flashes) * 2)

        def _tick(step: int):
            if actor not in self._actor_meta:
                return
            on = step % 2 == 0
            if on:
                prop.SetColor(1.0, 1.0, 0.2)
                prop.EdgeVisibilityOn()
                prop.SetLineWidth(max(2.0, base_line))
            else:
                self._restore_actor_base_visual(actor, meta)
                if base_edge:
                    prop.EdgeVisibilityOn()
                else:
                    prop.EdgeVisibilityOff()
                prop.SetLineWidth(base_line)
            if self.render_window:
                self.render_window.Render()
            if step + 1 < total_steps:
                QtCore.QTimer.singleShot(max(30, int(interval_ms)), lambda: _tick(step + 1))
            else:
                self._restore_actor_base_visual(actor, meta)
                prop.SetColor(base_color[0], base_color[1], base_color[2])
                if base_edge:
                    prop.EdgeVisibilityOn()
                else:
                    prop.EdgeVisibilityOff()
                prop.SetLineWidth(base_line)
                if self.render_window:
                    self.render_window.Render()

        _tick(0)
