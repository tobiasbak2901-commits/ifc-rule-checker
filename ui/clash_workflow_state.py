from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass
class ClashLastRun:
    time: float = 0.0
    results_count: int = 0


@dataclass
class ClashWorkflowState:
    activeStep: str = "setup"  # setup | results | fix
    selectedTestId: str = ""
    lastRun: Optional[ClashLastRun] = None
    selectedClashId: str = ""

    def as_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "activeStep": str(self.activeStep),
            "selectedTestId": str(self.selectedTestId),
            "selectedClashId": str(self.selectedClashId),
        }
        payload["lastRun"] = asdict(self.lastRun) if self.lastRun is not None else None
        return payload
