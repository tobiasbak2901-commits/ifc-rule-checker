from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Literal, Optional, Tuple


AiMode = Literal["Analyze", "Decisions", "Model"]
AiStatus = Literal["info", "warning", "error", "success"]
EvidenceKind = Literal["RULE", "STANDARD", "GEOMETRY", "MEASURE", "MODEL_PROPERTY", "ASSUMPTION"]


@dataclass(frozen=True)
class AiCamera:
    position: Tuple[float, float, float]
    target: Tuple[float, float, float]
    zoom: Optional[float] = None


@dataclass(frozen=True)
class AiSectionBox:
    enabled: bool
    bounds: Optional[Tuple[float, float, float, float, float, float]] = None


@dataclass(frozen=True)
class AiMeasurement:
    enabled: bool
    lastMeasure: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AiContext:
    activeMode: AiMode
    selectedElementIds: List[str]
    activeIssueId: Optional[str]
    searchSetA: Optional[str]
    searchSetB: Optional[str]
    camera: Optional[AiCamera]
    sectionBox: Optional[AiSectionBox]
    measurement: Optional[AiMeasurement]
    rulepackIdsActive: List[str]
    locale: str = "da-DK"

    def context_hash(self) -> str:
        payload = asdict(self)
        serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceLink:
    type: Literal["local", "url"]
    target: str


@dataclass(frozen=True)
class EvidenceItem:
    kind: EvidenceKind
    id: str
    title: str
    snippet: str
    link: Optional[EvidenceLink] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class AiAction:
    label: str
    actionId: str
    enabled: bool = True
    reason: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AiFactChip:
    label: str
    value: str


@dataclass(frozen=True)
class AiCardSection:
    id: Literal["why", "docs", "trace", "assumptions", "details"]
    title: str
    lines: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AiCardDebug:
    contextHash: str
    generatedAt: str
    model: Literal["rules", "llm", "hybrid"] = "rules"


@dataclass(frozen=True)
class AiCard:
    id: str
    title: str
    status: AiStatus
    summary: str
    bullets: List[str]
    recommendedActions: List[AiAction]
    citations: List[EvidenceItem]
    oneLineSummary: str = ""
    factChips: List[AiFactChip] = field(default_factory=list)
    sections: List[AiCardSection] = field(default_factory=list)
    debug: Optional[AiCardDebug] = None


def clamp_snippet(text: object, limit: int = 200) -> str:
    value = str(text or "").strip().replace("\n", " ")
    if len(value) <= int(limit):
        return value
    return value[: max(0, int(limit) - 3)] + "..."
