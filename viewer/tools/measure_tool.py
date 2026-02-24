from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


MeasurePoint = Tuple[float, float, float]


class MeasureMode:
    SELECT = "select"
    DISTANCE = "distance"
    CLEARANCE = "clearance"
    ANGLE = "angle"
    CHAIN = "chain"


@dataclass
class MeasureToolState:
    mode: str = MeasureMode.SELECT
    pending_points: List[MeasurePoint] = field(default_factory=list)
    pending_guids: List[str] = field(default_factory=list)


class MeasureTool:
    """Small state machine for interactive measuring."""

    def __init__(self):
        self.state = MeasureToolState()

    @property
    def mode(self) -> str:
        return self.state.mode

    def set_mode(self, mode: str) -> None:
        if mode == self.state.mode:
            return
        self.state.mode = str(mode or MeasureMode.SELECT)
        self.reset_pending()

    def reset_pending(self) -> None:
        self.state.pending_points.clear()
        self.state.pending_guids.clear()

    def add_distance_point(self, point: Optional[MeasurePoint]) -> Optional[Tuple[MeasurePoint, MeasurePoint]]:
        if point is None:
            return None
        self.state.pending_points.append(point)
        if len(self.state.pending_points) < 2:
            return None
        p0, p1 = self.state.pending_points[-2], self.state.pending_points[-1]
        self.state.pending_points = [p1]
        return p0, p1

    def add_clearance_guid(self, guid: Optional[str]) -> Optional[Tuple[str, str]]:
        if not guid:
            return None
        if not self.state.pending_guids:
            self.state.pending_guids = [guid]
            return None
        if len(self.state.pending_guids) == 1:
            if guid == self.state.pending_guids[0]:
                return None
            self.state.pending_guids.append(guid)
        else:
            if guid == self.state.pending_guids[-1]:
                return None
            self.state.pending_guids = [self.state.pending_guids[-1], guid]
        return self.state.pending_guids[0], self.state.pending_guids[1]
