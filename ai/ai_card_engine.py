from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, List, Optional
import uuid

from ai.models import AIContext, AICardResponse, Citation, NextAction
from ai.providers.base import BaseProvider


class AICardEngine:
    def __init__(self, provider: Optional[BaseProvider] = None):
        self._provider = provider

    def generate_card(self, context: AIContext, intent: str, question: Optional[str] = None) -> AICardResponse:
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        active_issue = context.active_issue
        has_issue = active_issue is not None and bool(active_issue.issue_id or active_issue.rule_id)

        summary = ""
        bullets: List[str] = []
        assumptions: List[str] = []
        citations: List[Citation] = []

        if not has_issue and not context.selection:
            summary = "Vaelg et clash eller en markering for at faa en grounded forklaring."
            bullets = [
                "Ponker siger: Ingen aktiv issue fundet.",
                "Hvorfor: Der er ingen aktiv rule-trace i den aktuelle visning.",
                "Hvad nu: Vaelg et clash i listen eller marker elementer i 3D.",
            ]
        elif has_issue and active_issue is not None:
            min_distance = float(active_issue.min_distance_m or 0.0)
            required = float(active_issue.required_clearance_m or 0.0)
            tolerance = float(active_issue.tolerance_m or 0.0)
            is_overlap = min_distance <= tolerance
            clash_type = active_issue.clash_type or ("overlap" if is_overlap else "clearance_fail")
            verdict = active_issue.clash_verdict or ("CLASH" if min_distance < required or is_overlap else "NO_CLASH")
            scope_left = ", ".join(active_issue.search_scope_left or ["-"])
            scope_right = ", ".join(active_issue.search_scope_right or ["-"])
            if is_overlap:
                summary = f"Ponker siger: Fysisk clash bekraeftet ({abs(min_distance) * 1000.0:.1f} mm overlap)."
            else:
                missing_mm = max(0.0, (required - min_distance) * 1000.0)
                summary = f"Ponker siger: Clearance-fejl. Mangler ca. {missing_mm:.1f} mm for at opfylde kravet."
            bullets = [
                (
                    "Hvorfor: "
                    f"verdict={verdict}, metode={active_issue.method or '-'}, "
                    f"minDistance={min_distance:.4f} m, required={required:.4f} m, tolerance={tolerance:.6f} m."
                ),
                (
                    "Hvad betyder det for projektering: "
                    "for koordinering er denne konflikt en reel risikopost for udfoerelse og pladsbehov."
                ),
                (
                    "Hvad nu: "
                    f"scope er {scope_left} vs {scope_right}; brug naeste handlinger til at dokumentere og afproeve fix."
                ),
            ]
            citations.append(
                Citation(
                    kind="GEOMETRY",
                    id="GEOM:minDistance",
                    label="GEOM:minDistance",
                    excerpt=(
                        f"minDistance={min_distance:.6f} m, required={required:.6f} m, "
                        f"method={active_issue.method or '-'}"
                    )[:200],
                    confidence=0.99,
                )
            )
            if context.measurement and context.measurement.value_mm is not None:
                citations.append(
                    Citation(
                        kind="MEASURE",
                        id=f"MEASURE:{context.measurement.measurement_id or 'latest'}",
                        label="MEASURE:latest",
                        excerpt=(
                            f"{context.measurement.kind or 'distance'}={float(context.measurement.value_mm):.1f} mm "
                            f"({context.measurement.method or '-'})"
                        )[:200],
                        confidence=0.95,
                    )
                )
            for rule in context.rules_fired:
                citations.append(
                    Citation(
                        kind="RULE",
                        id=f"RULE:{rule.rule_id}",
                        label=f"RULE:{rule.rule_id}",
                        excerpt=(rule.reason or "Rule fired")[:200],
                        confidence=0.98,
                    )
                )
                if rule.standard_refs:
                    for ref_id in rule.standard_refs:
                        ref = next((item for item in context.standard_refs if item.id == ref_id), None)
                        if ref is None:
                            continue
                        citations.append(
                            Citation(
                                kind="STANDARD",
                                id=ref.id,
                                label=ref.id,
                                excerpt=(ref.excerpt or ref.title)[:200],
                                confidence=0.9,
                            )
                        )
                else:
                    assumptions.append(f"Regel {rule.rule_id}: Ingen standard-kilde knyttet til denne regel endnu.")
            if clash_type == "clearance_fail":
                bullets.append("Ponker note: dette er en afstandsfejl, ikke et volumetrisk overlap.")
        else:
            classes = [
                f"{item.ai_class or 'Unknown'} ({item.confidence:.2f})"
                for item in context.classification_summary[:3]
            ]
            summary = "Ponker siger: Analyse af markering klar."
            bullets = [
                f"Klassifikation: {', '.join(classes) if classes else 'ingen signaler.'}",
                "Hvad nu: Brug klassifikationshjaelp eller rule trace for at goere naeste beslutning deterministisk.",
            ]

        confidence = self._confidence_score(context)
        bullets.append(
            f"Confidence: {confidence}% (paavirkes af klassifikation, trace-komplethed og maaledata)."
        )

        for note in context.project_memory[:3]:
            assumptions.append(f"Projekt-hukommelse [{note.scope}]: {note.text}")

        next_actions = self._build_next_actions(context)
        if intent == "PROPOSE_FIXES":
            bullets.insert(0, "Ponker siger: Fix-flow aktivt. Status vises i kortets trace/debug.")

        if question:
            summary = f"Ponker siger (Q/A): {question.strip()}"
            bullets.append("Svar er bundet til aktiv trace og tilladte citations.")

        allowed_ids = [item.id for item in citations]
        if self._provider and intent in {"PROJECT_QA", "EXPLAIN_CLASH"}:
            summary = self._provider.rephrase(summary, context, allowed_ids)

        response = AICardResponse(
            title="Ponker AI Card",
            summary=summary,
            bullets=bullets,
            citations=self._dedupe_citations(citations),
            assumptions=assumptions,
            next_actions=next_actions,
            debug_trace_id=trace_id,
        )
        self._log_event(context, intent=intent, question=question, response=response)
        return response

    def _confidence_score(self, context: AIContext) -> int:
        score = 45
        if context.active_issue and context.active_issue.method:
            score += 15
        if context.rules_fired:
            score += 20
        if any(item.standard_refs for item in context.rules_fired):
            score += 10
        if context.measurement and context.measurement.value_mm is not None:
            score += 5
        avg_class = 0.0
        if context.classification_summary:
            avg_class = sum(max(0.0, min(1.0, item.confidence)) for item in context.classification_summary) / float(
                len(context.classification_summary)
            )
        score += int(avg_class * 5.0)
        return max(0, min(100, score))

    def _build_next_actions(self, context: AIContext) -> List[NextAction]:
        out: List[NextAction] = []
        issue = context.active_issue
        fix_status = (context.fix_availability.status if context.fix_availability else "UNKNOWN").upper()
        fix_reasons = list(context.fix_availability.reasons or []) if context.fix_availability else []
        fix_enabled = fix_status == "AVAILABLE"
        fix_reason = ""
        if not fix_enabled and fix_reasons:
            first = fix_reasons[0]
            fix_reason = f"{first.get('code')}: {first.get('message')}"

        has_unknown = any((item.ai_class or "Unknown").strip().lower() == "unknown" for item in context.classification_summary)
        clash_type = (issue.clash_type if issue else "").strip().lower()

        out.append(
            NextAction(
                id="focus_clash",
                label="Fokuser clash",
                icon="target",
                enabled=issue is not None,
                reason="Ingen aktiv issue valgt." if issue is None else "",
                payload={"issue_id": issue.issue_id if issue else ""},
            )
        )

        if has_unknown:
            out.append(
                NextAction(
                    id="help_classify",
                    label="Hjaelp mig med at klassificere",
                    icon="tag",
                    enabled=True,
                    reason="",
                    payload={},
                )
            )
            out.append(
                NextAction(
                    id="show_ifc_properties",
                    label="Vis IFC properties",
                    icon="list",
                    enabled=True,
                    reason="",
                    payload={},
                )
            )

        if clash_type == "overlap":
            out.extend(
                [
                    NextAction("measure_distance", "Maal afstand", "ruler", True, "", {}),
                    NextAction("section_around_clash", "Section omkring clash", "section", True, "", {}),
                ]
            )
        elif clash_type == "clearance_fail":
            out.append(NextAction("show_requirements", "Vis krav", "book", True, "", {}))

        out.append(
            NextAction(
                id="generate_fixes",
                label="Generer fixes",
                icon="wand",
                enabled=fix_enabled,
                reason=fix_reason,
                payload={"issue_id": issue.issue_id if issue else ""},
            )
        )

        seen = set()
        deduped: List[NextAction] = []
        for item in out:
            if item.id in seen:
                continue
            seen.add(item.id)
            deduped.append(item)
        return deduped

    def _dedupe_citations(self, citations: Iterable[Citation]) -> List[Citation]:
        out: List[Citation] = []
        seen = set()
        for item in citations:
            key = (item.kind, item.id)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _log_event(self, context: AIContext, *, intent: str, question: Optional[str], response: AICardResponse) -> None:
        root = Path(context.project_root)
        log_dir = root / ".ponker"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "ai_log.jsonl"

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project_id": context.project_id,
            "intent": str(intent),
            "question": str(question or ""),
            "active_issue_id": context.active_issue.issue_id if context.active_issue else None,
            "debug_trace_id": response.debug_trace_id,
            "title": response.title,
            "summary": response.summary,
            "citations": [item.id for item in response.citations],
        }

        lines: List[str] = []
        if log_path.exists():
            try:
                lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            except Exception:
                lines = []
        lines.append(json.dumps(record, ensure_ascii=True))
        lines = lines[-50:]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
