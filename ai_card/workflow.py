from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union


class AiStep(str, Enum):
    CREATED = "CREATED"
    RESPONSIBILITY = "RESPONSIBILITY"
    CONTEXT = "CONTEXT"
    RULE_BASIS = "RULE_BASIS"
    MOVEABILITY = "MOVEABILITY"
    HIGH_IMPACT = "HIGH_IMPACT"
    DECISION = "DECISION"
    APPLY = "APPLY"


STEP_ORDER: Tuple[AiStep, ...] = (
    AiStep.CREATED,
    AiStep.RESPONSIBILITY,
    AiStep.CONTEXT,
    AiStep.RULE_BASIS,
    AiStep.MOVEABILITY,
    AiStep.HIGH_IMPACT,
    AiStep.DECISION,
    AiStep.APPLY,
)

STEP_LABELS: Dict[AiStep, str] = {
    AiStep.CREATED: "1. Created",
    AiStep.RESPONSIBILITY: "2. Responsibility",
    AiStep.CONTEXT: "3. Context",
    AiStep.RULE_BASIS: "4. Rule basis",
    AiStep.MOVEABILITY: "5. Moveability",
    AiStep.HIGH_IMPACT: "6. High-impact",
    AiStep.DECISION: "7. Decision",
    AiStep.APPLY: "8. Apply/Export",
}


@dataclass
class AiCardState:
    issue_id: str
    active_step: AiStep = AiStep.CREATED
    completed_steps: Set[AiStep] = field(default_factory=set)
    pinned_assumptions: List[str] = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)
    chosen_owner: Optional[str] = None
    chosen_fix_id: Optional[str] = None
    last_updated_ts: float = field(default_factory=time.time)


@dataclass(frozen=True)
class AiHeader:
    title: str
    status_badge: str
    severity_badge: str


@dataclass(frozen=True)
class AiChip:
    label: str
    value: str


@dataclass(frozen=True)
class AiStepperItem:
    step: AiStep
    label: str
    status: str  # active | completed | blocked | pending
    blocked_reason: str = ""


@dataclass(frozen=True)
class Action:
    action_id: str
    label: str
    enabled: bool = True
    reason: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FixCandidate:
    fix_id: str
    target_element: str  # "A" | "B"
    type: str  # translate | rotate | reroute_stub
    vector: Tuple[float, float, float]  # meters
    solves_issue_ids: List[str]
    creates_new_issue_estimate: int
    min_clearance_after: float
    violates_constraints: List[str]
    score: float
    explanation: List[str]
    citations: List[str] = field(default_factory=list)
    preview_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FixCandidateSummary:
    fix_id: str
    target_element: str
    solves_text: str
    creates_text: str
    move_text: str
    clearance_text: str
    violations_text: str
    why: List[str]
    score: float


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    text: str
    done: bool
    action: Optional[Action] = None


@dataclass(frozen=True)
class BlockChecklist:
    kind: str
    id: str
    title: str
    items: List[ChecklistItem]


@dataclass(frozen=True)
class BlockSummary:
    kind: str
    id: str
    title: str
    bullets: List[str]


@dataclass(frozen=True)
class TableRow:
    k: str
    v: str


@dataclass(frozen=True)
class BlockTable:
    kind: str
    id: str
    title: str
    rows: List[TableRow]


@dataclass(frozen=True)
class BlockFixList:
    kind: str
    id: str
    title: str
    fixes: List[FixCandidateSummary]


@dataclass(frozen=True)
class CitationItem:
    source_id: str
    title: str
    ref: str
    excerpt: str


@dataclass(frozen=True)
class BlockCitations:
    kind: str
    id: str
    title: str
    citations: List[CitationItem]


@dataclass(frozen=True)
class AssumptionItem:
    id: str
    text: str
    accepted: bool


@dataclass(frozen=True)
class BlockAssumptions:
    kind: str
    id: str
    title: str
    assumptions: List[AssumptionItem]


@dataclass(frozen=True)
class BlockTrace:
    kind: str
    id: str
    title: str
    trace_preview_lines: List[str]


Block = Union[
    BlockChecklist,
    BlockSummary,
    BlockTable,
    BlockFixList,
    BlockCitations,
    BlockAssumptions,
    BlockTrace,
]


@dataclass(frozen=True)
class AiTraceNode:
    id: str
    kind: str
    title: str
    data: Dict[str, Any]
    children: List["AiTraceNode"]
    ok: bool
    warnings: List[str]
    errors: List[str]


@dataclass(frozen=True)
class AiTrace:
    trace_version: int
    issue_id: str
    timestamp: float
    inputs: Dict[str, Any]
    steps: List[AiTraceNode]


@dataclass(frozen=True)
class AiDiagnostics:
    confidence: float
    confidence_breakdown: Dict[str, float]
    missing: List[str]


@dataclass(frozen=True)
class AiCardPayload:
    header: AiHeader
    chips: List[AiChip]
    stepper: List[AiStepperItem]
    blocks: List[Block]
    actions: List[Action]
    diagnostics: AiDiagnostics
    trace: AiTrace

    def to_dict(self) -> Dict[str, Any]:
        return jsonable(self)


def jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    return value


class AiCardStateStore:
    VERSION = 1

    def __init__(self, project_root: Path):
        self._project_root = Path(project_root)
        self._path = self._project_root / ".ponker" / "ai_card_state.json"

    @property
    def path(self) -> Path:
        return self._path

    def load_state(self, issue_id: str) -> AiCardState:
        issue_key = str(issue_id or "").strip()
        if not issue_key:
            issue_key = "__no_issue__"
        payload = self._read()
        entry = (payload.get("issues") or {}).get(issue_key)
        if not isinstance(entry, dict):
            return AiCardState(issue_id=issue_key)
        return self._state_from_dict(issue_key, entry)

    def save_state(self, state: AiCardState) -> None:
        payload = self._read()
        payload.setdefault("version", self.VERSION)
        issues = payload.setdefault("issues", {})
        if not isinstance(issues, dict):
            issues = {}
            payload["issues"] = issues
        issue_key = str(state.issue_id or "__no_issue__")
        state.last_updated_ts = float(time.time())
        issues[issue_key] = self._state_to_dict(state)
        self._write(payload)

    def patch_state(self, issue_id: str, **changes: Any) -> AiCardState:
        state = self.load_state(issue_id)
        for key, value in changes.items():
            if hasattr(state, key):
                setattr(state, key, value)
        state.last_updated_ts = float(time.time())
        self.save_state(state)
        return state

    def _read(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {"version": self.VERSION, "issues": {}}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"version": self.VERSION, "issues": {}}
            return data
        except Exception:
            return {"version": self.VERSION, "issues": {}}

    def _write(self, payload: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    def _state_from_dict(self, issue_key: str, data: Dict[str, Any]) -> AiCardState:
        completed_raw = data.get("completed_steps")
        completed: Set[AiStep] = set()
        if isinstance(completed_raw, Sequence):
            for item in completed_raw:
                try:
                    completed.add(AiStep(str(item)))
                except Exception:
                    continue
        active_raw = str(data.get("active_step") or AiStep.CREATED.value)
        try:
            active_step = AiStep(active_raw)
        except Exception:
            active_step = AiStep.CREATED
        pinned = [str(v) for v in list(data.get("pinned_assumptions") or []) if str(v).strip()]
        notes_raw = data.get("notes") or {}
        notes = {str(k): str(v) for k, v in notes_raw.items()} if isinstance(notes_raw, dict) else {}
        return AiCardState(
            issue_id=issue_key,
            active_step=active_step,
            completed_steps=completed,
            pinned_assumptions=pinned,
            notes=notes,
            chosen_owner=str(data.get("chosen_owner")) if data.get("chosen_owner") else None,
            chosen_fix_id=str(data.get("chosen_fix_id")) if data.get("chosen_fix_id") else None,
            last_updated_ts=float(data.get("last_updated_ts") or time.time()),
        )

    @staticmethod
    def _state_to_dict(state: AiCardState) -> Dict[str, Any]:
        return {
            "issue_id": str(state.issue_id),
            "active_step": state.active_step.value,
            "completed_steps": [step.value for step in sorted(state.completed_steps, key=lambda s: STEP_ORDER.index(s))],
            "pinned_assumptions": [str(v) for v in list(state.pinned_assumptions or []) if str(v).strip()],
            "notes": {str(k): str(v) for k, v in dict(state.notes or {}).items()},
            "chosen_owner": str(state.chosen_owner) if state.chosen_owner else None,
            "chosen_fix_id": str(state.chosen_fix_id) if state.chosen_fix_id else None,
            "last_updated_ts": float(state.last_updated_ts),
        }
