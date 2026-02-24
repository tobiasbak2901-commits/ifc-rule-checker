from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


_TEXT_TRANSLATION = str.maketrans(
    {
        "\u00e6": "ae",
        "\u00f8": "oe",
        "\u00e5": "aa",
    }
)


def _normalize_text(value: object) -> str:
    text = _norm(value)
    if not text:
        return ""
    return text.translate(_TEXT_TRANSLATION)


def _ensure_list(values: object) -> List[object]:
    if values is None:
        return []
    if isinstance(values, list):
        return values
    return [values]


def query_signature(query: object) -> str:
    try:
        return json.dumps(query or [], sort_keys=True, ensure_ascii=True, default=str)
    except Exception:
        return str(query)


def parse_query_text(text: str) -> Tuple[Optional[List[Dict[str, object]]], Optional[str]]:
    raw = (text or "").strip()
    if not raw:
        return [], None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc.msg} (line {exc.lineno}, col {exc.colno})"
    if not isinstance(parsed, list):
        return None, "Query must be a JSON array of condition objects."
    conditions: List[Dict[str, object]] = []
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            return None, f"Condition #{idx} must be an object."
        conditions.append(item)
    return conditions, None


def condition_label(condition: object) -> str:
    if not isinstance(condition, dict):
        return "invalid condition"
    parts = []
    for key, value in condition.items():
        if key == "invert":
            continue
        try:
            parts.append(f"{key}={json.dumps(value, ensure_ascii=True, default=str)}")
        except Exception:
            parts.append(f"{key}={value}")
    if not parts:
        return "empty condition"
    label = " && ".join(parts)
    if condition.get("invert"):
        return f"NOT({label})"
    return label


def evaluate_query(
    element,
    query: object,
    diameter_mm: Optional[float] = None,
) -> Tuple[bool, List[Tuple[str, bool, str]]]:
    conditions = query if isinstance(query, list) else []
    if not conditions:
        return True, []
    details: List[Tuple[str, bool, str]] = []
    all_ok = True
    for condition in conditions:
        ok, reason = evaluate_condition(element, condition, diameter_mm=diameter_mm)
        details.append((condition_label(condition), ok, reason))
        if not ok:
            all_ok = False
    return all_ok, details


def evaluate_condition(
    element,
    condition: object,
    diameter_mm: Optional[float] = None,
) -> Tuple[bool, str]:
    if not isinstance(condition, dict):
        return False, "Condition must be an object"

    invert = bool(condition.get("invert", False))
    checks: List[Tuple[bool, str]] = []

    if "ifcTypeIn" in condition:
        expected = {_norm(v) for v in _ensure_list(condition.get("ifcTypeIn")) if _norm(v)}
        value = _norm(getattr(element, "type", ""))
        ok = bool(expected) and value in expected
        checks.append((ok, f"ifcTypeIn ({getattr(element, 'type', '-')})"))

    if "disciplineIn" in condition:
        expected = {_norm(v) for v in _ensure_list(condition.get("disciplineIn")) if _norm(v)}
        value = _norm(getattr(element, "discipline", ""))
        ok = bool(expected) and value in expected
        checks.append((ok, f"disciplineIn ({getattr(element, 'discipline', '-')})"))

    if "systemContainsAny" in condition:
        needles = [_normalize_text(v) for v in _ensure_list(condition.get("systemContainsAny")) if _normalize_text(v)]
        values = _system_values(element)
        ok, matched = _contains_any(values, needles)
        checks.append((ok, f"systemContainsAny ({matched or '-'})"))

    if "nameContainsAny" in condition:
        needles = [_normalize_text(v) for v in _ensure_list(condition.get("nameContainsAny")) if _normalize_text(v)]
        values = [str(getattr(element, "name", "") or "")]
        ok, matched = _contains_any(values, needles)
        checks.append((ok, f"nameContainsAny ({matched or '-'})"))

    if "classificationContainsAny" in condition:
        needles = [
            _normalize_text(v)
            for v in _ensure_list(condition.get("classificationContainsAny"))
            if _normalize_text(v)
        ]
        values = [
            str(getattr(element, "class_name", "") or ""),
            str(getattr(element, "utility_type", "") or ""),
        ]
        ok, matched = _contains_any(values, needles)
        checks.append((ok, f"classificationContainsAny ({matched or '-'})"))

    if "psetEquals" in condition:
        ok, reason = _match_pset_equals(element, condition.get("psetEquals"))
        checks.append((ok, reason))

    if "minDiameter" in condition:
        value = _to_float(condition.get("minDiameter"))
        ok = value is not None and diameter_mm is not None and float(diameter_mm) >= value
        checks.append((ok, f"minDiameter ({diameter_mm if diameter_mm is not None else '-'})"))

    if "maxDiameter" in condition:
        value = _to_float(condition.get("maxDiameter"))
        ok = value is not None and diameter_mm is not None and float(diameter_mm) <= value
        checks.append((ok, f"maxDiameter ({diameter_mm if diameter_mm is not None else '-'})"))

    if "layerContainsAny" in condition:
        needles = [_normalize_text(v) for v in _ensure_list(condition.get("layerContainsAny")) if _normalize_text(v)]
        layers = _layer_values(element)
        ok, matched = _contains_any(layers, needles)
        checks.append((ok, f"layerContainsAny ({matched or '-'})"))

    if not checks:
        return False, "No supported condition keys"

    base_ok = all(ok for ok, _ in checks)
    if base_ok:
        reason = "; ".join(reason for _, reason in checks)
    else:
        reason = "; ".join(reason for ok, reason in checks if not ok)

    if invert:
        return (not base_ok), f"invert: {reason}"
    return base_ok, reason


def _to_float(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


def _contains_any(values: Iterable[object], needles: List[str]) -> Tuple[bool, str]:
    if not needles:
        return False, ""
    normalized = [(_normalize_text(v), str(v)) for v in values if str(v or "").strip()]
    for needle in needles:
        for candidate_norm, candidate_raw in normalized:
            if needle and needle in candidate_norm:
                return True, candidate_raw
    return False, ""


def _system_values(element) -> List[str]:
    values: List[str] = []
    direct = getattr(element, "system", None)
    if direct:
        values.append(str(direct))
    systems = getattr(element, "systems", None) or []
    values.extend(str(v) for v in systems if v)
    groups = getattr(element, "system_group_names", None) or []
    values.extend(str(v) for v in groups if v)
    meta = getattr(element, "ifc_meta", {}) or {}
    meta_systems = meta.get("system_groups") or meta.get("systems") or []
    values.extend(str(v) for v in meta_systems if v)
    return values


def _layer_values(element) -> List[str]:
    values: List[str] = []
    layers = getattr(element, "layers", None) or []
    values.extend(str(v) for v in layers if v)
    meta = getattr(element, "ifc_meta", {}) or {}
    meta_layers = meta.get("layers") or []
    values.extend(str(v) for v in meta_layers if v)
    return values


def _match_pset_equals(element, spec: object) -> Tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, "psetEquals invalid"
    pset = _norm(spec.get("pset"))
    prop = _norm(spec.get("prop"))
    expected_raw = spec.get("value")
    expected = _normalize_text(expected_raw)
    if_available = bool(spec.get("ifAvailable", False))
    if not pset or not prop:
        return False, "psetEquals missing pset/prop"
    if expected_raw is None:
        return False, "psetEquals missing value"

    actual = _find_pset_value(element, pset, prop)
    if actual is None:
        if if_available:
            return True, f"psetEquals skipped {pset}.{prop} (not available)"
        return False, f"psetEquals missing {pset}.{prop}"
    actual_norm = _normalize_text(actual)
    if actual_norm == expected:
        return True, f"psetEquals {pset}.{prop}={actual}"
    return False, f"psetEquals {pset}.{prop}={actual} (expected {expected_raw})"


def _find_pset_value(element, pset: str, prop: str):
    psets = getattr(element, "psets", {}) or {}
    value = _find_in_pset_map(psets, pset, prop)
    if value is not None:
        return value

    type_psets = getattr(element, "type_psets", {}) or {}
    value = _find_in_pset_map(type_psets, pset, prop)
    if value is not None:
        return value

    meta = getattr(element, "ifc_meta", {}) or {}
    if pset in ("item", "ifcitem"):
        item = meta.get("item") or {}
        return _find_in_flat_map(item, prop)
    if pset in ("type", "ifctype"):
        item = meta.get("type") or {}
        return _find_in_flat_map(item, prop)

    meta_psets = meta.get("psets") or {}
    value = _find_in_pset_map(meta_psets, pset, prop)
    if value is not None:
        return value

    meta_type_psets = meta.get("type_psets") or {}
    return _find_in_pset_map(meta_type_psets, pset, prop)


def _find_in_pset_map(psets: object, pset: str, prop: str):
    if not isinstance(psets, dict):
        return None
    for pset_name, props in psets.items():
        if _norm(pset_name) != pset:
            continue
        if not isinstance(props, dict):
            continue
        return _find_in_flat_map(props, prop)
    return None


def _find_in_flat_map(values: object, prop: str):
    if not isinstance(values, dict):
        return None
    for key, value in values.items():
        if _norm(key) == prop:
            return value
    return None
