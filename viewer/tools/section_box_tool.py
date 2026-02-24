from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


Bounds = Tuple[float, float, float, float, float, float]


@dataclass
class SectionBoxState:
    enabled: bool = False
    bounds: Optional[Bounds] = None
    padding: float = 0.2


class SectionBoxTool:
    """Keeps section-box state and common fit/reset helpers."""

    def __init__(self):
        self.state = SectionBoxState()

    def set_enabled(self, enabled: bool) -> None:
        self.state.enabled = bool(enabled)

    def set_bounds(self, bounds: Optional[Bounds]) -> Optional[Bounds]:
        self.state.bounds = tuple(bounds) if bounds else None
        return self.state.bounds

    def clear(self) -> None:
        self.state.enabled = False
        self.state.bounds = None

    def fit_to_bounds(self, bounds: Bounds, padding: float = 0.2) -> Bounds:
        minx, maxx, miny, maxy, minz, maxz = bounds
        pad = max(0.0, float(padding))
        dx = max(1e-6, maxx - minx)
        dy = max(1e-6, maxy - miny)
        dz = max(1e-6, maxz - minz)
        px = dx * pad
        py = dy * pad
        pz = dz * pad
        fitted = (minx - px, maxx + px, miny - py, maxy + py, minz - pz, maxz + pz)
        self.state.bounds = fitted
        return fitted
