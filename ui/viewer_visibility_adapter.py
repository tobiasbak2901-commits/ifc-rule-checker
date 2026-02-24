from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from ui.viewer import VTK3DViewer


class ViewerVisibilityAdapter:
    def __init__(
        self,
        viewer: Optional[VTK3DViewer],
        *,
        focus_callback: Optional[Callable[[List[str]], None]] = None,
        show_all_callback: Optional[Callable[[], None]] = None,
    ):
        self._viewer = viewer
        self._focus_callback = focus_callback
        self._show_all_callback = show_all_callback

    @staticmethod
    def _normalize_keys(keys: Sequence[str]) -> List[str]:
        normalized: List[str] = []
        for value in list(keys or []):
            guid = str(value or "").strip()
            if not guid or guid in normalized:
                continue
            normalized.append(guid)
        return normalized

    def hide(self, keys: List[str]) -> None:
        if self._viewer is None:
            return
        guids = self._normalize_keys(keys)
        if not guids:
            return
        self._viewer.hide_guids(guids)

    def showOnly(self, keys: List[str]) -> None:
        if self._viewer is None:
            return
        guids = self._normalize_keys(keys)
        if not guids:
            return
        self._viewer.isolate_guids(guids, transparent=False)

    def showAll(self) -> None:
        if self._show_all_callback is not None:
            self._show_all_callback()
            return
        if self._viewer is not None:
            self._viewer.show_all()

    def setTransparency(self, keys: List[str], alpha: float) -> None:
        if self._viewer is None:
            return
        guids = self._normalize_keys(keys)
        if not guids:
            return
        raw = float(alpha)
        if raw > 1.0:
            raw = raw / 100.0
        self._viewer.set_opacity_for_guids(guids, raw)

    def focus(self, keys: List[str]) -> None:
        guids = self._normalize_keys(keys)
        if not guids:
            return
        if self._focus_callback is not None:
            self._focus_callback(guids)
            return
        if self._viewer is None:
            return
        bounds: Optional[Tuple[float, float, float, float, float, float]] = None
        for guid in guids:
            current = self._viewer.get_bounds_for_guid(guid, preferred_tags=("ifc",))
            if current is None:
                current = self._viewer.get_bounds_for_guid(guid)
            if current is None:
                continue
            if bounds is None:
                bounds = tuple(float(v) for v in current)
                continue
            bounds = (
                min(bounds[0], float(current[0])),
                max(bounds[1], float(current[1])),
                min(bounds[2], float(current[2])),
                max(bounds[3], float(current[3])),
                min(bounds[4], float(current[4])),
                max(bounds[5], float(current[5])),
            )
        if bounds is not None:
            self._viewer.focus_on_bounds(bounds)

