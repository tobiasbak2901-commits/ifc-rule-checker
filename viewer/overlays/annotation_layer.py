from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


Vec3 = Tuple[float, float, float]


class AnnotationLayer:
    """Overlay manager for dimension lines/labels."""

    def __init__(self, viewer):
        self.viewer = viewer
        self._entries: Dict[str, List[object]] = {}

    def clear(self):
        for actors in list(self._entries.values()):
            for actor in actors:
                self.viewer.remove_actor(actor)
        self._entries.clear()

    def remove(self, entry_id: str):
        actors = self._entries.pop(str(entry_id), [])
        for actor in actors:
            self.viewer.remove_actor(actor)

    def add_dimension(
        self,
        entry_id: str,
        p0: Vec3,
        p1: Vec3,
        label: str,
        color: Tuple[float, float, float] = (1.0, 0.25, 0.58),
        marker_radius: float = 0.014,
    ):
        key = str(entry_id)
        self.remove(key)
        line = self.viewer.add_line(p0, p1, color, pickable=False)
        m0 = self.viewer.add_marker(p0, color, radius=marker_radius, pickable=False)
        m1 = self.viewer.add_marker(p1, color, radius=marker_radius, pickable=False)
        mid = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, (p0[2] + p1[2]) * 0.5)
        text = self.viewer.add_text3d(mid, label, color, scale=0.015, pickable=False)
        self._entries[key] = [line, m0, m1, text]

    def add_hud_tag(
        self,
        entry_id: str,
        point: Vec3,
        lines: Iterable[str],
        color: Tuple[float, float, float] = (0.89, 0.91, 0.95),
    ):
        key = str(entry_id)
        self.remove(key)
        text = " | ".join(str(v) for v in lines if str(v).strip())
        if not text:
            return
        actor = self.viewer.add_text3d(point, text, color, scale=0.012, pickable=False)
        self._entries[key] = [actor]
