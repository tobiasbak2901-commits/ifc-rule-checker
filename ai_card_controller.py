from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from typing import Any, Callable, Dict, Iterable, List, Optional

from ai_cards import (
    AiAction,
    AiCard,
    AiCardDebug,
    AiCardSection,
    AiContext,
    AiFactChip,
    EvidenceItem,
    EvidenceLink,
    clamp_snippet,
)
from models import Issue


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(out):
        return float(default)
    return out


def find_rule_source_payload(rulepack: object, rule_id: Optional[str]) -> Dict[str, Any]:
    rid = str(rule_id or "").strip()
    if not rid or rulepack is None:
        return {}
    for generated in list(getattr(rulepack, "generated_rules", []) or []):
        if not isinstance(generated, dict):
            continue
        if str(generated.get("id") or "") != rid:
            continue
        source = generated.get("source")
        if isinstance(source, dict):
            payload = dict(source)
            payload.setdefault("rule_id", rid)
            payload.setdefault("yaml_path", f"rules[{rid}]")
            return payload
    for utility_rule in list(getattr(rulepack, "utility_rules", []) or []):
        if str(getattr(utility_rule, "rule_id", "")) != rid:
            continue
        source = getattr(utility_rule, "source", None)
        if isinstance(source, dict):
            payload = dict(source)
            payload.setdefault("rule_id", rid)
            payload.setdefault("yaml_path", f"utility_rules[{rid}]")
            return payload
    return {}


def rule_source_to_evidence(rule_id: str, source: Optional[Dict[str, Any]]) -> List[EvidenceItem]:
    rid = str(rule_id or "").strip() or "SEARCH_SET_CLASH"
    payload = dict(source or {})
    source_section = str(payload.get("section") or payload.get("clause") or "").strip()
    source_standard = str(payload.get("standard") or "Rulepack").strip() or "Rulepack"
    excerpt = str(payload.get("excerpt") or payload.get("note") or "").strip()
    yaml_path = str(payload.get("yaml_path") or "").strip()

    evidence: List[EvidenceItem] = [
        EvidenceItem(
            kind="RULE",
            id=f"rule:{rid}",
            title=f"Regel {rid}",
            snippet=clamp_snippet(payload.get("note") or "Reglen er markeret som udløsende i denne vurdering."),
            link=EvidenceLink(type="local", target=yaml_path) if yaml_path else None,
            confidence=0.98,
        )
    ]
    if source_standard:
        section_suffix = f" {source_section}" if source_section else ""
        evidence.append(
            EvidenceItem(
                kind="STANDARD",
                id=f"{source_standard}{section_suffix}".strip(),
                title=f"{source_standard}{section_suffix}".strip(),
                snippet=clamp_snippet(excerpt or payload.get("note") or "Ingen kort paragraftekst angivet i rulepack."),
                link=None,
                confidence=0.9,
            )
        )
    return evidence


def build_issue_ai_card(
    context: AiContext,
    issue: Issue,
    *,
    class_a: str,
    class_b: str,
    rule_source: Optional[Dict[str, Any]] = None,
    fallback_warning: Optional[str] = None,
    fix_generation_debug: Optional[Dict[str, Any]] = None,
    fix_feedback: Optional[Dict[str, Any]] = None,
) -> AiCard:
    diag = dict(issue.clash_diagnostics or {})
    narrow = dict(diag.get("narrowphase") or {})
    broad = dict(diag.get("broadphase") or {})
    eps = _safe_float(narrow.get("eps"), 1.0e-4)
    min_distance_m = issue.min_distance_world
    if min_distance_m is None:
        min_distance_m = _safe_float(narrow.get("minDistance"), 0.0)
    required_m = issue.required_clearance_world
    if required_m is None:
        required_m = _safe_float(narrow.get("requiredClearance"), 0.0)
    method = str(narrow.get("method") or issue.detection_method or "unknown")
    min_distance_m = float(min_distance_m)
    required_m = float(required_m)
    overlap_mm = 0.0
    if min_distance_m <= eps:
        overlap_mm = abs(min_distance_m) * 1000.0
    measured_clearance_mm = max(0.0, min_distance_m * 1000.0)
    missing_mm = max(0.0, (required_m - max(min_distance_m, 0.0)) * 1000.0)
    scope_left = ", ".join(issue.search_set_names_a or ["-"])
    scope_right = ", ".join(issue.search_set_names_b or ["-"])

    status = "error" if min_distance_m <= eps else "warning"
    if min_distance_m > required_m:
        status = "success"
    is_overlap = min_distance_m <= eps
    if is_overlap:
        summary = (
            f"Clash bekræftet: fysisk overlap ({overlap_mm:.1f} mm) mellem {class_a or 'Unknown'} og {class_b or 'Unknown'}."
        )
    else:
        summary = (
            f"Clearance-overskridelse: målt afstand {min_distance_m*1000.0:.1f} mm "
            f"mod krav {required_m*1000.0:.1f} mm."
        )

    bullets = [
        (
            "Hvad sker der? "
            + (
                f"Elementerne overlapper (minDistance={min_distance_m:.4f} m, tolerance EPS={eps:.6f} m)."
                if is_overlap
                else f"Afstanden er under kravet med ca. {missing_mm:.1f} mm."
            )
        ),
        (
            "Hvorfor? "
            f"Regel {issue.rule_id or 'SEARCH_SET_CLASH'} blev udløst med metode {method}. "
            f"Scope: {scope_left} vs {scope_right}. "
            f"Broadphase hit={'ja' if bool(broad.get('intersects')) else 'nej'} "
            f"(pad={_safe_float(broad.get('padding'), 0.0):.4f} m)."
        ),
        "Hvad kan du gøre? Fokusér på clash, mål frihøjde igen, og generér løsningsforslag før beslutning.",
    ]

    citations: List[EvidenceItem] = [
        EvidenceItem(
            kind="GEOMETRY",
            id="geom:min_distance",
            title="Geometrimåling",
            snippet=(
                f"minDistance={min_distance_m:.6f} m, requiredClearance={required_m:.6f} m, "
                f"method={method}, eps={eps:.6f} m"
            ),
            confidence=0.99,
        )
    ]
    citations.extend(rule_source_to_evidence(issue.rule_id or "SEARCH_SET_CLASH", rule_source))

    section_enabled = bool(context.sectionBox and context.sectionBox.enabled)
    section_action_label = "Fjern section omkring clash" if section_enabled else "Section omkring clash"
    actions = [
        AiAction(label="Generér fixes", actionId="generate_fixes", params={"issue_id": issue.issue_id or ""}),
        AiAction(label="Fokusér clash", actionId="focus_issue", params={"issue_id": issue.issue_id or ""}),
        AiAction(label="Mål afstand", actionId="start_measure", params={"mode": "clearance"}),
        AiAction(label=section_action_label, actionId="toggle_section_box", params={"scope": "issue"}),
    ]
    feedback = dict(fix_feedback or {})
    feedback_mode = str(feedback.get("mode") or "").strip().lower()
    if feedback_mode == "no_simple_fix":
        actions.append(AiAction(label="Tillad Z-flyt", actionId="allow_z_move", params={"issue_id": issue.issue_id or ""}))
        actions.append(
            AiAction(
                label="Forøg maks. flyt",
                actionId="increase_max_move",
                params={"issue_id": issue.issue_id or ""},
            )
        )

    one_line = (
        f"Overlap: {overlap_mm:.1f} mm | "
        f"Clearance: {measured_clearance_mm:.1f} mm | "
        f"Rule: {issue.rule_id or 'SEARCH_SET_CLASH'}"
    )
    fact_chips = [
        AiFactChip(label="Overlap", value=f"{overlap_mm:.1f} mm" if is_overlap else "0.0 mm"),
        AiFactChip(label="Clearance", value=f"{measured_clearance_mm:.1f} mm"),
        AiFactChip(label="Rule", value=str(issue.rule_id or "SEARCH_SET_CLASH")),
    ]

    assumptions_lines = [
        f"EPS/tolerance: {eps:.6f} m.",
        f"Broadphase padding: {_safe_float(broad.get('padding'), 0.0):.4f} m.",
    ]
    if fallback_warning:
        assumptions_lines.append(str(fallback_warning))
    if str(class_a or "Unknown").lower() == "unknown" or str(class_b or "Unknown").lower() == "unknown":
        assumptions_lines.append(
            "Klassifikation er ukendt; forslag kan være geometri-baserede indtil system/disciplin er sat."
        )

    source_payload = dict(rule_source or {})
    standard = str(source_payload.get("standard") or "").strip()
    section = str(source_payload.get("section") or source_payload.get("clause") or "").strip()
    excerpt = str(source_payload.get("excerpt") or source_payload.get("note") or "").strip()
    if standard:
        docs_lines = [
            f"Standard: {standard}",
            f"Afsnit: {section or '-'}",
            (
                "Krav: "
                + (
                    excerpt
                    or "Ledninger må ikke overlappe eller ligge tættere end den krævede friafstand."
                )
            ),
        ]
    else:
        docs_lines = [
            "Denne vurdering er kun geometrisk.",
            "Ingen specifik standardregel er knyttet til denne clash-type.",
        ]

    suggestion_lines: List[str] = []
    suggestion_title = "Hvorfor"
    if feedback_mode == "suggestion":
        suggestion_title = "Forslag"
        suggestion_lines = [
            str(feedback.get("title") or "Forslag: Flyt elementet."),
            str(feedback.get("impact") or "Løser mindst 1 clash."),
        ]
    elif feedback_mode == "no_simple_fix":
        suggestion_title = "Ingen simple fixes fundet"
        warning_lines = [str(v) for v in list(feedback.get("bullets") or []) if str(v).strip()]
        suggestion_lines = warning_lines or [
            "Begge elementer låst i Z-retning.",
            "Maksimal flyt er mindre end påkrævet clearance.",
        ]
    else:
        suggestion_lines = bullets

    details_lines = [
        f"minDistance={min_distance_m:.6f} m",
        f"requiredClearance={required_m:.6f} m",
        f"method={method}",
        f"broadphase.intersects={bool(broad.get('intersects'))}",
    ]
    debug_payload = dict(fix_generation_debug or {})
    if debug_payload:
        details_lines.append(f"lastFixGenStatus={debug_payload.get('lastFixGenStatus', '-')}")
        details_lines.append(f"lastFixGenReason={debug_payload.get('lastFixGenReason', '-')}")
        details_lines.append(f"candidatesEvaluated={debug_payload.get('candidatesEvaluated', 0)}")
        details_lines.append(f"topCandidateScore={debug_payload.get('topCandidateScore', '-')}")

    card_id = f"ai:issue:{issue.issue_id or (issue.guid_a + '|' + issue.guid_b + '|' + (issue.rule_id or ''))}"
    return AiCard(
        id=card_id,
        title=f"{class_a or 'Unknown'} vs {class_b or 'Unknown'}",
        status=status,
        summary=summary,
        bullets=bullets,
        recommendedActions=actions,
        citations=citations,
        oneLineSummary=one_line,
        factChips=fact_chips,
        sections=[
            AiCardSection(id="why", title=suggestion_title, lines=suggestion_lines),
            AiCardSection(id="docs", title="Kilde", lines=docs_lines),
            AiCardSection(id="assumptions", title="Antagelser", lines=assumptions_lines),
            AiCardSection(id="details", title="Detaljer", lines=details_lines),
        ],
        debug=AiCardDebug(contextHash=context.context_hash(), generatedAt=_now_iso(), model="rules"),
    )


def build_selection_ai_card(
    context: AiContext,
    *,
    selected_ids: List[str],
    class_name: str,
    class_confidence: float,
    top_candidates: Iterable[str],
    applicable_rules: Iterable[str],
    missing_data: Iterable[str],
) -> AiCard:
    class_label = str(class_name or "Unknown")
    conf = _safe_float(class_confidence, 0.0)
    candidate_lines = [str(v).strip() for v in list(top_candidates or []) if str(v).strip()][:3]
    rule_lines = [str(v).strip() for v in list(applicable_rules or []) if str(v).strip()][:3]
    missing_lines = [str(v).strip() for v in list(missing_data or []) if str(v).strip()][:3]
    if class_label.lower() == "unknown":
        status = "warning"
        summary = "Klassifikation er usikker (Unknown). Der mangler data for sikker regelvurdering."
    elif conf < 0.5:
        status = "info"
        summary = f"Foreløbig klassifikation: {class_label} (confidence {conf:.2f}). Verificér før beslutning."
    else:
        status = "success"
        summary = f"Valgt objekt er klassificeret som {class_label} (confidence {conf:.2f})."

    bullets = [
        f"Hvad sker der? Du har valgt {len(selected_ids)} objekt(er). Primær klasse: {class_label} (confidence {conf:.2f}).",
        "Hvorfor? Klassifikationen bygger på model-egenskaber (system/type/navn).",
    ]
    if candidate_lines:
        bullets.append("Top-kandidater: " + " | ".join(candidate_lines))
    if rule_lines:
        bullets.append("Mulige regler: " + " | ".join(rule_lines))
    if missing_lines:
        bullets.append("Mangler data: " + " | ".join(missing_lines))
    else:
        bullets.append("Hvad kan du gøre? Start måling eller fokusér på issue for at få regeludløsning.")

    citations: List[EvidenceItem] = [
        EvidenceItem(
            kind="MODEL_PROPERTY",
            id="model:classification",
            title="Klassifikation",
            snippet=clamp_snippet(f"class={class_label}, confidence={conf:.2f}"),
            confidence=0.9,
        )
    ]
    if class_label.lower() == "unknown":
        citations.append(
            EvidenceItem(
                kind="ASSUMPTION",
                id="assumption:missing_classification_inputs",
                title="Manglende input",
                snippet="mangler diameter/systemnavn; kontrollér Pset-egenskaber for type- og systemfelter.",
                confidence=0.75,
            )
        )

    section_enabled = bool(context.sectionBox and context.sectionBox.enabled)
    section_action_label = "Fjern section box" if section_enabled else "Sektion på udvalg"
    actions = [
        AiAction(label="Mål afstand", actionId="start_measure", params={"mode": "clearance"}),
        AiAction(label=section_action_label, actionId="toggle_section_box", params={"scope": "selection"}),
        AiAction(label="Åbn rule trace", actionId="open_rule_trace", params={"guid": selected_ids[0] if selected_ids else ""}),
    ]
    if class_label.lower() == "unknown":
        actions.append(AiAction(label="Hjælp mig med at klassificere", actionId="help_classify", params={}))

    stable_key = "|".join(sorted([str(v) for v in selected_ids if str(v)]))
    stable_hash = hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:12] if stable_key else context.context_hash()[:12]
    return AiCard(
        id=f"ai:selection:{stable_hash}",
        title="Objektanalyse",
        status=status,
        summary=summary,
        bullets=bullets,
        recommendedActions=actions,
        citations=citations,
        oneLineSummary=f"SELECTION • class: {class_label} • confidence: {conf:.2f}",
        factChips=[
            AiFactChip(label="Klasse", value=class_label),
            AiFactChip(label="Confidence", value=f"{conf:.2f}"),
            AiFactChip(label="Udvalg", value=f"{len(selected_ids)} objekt(er)"),
            AiFactChip(label="Regler", value=", ".join(rule_lines) if rule_lines else "none"),
        ],
        sections=[
            AiCardSection(id="why", title="Hvorfor", lines=bullets[:2]),
            AiCardSection(
                id="docs",
                title="Dokumentation",
                lines=[f"[{item.kind}] {item.title}: {item.snippet}" for item in citations] or ["Ingen dokumentation."],
            ),
            AiCardSection(id="assumptions", title="Antagelser", lines=missing_lines or ["Ingen særlige antagelser."]),
            AiCardSection(
                id="details",
                title="Detaljer",
                lines=[
                    f"selected={len(selected_ids)}",
                    f"class={class_label}",
                    f"confidence={conf:.3f}",
                ],
            ),
        ],
        debug=AiCardDebug(contextHash=context.context_hash(), generatedAt=_now_iso(), model="rules"),
    )


def build_empty_ai_card(context: AiContext) -> AiCard:
    return AiCard(
        id=f"ai:empty:{context.context_hash()[:8]}",
        title="Ponker AI",
        status="info",
        summary="Vælg et objekt eller et clash for at få AI-forklaring.",
        bullets=[],
        recommendedActions=[],
        citations=[],
        oneLineSummary="Vælg et objekt eller et clash.",
        factChips=[],
        sections=[],
        debug=AiCardDebug(contextHash=context.context_hash(), generatedAt=_now_iso(), model="rules"),
    )


def validate_ai_card_payload(payload: Dict[str, Any]) -> Optional[AiCard]:
    if not isinstance(payload, dict):
        return None
    try:
        actions: List[AiAction] = []
        for item in list(payload.get("recommendedActions") or []):
            if not isinstance(item, dict):
                continue
            actions.append(
                AiAction(
                    label=str(item.get("label") or ""),
                    actionId=str(item.get("actionId") or ""),
                    enabled=bool(item.get("enabled", True)),
                    reason=str(item.get("reason") or ""),
                    params=dict(item.get("params") or {}),
                )
            )
        citations: List[EvidenceItem] = []
        for item in list(payload.get("citations") or []):
            if not isinstance(item, dict):
                continue
            link_raw = item.get("link")
            link = None
            if isinstance(link_raw, dict) and link_raw.get("type") in ("local", "url"):
                link = EvidenceLink(type=str(link_raw["type"]), target=str(link_raw.get("target") or ""))
            citations.append(
                EvidenceItem(
                    kind=str(item.get("kind") or "ASSUMPTION"),  # type: ignore[arg-type]
                    id=str(item.get("id") or ""),
                    title=str(item.get("title") or ""),
                    snippet=clamp_snippet(item.get("snippet") or ""),
                    link=link,
                    confidence=_safe_float(item.get("confidence"), 0.5),
                )
            )
        debug_raw = payload.get("debug")
        debug = None
        if isinstance(debug_raw, dict):
            debug = AiCardDebug(
                contextHash=str(debug_raw.get("contextHash") or ""),
                generatedAt=str(debug_raw.get("generatedAt") or _now_iso()),
                model=str(debug_raw.get("model") or "hybrid"),  # type: ignore[arg-type]
            )
        fact_chips: List[AiFactChip] = []
        for item in list(payload.get("factChips") or []):
            if not isinstance(item, dict):
                continue
            fact_chips.append(
                AiFactChip(
                    label=str(item.get("label") or ""),
                    value=str(item.get("value") or ""),
                )
            )
        sections: List[AiCardSection] = []
        for item in list(payload.get("sections") or []):
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("id") or "details")
            if section_id not in ("why", "docs", "trace", "assumptions", "details"):
                section_id = "details"
            sections.append(
                AiCardSection(
                    id=section_id,  # type: ignore[arg-type]
                    title=str(item.get("title") or section_id.title()),
                    lines=[str(v) for v in list(item.get("lines") or [])],
                )
            )
        return AiCard(
            id=str(payload.get("id") or ""),
            title=str(payload.get("title") or "Ponker AI"),
            status=str(payload.get("status") or "info"),  # type: ignore[arg-type]
            summary=str(payload.get("summary") or ""),
            bullets=[str(v) for v in list(payload.get("bullets") or [])],
            recommendedActions=actions,
            citations=citations,
            oneLineSummary=str(payload.get("oneLineSummary") or ""),
            factChips=fact_chips,
            sections=sections,
            debug=debug,
        )
    except Exception:
        return None


class AiCardController:
    def __init__(
        self,
        deterministic_builder: Callable[[AiContext], AiCard],
        *,
        llm_rewriter: Optional[Callable[[AiContext, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self._deterministic_builder = deterministic_builder
        self._llm_rewriter = llm_rewriter
        self._use_llm = str(os.environ.get("USE_LLM", "false")).strip().lower() in ("1", "true", "yes")

    def generate(self, context: AiContext) -> AiCard:
        base_card = self._deterministic_builder(context)
        if not self._use_llm or not callable(self._llm_rewriter):
            return base_card
        try:
            rewritten_payload = self._llm_rewriter(context, asdict(base_card))
            candidate = validate_ai_card_payload(rewritten_payload if isinstance(rewritten_payload, dict) else {})
            if candidate is None:
                return base_card
            # Preserve deterministic citation IDs and all numeric snippets.
            base_ids = {item.id for item in base_card.citations}
            cand_ids = {item.id for item in candidate.citations}
            if not base_ids.issubset(cand_ids):
                return base_card
            return candidate
        except Exception:
            return base_card
