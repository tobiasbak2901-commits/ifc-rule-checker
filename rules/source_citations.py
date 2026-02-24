from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from models import SourceCitation


DEFAULT_STANDARD = "DS 475:2012"


def _to_source_citation(raw: object, rule_id: str, yaml_path: Optional[str] = None) -> SourceCitation:
    source = raw if isinstance(raw, dict) else {}
    standard = str(source.get("standard") or DEFAULT_STANDARD)
    clause = source.get("clause")
    page = source.get("page")
    url = source.get("url")
    note = source.get("note")
    page_num: Optional[int]
    try:
        page_num = int(page) if page is not None else None
    except Exception:
        page_num = None
    return SourceCitation(
        standard=standard,
        rule_id=str(rule_id or ""),
        clause=str(clause) if clause else None,
        page=page_num,
        url=str(url) if url else None,
        note=str(note) if note else None,
        yaml_path=yaml_path,
    )


def citation_for_rule(rule_id: str, source: object, yaml_path: Optional[str] = None) -> SourceCitation:
    return _to_source_citation(source, rule_id=rule_id, yaml_path=yaml_path)


def find_rule_source(rulepack: object, rule_id: str) -> Optional[SourceCitation]:
    if not rulepack or not rule_id:
        return None
    for generated in list(getattr(rulepack, "generated_rules", []) or []):
        if not isinstance(generated, dict):
            continue
        if str(generated.get("id") or "") != str(rule_id):
            continue
        source = generated.get("source")
        return _to_source_citation(source, rule_id=rule_id, yaml_path=f"rules[{rule_id}]")
    for utility_rule in list(getattr(rulepack, "utility_rules", []) or []):
        if str(getattr(utility_rule, "rule_id", "")) != str(rule_id):
            continue
        source = getattr(utility_rule, "source", None)
        return _to_source_citation(source, rule_id=rule_id, yaml_path=f"utility_rules[{rule_id}]")
    return None


def citations_for_rule_ids(
    rulepack: object,
    rule_ids: Iterable[str],
    fallback_note: Optional[str] = None,
) -> List[SourceCitation]:
    out: List[SourceCitation] = []
    seen: set[str] = set()
    for rule_id in rule_ids:
        rid = str(rule_id or "").strip()
        if not rid or rid in seen:
            continue
        seen.add(rid)
        citation = find_rule_source(rulepack, rid)
        if citation is None:
            citation = SourceCitation(
                standard=DEFAULT_STANDARD,
                rule_id=rid,
                note=fallback_note or "Parafrase baseret på intern regeldefinition.",
                yaml_path=f"rules[{rid}]",
            )
        out.append(citation)
    return out


def citation_label(citation: SourceCitation) -> str:
    parts = [citation.standard, citation.rule_id]
    if citation.clause:
        parts.append(str(citation.clause))
    if citation.page is not None:
        parts.append(f"p.{int(citation.page)}")
    return " | ".join(parts)


def citation_details(citation: SourceCitation) -> str:
    lines = [
        f"Standard: {citation.standard}",
        f"Rule ID: {citation.rule_id}",
        f"Clause: {citation.clause or '-'}",
        f"Page: {citation.page if citation.page is not None else '-'}",
        f"Rulepack path: {citation.yaml_path or '-'}",
    ]
    if citation.note:
        lines.append("")
        lines.append("Parafrase")
        lines.append(str(citation.note))
    if citation.url:
        lines.append("")
        lines.append(f"Link: {citation.url}")
    return "\n".join(lines)
