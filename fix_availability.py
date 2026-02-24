from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


def computeFixAvailability(issue: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        report = _base_report(context)
        reasons: list[dict[str, str]] = []

        if issue is None:
            _add_reason(reasons, "CLASH_CONTEXT_MISSING", "No issue selected.")

        cls_a = _norm_class(report["classification"]["A"].get("class"))
        cls_b = _norm_class(report["classification"]["B"].get("class"))
        if cls_a == "unknown":
            _add_reason(reasons, "CLASSIFICATION_UNKNOWN_A", "Element A classification is Unknown.")
        if cls_b == "unknown":
            _add_reason(reasons, "CLASSIFICATION_UNKNOWN_B", "Element B classification is Unknown.")

        search_sets = report.get("searchSets") or {}
        count_a = _to_int(((search_sets.get("A") or {}).get("count")))
        count_b = _to_int(((search_sets.get("B") or {}).get("count")))
        if count_a <= 0 or count_b <= 0:
            _add_reason(reasons, "SEARCHSET_EMPTY", "Search set scope is missing or empty for A/B.")

        rule_applicability = context.get("ruleApplicability") or {}
        any_applicable = bool(rule_applicability.get("anyApplicable", False))
        has_generic_fallback = bool(rule_applicability.get("hasGenericFallback", False))
        if not any_applicable and not has_generic_fallback:
            _add_reason(
                reasons,
                "NO_APPLICABLE_RULES",
                "No applicable pair rule found and no generic fallback rule is available.",
            )

        constraints = report.get("constraints") or {}
        movable_count = 0
        missing_constraints = False
        max_move_zero = False
        protected_count = 0
        for side in ("A", "B"):
            side_constraints = constraints.get(side) or {}
            max_move = side_constraints.get("maxMoveM")
            protected = side_constraints.get("protected")
            if protected is True:
                protected_count += 1
            if max_move is None:
                missing_constraints = True
                continue
            try:
                max_move_value = float(max_move)
            except (TypeError, ValueError):
                missing_constraints = True
                continue
            if max_move_value <= 0:
                max_move_zero = True
            if max_move_value > 0 and protected is not True:
                movable_count += 1
        if missing_constraints:
            _add_reason(reasons, "MISSING_CONSTRAINTS", "Required movement constraints are missing.")
        if movable_count <= 0:
            if protected_count >= 2:
                _add_reason(reasons, "ELEMENT_PROTECTED", "Both elements are protected and cannot be moved.")
            if max_move_zero:
                _add_reason(reasons, "MAX_MOVE_ZERO", "No movable element has max_move > 0.")

        clash_context = report.get("clashContext") or {}
        if (
            clash_context.get("minDistanceM") is None
            or clash_context.get("pA") is None
            or clash_context.get("pB") is None
        ):
            _add_reason(
                reasons,
                "CLASH_CONTEXT_MISSING",
                "Clash context is incomplete (missing min distance and/or pA/pB).",
            )

        generation_status = str(context.get("generationStatus") or "").strip()
        if generation_status in ("NoSolution", "Manual"):
            _add_reason(
                reasons,
                "NO_APPLICABLE_RULES",
                "Fix generation completed without a feasible candidate.",
            )

        report["reasons"] = reasons
        report["status"] = "AVAILABLE" if not reasons else "NOT_AVAILABLE"
        return report
    except Exception as exc:
        report = _base_report(context)
        report["status"] = "ERROR"
        report["reasons"] = [
            {"code": "INTERNAL_ERROR", "message": f"Failed to compute fix availability: {exc}"}
        ]
        return report


def _base_report(context: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "status": "NOT_AVAILABLE",
        "reasons": [],
        "classification": {
            "A": {"ifcType": "", "systemGroup": None, "name": None, "class": "Unknown", "confidence": 0.0},
            "B": {"ifcType": "", "systemGroup": None, "name": None, "class": "Unknown", "confidence": 0.0},
        },
        "constraints": {
            "A": {"movability": "Unknown", "maxMoveM": None, "zAllowed": None, "protected": None},
            "B": {"movability": "Unknown", "maxMoveM": None, "zAllowed": None, "protected": None},
        },
        "rulepack": {"path": "", "id": None, "version": None},
        "ruleTrace": {
            "A": {"signalsMatched": 0, "topSignals": [], "failed": []},
            "B": {"signalsMatched": 0, "topSignals": [], "failed": []},
        },
        "clashContext": {"minDistanceM": None, "method": None, "pA": None, "pB": None},
        "searchSets": {
            "A": {"name": "", "count": 0},
            "B": {"name": "", "count": 0},
        },
    }
    if not isinstance(context, dict):
        return base
    report = deepcopy(base)
    for key in (
        "classification",
        "constraints",
        "rulepack",
        "ruleTrace",
        "clashContext",
        "searchSets",
    ):
        if key in context and isinstance(context[key], dict):
            report[key] = _deep_merge(report[key], context[key])
    return report


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _norm_class(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    return text.lower()


def _add_reason(reasons: list[dict[str, str]], code: str, message: str) -> None:
    for item in reasons:
        if item.get("code") == code:
            return
    reasons.append({"code": code, "message": message})


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0
