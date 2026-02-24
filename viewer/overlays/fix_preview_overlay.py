from __future__ import annotations

from typing import List, Optional, Tuple
import math

from models import CandidateFix, Issue, SourceCitation


Vec3 = Tuple[float, float, float]


class FixPreviewOverlay:
    """Virtual fix preview: original + moved ghost, delta arrow, and short why-panel."""

    def __init__(self, viewer, add_geometry_fn):
        self.viewer = viewer
        self._add_geometry_fn = add_geometry_fn
        self._actors: List[object] = []

    def clear(self):
        for actor in list(self._actors):
            self.viewer.remove_actor(actor)
        self._actors.clear()

    def _track(self, actor):
        if actor is None:
            return
        try:
            actor.PickableOff()
        except Exception:
            pass
        self._actors.append(actor)

    def _add_arrow(self, p0: Vec3, p1: Vec3, color: Tuple[float, float, float]) -> None:
        self._track(self.viewer.add_line(p0, p1, color, pickable=False))
        vx = float(p1[0] - p0[0])
        vy = float(p1[1] - p0[1])
        vz = float(p1[2] - p0[2])
        length = math.sqrt(vx * vx + vy * vy + vz * vz)
        if length <= 1e-9:
            return
        ux, uy, uz = vx / length, vy / length, vz / length
        # Use a stable perpendicular basis for arrowhead wings.
        if abs(ux) < 0.9:
            px, py, pz = 1.0, 0.0, 0.0
        else:
            px, py, pz = 0.0, 1.0, 0.0
        wx = uy * pz - uz * py
        wy = uz * px - ux * pz
        wz = ux * py - uy * px
        w_len = math.sqrt(wx * wx + wy * wy + wz * wz)
        if w_len <= 1e-9:
            return
        wx, wy, wz = wx / w_len, wy / w_len, wz / w_len
        head_len = min(max(length * 0.2, 0.01), 0.08)
        wing = head_len * 0.45
        base = (
            p1[0] - ux * head_len,
            p1[1] - uy * head_len,
            p1[2] - uz * head_len,
        )
        left = (
            base[0] + wx * wing,
            base[1] + wy * wing,
            base[2] + wz * wing,
        )
        right = (
            base[0] - wx * wing,
            base[1] - wy * wing,
            base[2] - wz * wing,
        )
        self._track(self.viewer.add_line(p1, left, color, pickable=False))
        self._track(self.viewer.add_line(p1, right, color, pickable=False))

    def show(
        self,
        issue: Optional[Issue],
        fix: CandidateFix,
        metrics_text: str,
        rule_text: str,
        citations: List[SourceCitation],
    ) -> bool:
        self.clear()
        if not fix:
            return False
        guid = str(fix.params.get("guid") or "")
        if not guid:
            return False
        dx = float(fix.params.get("dx", 0.0))
        dy = float(fix.params.get("dy", 0.0))
        dz = float(fix.params.get("dz", 0.0))
        src_color = (1.0, 0.45, 0.08)
        moved_color = (0.25, 0.95, 0.45)
        self._track(self._add_geometry_fn(guid, src_color, opacity=0.38, translate=None, render=False))
        self._track(self._add_geometry_fn(guid, moved_color, opacity=0.35, translate=(dx, dy, dz), render=False))

        if issue and issue.p_a and issue.p_b:
            anchor = issue.p_a
            if guid and issue.guid_b and str(guid) == str(issue.guid_b):
                anchor = issue.p_b
            moved_p0 = (anchor[0] + dx, anchor[1] + dy, anchor[2] + dz)
            self._add_arrow(anchor, moved_p0, moved_color)
            self._track(self.viewer.add_marker(anchor, src_color, radius=0.013, pickable=False))
            self._track(self.viewer.add_marker(moved_p0, moved_color, radius=0.013, pickable=False))
            delta_text = f"Flyt: {fix.params.get('d_mm', 0.0):.0f} mm"
            self._track(self.viewer.add_text3d(moved_p0, delta_text, moved_color, scale=0.013))

            info = f"{metrics_text} | {rule_text}"
            info_point: Vec3 = (moved_p0[0], moved_p0[1], moved_p0[2] + 0.05)
            self._track(self.viewer.add_text3d(info_point, info, (0.92, 0.94, 0.98), scale=0.011))
        self.viewer.render()
        return True
