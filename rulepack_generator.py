from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except Exception as exc:  # pragma: no cover - optional dependency guard
    raise RuntimeError("rulepack_generator requires PyYAML (pip install pyyaml)") from exc


SUPPORTED_CHECK_TYPES = {"min_clearance"}
SEVERITY_VALUES = {"info", "warning", "error"}
RULEPACK_ID_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
RULE_ID_RE = re.compile(r"^[A-Z0-9_]+$")
CLASS_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]+$")


@dataclass
class SignalTrace:
    signalType: str
    triedPaths: List[str]
    matchedPath: Optional[str]
    matchedValue: Optional[str]
    keywordsHit: List[str]
    reason: str


@dataclass
class ClassMatchTrace:
    classId: str
    matched: bool
    signals: List[SignalTrace]
    confidence: float


@dataclass
class RuleApplyTrace:
    ruleId: str
    applicable: bool
    relation: str
    classIn: List[str]
    reason: str


@dataclass
class RuleCheckTrace:
    ruleId: str
    checkType: str
    inputValues: Dict[str, Any]
    threshold: Dict[str, Any]
    passed: bool
    reason: str


@dataclass
class SelectionTrace:
    topClassId: str
    topConfidence: float
    classMatches: List[ClassMatchTrace] = field(default_factory=list)
    ruleApplies: List[RuleApplyTrace] = field(default_factory=list)
    ruleChecks: List[RuleCheckTrace] = field(default_factory=list)


def parse_rulepack_input_text(text: str, suffix: str = ".json") -> Dict[str, Any]:
    parsed: object
    if suffix.lower() in (".yaml", ".yml"):
        parsed = yaml.safe_load(text) or {}
    else:
        parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Input must be a mapping/object at the top level.")
    return parsed


def load_rulepack_input(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return parse_rulepack_input_text(text, path.suffix)


def load_rulepack_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Rulepack YAML must be a mapping.")
    return parsed


def ensure_yaml_extension(path: Path) -> Tuple[Path, bool]:
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return path, False
    return path.with_suffix(".yaml"), True


def dump_rulepack_yaml(rulepack_data: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        rulepack_data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
    )


def write_rulepack_yaml(rulepack_data: Dict[str, Any], path: Path) -> Path:
    target_path, _ = ensure_yaml_extension(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(dump_rulepack_yaml(rulepack_data), encoding="utf-8")
    return target_path


def generate_rulepack_from_input(input_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors = validate_rulepack_input(input_data)
    if errors:
        return None, errors
    output_data = build_rulepack_yaml(input_data)
    output_errors = validate_rulepack_output(output_data)
    if output_errors:
        return None, output_errors
    return output_data, []


def build_rulepack_yaml(input_data: Dict[str, Any]) -> Dict[str, Any]:
    rulepack_meta = input_data.get("rulepack") or {}
    classes = input_data.get("classes") or []
    defaults = input_data.get("defaults") or {}
    constraints = defaults.get("constraints") or {}
    rules = input_data.get("rules") or []

    output_classes: List[Dict[str, Any]] = []
    for cls in classes:
        if not isinstance(cls, dict):
            continue
        class_id = str(cls.get("id") or "").strip()
        class_name = str(cls.get("name") or "").strip() or class_id
        keywords = [str(v).strip() for v in _ensure_list(cls.get("keywords")) if str(v).strip()]
        path_candidates = [str(v).strip() for v in _ensure_list(cls.get("path_candidates")) if str(v).strip()]
        output_classes.append(
            {
                "id": class_id,
                "name": class_name,
                "match": {
                    "any": [
                        {
                            "property_contains_any": {
                                "path_candidates": path_candidates,
                                "values": keywords,
                            }
                        }
                    ]
                },
            }
        )

    output_rules: List[Dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        class_in, relation = _input_rule_applies(rule)
        check = dict(rule.get("check") or {})
        explain_short = _rule_explain_short(rule)
        output_rules.append(
            {
                "id": str(rule.get("id") or "").strip(),
                "title": str(rule.get("title") or "").strip(),
                "applies_to": {
                    "class_in": class_in,
                    "relation": relation,
                },
                "check": check,
                "severity": str(rule.get("severity") or "").strip(),
                "explain": {"short": explain_short},
            }
        )

    return {
        "schema_version": 1,
        "rulepack": {
            "id": str(rulepack_meta.get("id") or "").strip(),
            "name": str(rulepack_meta.get("name") or "").strip(),
            "version": str(rulepack_meta.get("version") or "").strip(),
            "author": str(rulepack_meta.get("author") or "").strip(),
            "description": str(rulepack_meta.get("description") or "").strip(),
        },
        "classification": {
            "classes": output_classes,
        },
        "defaults": {
            "constraints": {
                "max_move_m": constraints.get("max_move_m"),
                "z_move_allowed": constraints.get("z_move_allowed"),
            }
        },
        "rules": output_rules,
    }


def validate_rulepack_input(data: object, supported_check_types: Optional[Iterable[str]] = None) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["[root] must be an object/mapping"]

    check_types = {str(v).strip().lower() for v in (supported_check_types or SUPPORTED_CHECK_TYPES)}
    _validate_rulepack_meta(data.get("rulepack"), errors, path="rulepack")
    _validate_input_classes(data.get("classes"), errors)
    _validate_defaults(data.get("defaults"), errors)
    _validate_input_rules(data.get("rules"), errors, check_types)
    return errors


def validate_rulepack_output(data: object, supported_check_types: Optional[Iterable[str]] = None) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["[root] must be an object/mapping"]

    check_types = {str(v).strip().lower() for v in (supported_check_types or SUPPORTED_CHECK_TYPES)}
    schema_version = data.get("schema_version")
    if schema_version != 1:
        errors.append("[schema_version] must be 1")

    _validate_rulepack_meta(data.get("rulepack"), errors, path="rulepack")
    _validate_output_classes((data.get("classification") or {}).get("classes"), errors)
    _validate_defaults(data.get("defaults"), errors)
    _validate_output_rules(data.get("rules"), errors, check_types)
    return errors


def _validate_rulepack_meta(raw: object, errors: List[str], path: str) -> None:
    if not isinstance(raw, dict):
        errors.append(f"[{path}] must be an object")
        return
    rulepack_id = str(raw.get("id") or "").strip()
    if not rulepack_id:
        errors.append(f"[{path}.id] is required")
    elif not RULEPACK_ID_RE.match(rulepack_id):
        errors.append(f"[{path}.id] must match ^[a-z0-9_]+$ and not start with a digit")
    for field_name in ("name", "version", "author", "description"):
        value = str(raw.get(field_name) or "").strip()
        if not value:
            errors.append(f"[{path}.{field_name}] is required")


def _validate_input_classes(raw: object, errors: List[str]) -> None:
    if not isinstance(raw, list) or not raw:
        errors.append("[classes] must contain at least 1 class")
        return
    for idx, item in enumerate(raw):
        _validate_class_common(item, errors, f"classes[{idx}]")


def _validate_output_classes(raw: object, errors: List[str]) -> None:
    if not isinstance(raw, list) or not raw:
        errors.append("[classification.classes] must contain at least 1 class")
        return
    for idx, item in enumerate(raw):
        path = f"classification.classes[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"[{path}] must be an object")
            continue
        _validate_class_common(item, errors, path)
        match = item.get("match")
        if not isinstance(match, dict):
            errors.append(f"[{path}.match] is required")
            continue
        any_signals = match.get("any")
        if not isinstance(any_signals, list) or not any_signals:
            errors.append(f"[{path}.match.any] must contain at least 1 signal")
            continue
        signal_ok = False
        for signal_idx, signal in enumerate(any_signals):
            signal_path = f"{path}.match.any[{signal_idx}]"
            if not isinstance(signal, dict):
                errors.append(f"[{signal_path}] must be an object")
                continue
            spec = signal.get("property_contains_any")
            if not isinstance(spec, dict):
                continue
            signal_ok = True
            paths = [str(v).strip() for v in _ensure_list(spec.get("path_candidates")) if str(v).strip()]
            values = [str(v).strip() for v in _ensure_list(spec.get("values")) if str(v).strip()]
            if not paths:
                errors.append(f"[{signal_path}.property_contains_any.path_candidates] must contain at least 1 value")
            if not values:
                errors.append(f"[{signal_path}.property_contains_any.values] must contain at least 1 value")
        if not signal_ok:
            errors.append(f"[{path}.match.any] must include property_contains_any")


def _validate_class_common(item: object, errors: List[str], path: str) -> None:
    if not isinstance(item, dict):
        errors.append(f"[{path}] must be an object")
        return
    class_id = str(item.get("id") or "").strip()
    if not class_id:
        errors.append(f"[{path}.id] is required")
    elif not CLASS_ID_RE.match(class_id):
        errors.append(f"[{path}.id] must match ^[A-Za-z][A-Za-z0-9_]+$")
    class_name = str(item.get("name") or "").strip()
    if not class_name:
        errors.append(f"[{path}.name] is required")

    if "match" in item:
        return
    keywords = [str(v).strip() for v in _ensure_list(item.get("keywords")) if str(v).strip()]
    paths = [str(v).strip() for v in _ensure_list(item.get("path_candidates")) if str(v).strip()]
    if not keywords:
        errors.append(f"[{path}.keywords] must contain at least 1 value")
    if not paths:
        errors.append(f"[{path}.path_candidates] must contain at least 1 value")


def _validate_defaults(raw: object, errors: List[str]) -> None:
    if not isinstance(raw, dict):
        errors.append("[defaults] is required")
        return
    constraints = raw.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("[defaults.constraints] is required")
        return
    max_move = constraints.get("max_move_m")
    if not isinstance(max_move, (int, float)):
        errors.append("[defaults.constraints.max_move_m] must be a number")
    elif float(max_move) < 0:
        errors.append("[defaults.constraints.max_move_m] must be >= 0")
    z_move = constraints.get("z_move_allowed")
    if not isinstance(z_move, bool):
        errors.append("[defaults.constraints.z_move_allowed] must be boolean")


def _validate_input_rules(raw: object, errors: List[str], supported_check_types: set[str]) -> None:
    if not isinstance(raw, list) or not raw:
        errors.append("[rules] must contain at least 1 rule")
        return
    seen_ids: set[str] = set()
    for idx, rule in enumerate(raw):
        _validate_rule_common(rule, errors, f"rules[{idx}]", seen_ids, supported_check_types, input_mode=True)


def _validate_output_rules(raw: object, errors: List[str], supported_check_types: set[str]) -> None:
    if not isinstance(raw, list) or not raw:
        errors.append("[rules] must contain at least 1 rule")
        return
    seen_ids: set[str] = set()
    for idx, rule in enumerate(raw):
        _validate_rule_common(rule, errors, f"rules[{idx}]", seen_ids, supported_check_types, input_mode=False)


def _validate_rule_common(
    rule: object,
    errors: List[str],
    path: str,
    seen_ids: set[str],
    supported_check_types: set[str],
    *,
    input_mode: bool,
) -> None:
    if not isinstance(rule, dict):
        errors.append(f"[{path}] must be an object")
        return
    rule_id = str(rule.get("id") or "").strip()
    if not rule_id:
        errors.append(f"[{path}.id] is required")
    else:
        if not RULE_ID_RE.match(rule_id):
            errors.append(f"[{path}.id] must match ^[A-Z0-9_]+$")
        if rule_id in seen_ids:
            errors.append(f"[{path}.id] must be unique")
        seen_ids.add(rule_id)
    if not str(rule.get("title") or "").strip():
        errors.append(f"[{path}.title] is required")

    class_in, relation = _input_rule_applies(rule) if input_mode else _output_rule_applies(rule)
    applies_path = f"{path}.applies_to" if not input_mode else path
    if not class_in:
        errors.append(f"[{applies_path}.class_in] must contain at least 1 value")
    if not relation:
        errors.append(f"[{applies_path}.relation] must be a non-empty string")

    check = rule.get("check")
    if not isinstance(check, dict):
        errors.append(f"[{path}.check] is required")
    else:
        check_type = str(check.get("type") or "").strip().lower()
        if not check_type:
            errors.append(f"[{path}.check.type] is required")
        elif check_type not in supported_check_types:
            errors.append(f"[{path}.check.type] unsupported check type '{check_type}'")
        if check_type == "min_clearance":
            min_distance = check.get("min_distance_m")
            if not isinstance(min_distance, (int, float)):
                errors.append(f"[{path}.check.min_distance_m] is required for min_clearance")
            elif float(min_distance) < 0:
                errors.append(f"[{path}.check.min_distance_m] must be >= 0")

    severity = str(rule.get("severity") or "").strip().lower()
    if severity not in SEVERITY_VALUES:
        errors.append(f"[{path}.severity] must be one of {sorted(SEVERITY_VALUES)}")

    explain_short = _rule_explain_short(rule)
    if not explain_short:
        if input_mode:
            errors.append(f"[{path}.explain_short] is required")
        else:
            errors.append(f"[{path}.explain.short] is required")


def _input_rule_applies(rule: Dict[str, Any]) -> Tuple[List[str], str]:
    applies = rule.get("applies_to")
    if isinstance(applies, dict):
        class_in = [str(v).strip() for v in _ensure_list(applies.get("class_in")) if str(v).strip()]
        relation = str(applies.get("relation") or "").strip()
        return class_in, relation
    class_in = [str(v).strip() for v in _ensure_list(rule.get("class_in")) if str(v).strip()]
    relation = str(rule.get("relation") or "").strip()
    return class_in, relation


def _output_rule_applies(rule: Dict[str, Any]) -> Tuple[List[str], str]:
    applies = rule.get("applies_to")
    if not isinstance(applies, dict):
        return [], ""
    class_in = [str(v).strip() for v in _ensure_list(applies.get("class_in")) if str(v).strip()]
    relation = str(applies.get("relation") or "").strip()
    return class_in, relation


def _rule_explain_short(rule: Dict[str, Any]) -> str:
    if "explain_short" in rule and str(rule.get("explain_short") or "").strip():
        return str(rule.get("explain_short")).strip()
    explain = rule.get("explain")
    if isinstance(explain, dict):
        return str(explain.get("short") or "").strip()
    return ""


def build_trace_for_selection(element: Any, rulepack: Any) -> SelectionTrace:
    selected, peer, relation, measured_clearance_m = _unwrap_selection(element)

    class_specs = _extract_class_specs(rulepack)
    class_traces: List[ClassMatchTrace] = [_trace_class_match(selected, spec) for spec in class_specs]
    class_traces.sort(key=lambda trace: (trace.confidence, trace.matched, trace.classId), reverse=True)

    top_class_id = "Unknown"
    top_conf = 0.0
    if class_traces:
        top = class_traces[0]
        top_class_id = top.classId
        top_conf = float(top.confidence)

    selected_class = _element_class_id(selected) or (top_class_id if top_class_id != "Unknown" else None)
    peer_class = _element_class_id(peer)
    relation_norm = _relation_norm(relation)

    rule_specs = _extract_rule_specs(rulepack)
    apply_traces: List[RuleApplyTrace] = []
    check_traces: List[RuleCheckTrace] = []

    for rule_spec in rule_specs:
        rule_id = str(rule_spec.get("id") or "").strip() or "<missing>"
        class_in = [str(v).strip() for v in _ensure_list(rule_spec.get("class_in")) if str(v).strip()]
        rule_relation = _relation_norm(rule_spec.get("relation"))
        class_ok = False
        if peer is not None:
            class_ok = bool(selected_class and peer_class and selected_class in class_in and peer_class in class_in)
        else:
            class_ok = bool(selected_class and selected_class in class_in)
        relation_ok = rule_relation == "any" or relation_norm == rule_relation
        applicable = bool(class_ok and relation_ok)

        reason_parts: List[str] = []
        if class_ok:
            reason_parts.append("class_in matched")
        else:
            reason_parts.append("class_in did not match selection")
        if relation_ok:
            reason_parts.append(f"relation matched ({relation_norm})")
        else:
            reason_parts.append(f"relation mismatch (selection={relation_norm}, rule={rule_relation})")
        apply_trace = RuleApplyTrace(
            ruleId=rule_id,
            applicable=applicable,
            relation=rule_relation,
            classIn=class_in,
            reason="; ".join(reason_parts),
        )
        apply_traces.append(apply_trace)

        check_type = str(rule_spec.get("check_type") or "").strip().lower()
        threshold = dict(rule_spec.get("threshold") or {})
        input_values = {
            "measured_clearance_m": measured_clearance_m,
            "relation": relation_norm,
            "selected_class": selected_class,
            "peer_class": peer_class,
        }
        passed = False
        check_reason = "Rule not applicable."
        if check_type == "min_clearance":
            min_distance = threshold.get("min_distance_m")
            try:
                min_distance_f = float(min_distance)
            except (TypeError, ValueError):
                min_distance_f = None
            if not applicable:
                check_reason = "Rule check skipped because applies_to did not match."
            elif min_distance_f is None:
                check_reason = "Invalid rule threshold: min_distance_m missing."
            elif measured_clearance_m is None:
                check_reason = "Measured clearance unavailable for selected pair."
            else:
                passed = float(measured_clearance_m) >= min_distance_f
                if passed:
                    check_reason = (
                        f"Measured clearance {float(measured_clearance_m):.3f} m >= "
                        f"{float(min_distance_f):.3f} m"
                    )
                else:
                    check_reason = (
                        f"Measured clearance {float(measured_clearance_m):.3f} m < "
                        f"{float(min_distance_f):.3f} m"
                    )
        else:
            check_reason = f"Unsupported check type '{check_type}'."

        check_traces.append(
            RuleCheckTrace(
                ruleId=rule_id,
                checkType=check_type,
                inputValues=input_values,
                threshold=threshold,
                passed=passed,
                reason=check_reason,
            )
        )

    return SelectionTrace(
        topClassId=top_class_id,
        topConfidence=float(top_conf),
        classMatches=class_traces,
        ruleApplies=apply_traces,
        ruleChecks=check_traces,
    )


def _trace_class_match(element: Any, class_spec: Dict[str, Any]) -> ClassMatchTrace:
    class_id = str(class_spec.get("id") or "Unknown")
    signals_spec = class_spec.get("signals") or []
    traces: List[SignalTrace] = []
    scores: List[float] = []
    matched = False

    for signal in signals_spec:
        signal_type = str(signal.get("signalType") or "property_contains_any")
        path_candidates = [str(v).strip() for v in _ensure_list(signal.get("path_candidates")) if str(v).strip()]
        keywords = [str(v).strip() for v in _ensure_list(signal.get("keywords")) if str(v).strip()]
        tried_paths: List[str] = []
        matched_path: Optional[str] = None
        matched_value: Optional[str] = None
        keywords_hit: List[str] = []
        for path in path_candidates:
            tried_paths.append(path)
            for candidate_value in _collect_path_values(element, path):
                candidate_norm = _normalize_text(candidate_value)
                for keyword in keywords:
                    keyword_norm = _normalize_text(keyword)
                    if not keyword_norm:
                        continue
                    if keyword_norm in candidate_norm:
                        if keyword not in keywords_hit:
                            keywords_hit.append(keyword)
                        if matched_path is None:
                            matched_path = path
                            matched_value = candidate_value
        signal_matched = matched_path is not None
        if signal_matched:
            matched = True
        denom = len(keywords) if keywords else 1
        scores.append(min(1.0, len(keywords_hit) / float(denom)))
        if signal_matched:
            reason = (
                f"Matched {len(keywords_hit)} keyword(s) on path '{matched_path}'"
                f" using value '{matched_value}'."
            )
        else:
            reason = "No keyword matches found in the provided path candidates."
        traces.append(
            SignalTrace(
                signalType=signal_type,
                triedPaths=tried_paths,
                matchedPath=matched_path,
                matchedValue=matched_value,
                keywordsHit=keywords_hit,
                reason=reason,
            )
        )

    confidence = 0.0
    if scores:
        confidence = max(0.0, min(1.0, sum(scores) / float(len(scores))))
    if not matched:
        confidence = 0.0
    return ClassMatchTrace(classId=class_id, matched=matched, signals=traces, confidence=confidence)


def _unwrap_selection(element: Any) -> Tuple[Any, Any, str, Optional[float]]:
    if isinstance(element, dict):
        selected = element.get("element")
        peer = element.get("peer")
        relation = str(element.get("relation") or "any")
        measured = element.get("measured_clearance_m")
        measured_val: Optional[float]
        try:
            measured_val = float(measured) if measured is not None else None
        except (TypeError, ValueError):
            measured_val = None
        return selected, peer, relation, measured_val
    return element, None, "any", None


def _extract_class_specs(rulepack: Any) -> List[Dict[str, Any]]:
    if isinstance(rulepack, dict):
        return _class_specs_from_output(rulepack.get("classification"))

    explicit = getattr(rulepack, "classification_classes", None)
    if isinstance(explicit, list) and explicit:
        return _normalize_class_specs(explicit)

    return _class_specs_from_classifiers(getattr(rulepack, "classifiers", None))


def _extract_rule_specs(rulepack: Any) -> List[Dict[str, Any]]:
    if isinstance(rulepack, dict):
        return _rule_specs_from_output(rulepack.get("rules"))

    generated_rules = getattr(rulepack, "generated_rules", None)
    if isinstance(generated_rules, list) and generated_rules:
        return _normalize_rule_specs(generated_rules)

    utility_rules = getattr(rulepack, "utility_rules", None)
    if not isinstance(utility_rules, list):
        return []
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for utility_rule in utility_rules:
        rule_id = str(getattr(utility_rule, "rule_id", "") or "").strip()
        if not rule_id:
            continue
        key = f"{rule_id}|{getattr(utility_rule, 'relation', '')}|{getattr(utility_rule, 'utility_a', '')}|{getattr(utility_rule, 'utility_b', '')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": rule_id,
                "class_in": [
                    str(getattr(utility_rule, "utility_a", "") or ""),
                    str(getattr(utility_rule, "utility_b", "") or ""),
                ],
                "relation": _relation_norm(getattr(utility_rule, "relation", None)),
                "check_type": "min_clearance",
                "threshold": {"min_distance_m": float(getattr(utility_rule, "min_distance_m", 0.0) or 0.0)},
            }
        )
    return out


def _class_specs_from_output(raw_classification: object) -> List[Dict[str, Any]]:
    if not isinstance(raw_classification, dict):
        return []
    classes = raw_classification.get("classes")
    if not isinstance(classes, list):
        return []
    specs: List[Dict[str, Any]] = []
    for item in classes:
        if not isinstance(item, dict):
            continue
        class_id = str(item.get("id") or "").strip()
        if not class_id:
            continue
        signals: List[Dict[str, Any]] = []
        match = item.get("match")
        if isinstance(match, dict):
            for signal in _ensure_list(match.get("any")):
                if not isinstance(signal, dict):
                    continue
                payload = signal.get("property_contains_any")
                if not isinstance(payload, dict):
                    continue
                signals.append(
                    {
                        "signalType": "property_contains_any",
                        "path_candidates": [str(v).strip() for v in _ensure_list(payload.get("path_candidates")) if str(v).strip()],
                        "keywords": [str(v).strip() for v in _ensure_list(payload.get("values")) if str(v).strip()],
                    }
                )
        if not signals:
            keywords = [str(v).strip() for v in _ensure_list(item.get("keywords")) if str(v).strip()]
            paths = [str(v).strip() for v in _ensure_list(item.get("path_candidates")) if str(v).strip()]
            if keywords and paths:
                signals.append(
                    {
                        "signalType": "property_contains_any",
                        "path_candidates": paths,
                        "keywords": keywords,
                    }
                )
        specs.append({"id": class_id, "name": str(item.get("name") or class_id), "signals": signals})
    return specs


def _normalize_class_specs(raw_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for item in raw_specs:
        if not isinstance(item, dict):
            continue
        class_id = str(item.get("id") or "").strip()
        if not class_id:
            continue
        signals = []
        for signal in _ensure_list(item.get("signals")):
            if not isinstance(signal, dict):
                continue
            signals.append(
                {
                    "signalType": str(signal.get("signalType") or "property_contains_any"),
                    "path_candidates": [str(v).strip() for v in _ensure_list(signal.get("path_candidates")) if str(v).strip()],
                    "keywords": [str(v).strip() for v in _ensure_list(signal.get("keywords")) if str(v).strip()],
                }
            )
        specs.append({"id": class_id, "name": str(item.get("name") or class_id), "signals": signals})
    return specs


def _class_specs_from_classifiers(raw_classifiers: object) -> List[Dict[str, Any]]:
    if not isinstance(raw_classifiers, list):
        return []
    specs: List[Dict[str, Any]] = []
    for item in raw_classifiers:
        if not isinstance(item, dict):
            continue
        class_id = str(item.get("className") or item.get("name") or "").strip()
        if not class_id:
            continue
        signals: List[Dict[str, Any]] = []
        for matcher in _ensure_list(item.get("matchers")):
            if not isinstance(matcher, dict) or not matcher:
                continue
            key = str(next(iter(matcher.keys())))
            value = matcher.get(key)
            if key in ("propertyContainsAny", "property_contains_any") and isinstance(value, dict):
                signals.append(
                    {
                        "signalType": "property_contains_any",
                        "path_candidates": [str(v).strip() for v in _ensure_list(value.get("path_candidates")) if str(v).strip()],
                        "keywords": [str(v).strip() for v in _ensure_list(value.get("values")) if str(v).strip()],
                    }
                )
                continue
            values = [str(v).strip() for v in _ensure_list(value) if str(v).strip()]
            if not values:
                continue
            path_map = {
                "nameContainsAny": ["Name"],
                "typeNameContainsAny": ["Type.Name"],
                "systemContainsAny": ["System/Group"],
                "systemNameContainsAny": ["System/Group"],
                "systemGroupNameContainsAny": ["System/Group"],
                "ifcTypeIn": ["Item.ifcType"],
            }
            path_candidates = path_map.get(key)
            if not path_candidates:
                continue
            signals.append(
                {
                    "signalType": "property_contains_any",
                    "path_candidates": path_candidates,
                    "keywords": values,
                }
            )
        specs.append({"id": class_id, "name": class_id, "signals": signals})
    return specs


def _rule_specs_from_output(raw_rules: object) -> List[Dict[str, Any]]:
    if not isinstance(raw_rules, list):
        return []
    specs: List[Dict[str, Any]] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("id") or "").strip()
        if not rule_id:
            continue
        applies = item.get("applies_to")
        check = item.get("check")
        if not isinstance(applies, dict) or not isinstance(check, dict):
            continue
        class_in = [str(v).strip() for v in _ensure_list(applies.get("class_in")) if str(v).strip()]
        relation = str(applies.get("relation") or "").strip()
        check_type = str(check.get("type") or "").strip()
        threshold: Dict[str, Any] = {}
        if "min_distance_m" in check:
            threshold["min_distance_m"] = check.get("min_distance_m")
        specs.append(
            {
                "id": rule_id,
                "class_in": class_in,
                "relation": relation,
                "check_type": check_type,
                "threshold": threshold,
            }
        )
    return specs


def _normalize_rule_specs(raw_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("id") or "").strip()
        if not rule_id:
            continue
        specs.append(
            {
                "id": rule_id,
                "class_in": [str(v).strip() for v in _ensure_list(item.get("class_in")) if str(v).strip()],
                "relation": str(item.get("relation") or "").strip(),
                "check_type": str(item.get("check_type") or "").strip(),
                "threshold": dict(item.get("threshold") or {}),
            }
        )
    return specs


def _collect_path_values(element: Any, path: str) -> List[str]:
    if element is None:
        return []
    normalized = path.strip().lower()
    values: List[str] = []

    def add(value: object) -> None:
        text = str(value or "").strip()
        if text and text not in values:
            values.append(text)

    def add_many(items: object) -> None:
        if isinstance(items, (list, tuple, set)):
            for item in items:
                add(item)
        elif items is not None:
            add(items)

    meta = getattr(element, "ifc_meta", {}) or {}
    item_meta = meta.get("item") if isinstance(meta, dict) else None
    type_meta = meta.get("type") if isinstance(meta, dict) else None

    if normalized in ("system/group", "system", "group", "system/group.name"):
        add(getattr(element, "system", None))
        add_many(getattr(element, "systems", None))
        add_many(getattr(element, "system_group_names", None))
        if isinstance(meta, dict):
            add_many(meta.get("system_groups"))
            add_many(meta.get("systems"))
            item = meta.get("item")
            if isinstance(item, dict):
                for key in ("System/Group", "System / Group", "System"):
                    add(item.get(key))
        for pset_source in (getattr(element, "psets", None), getattr(element, "type_psets", None)):
            if not isinstance(pset_source, dict):
                continue
            for _pset_name, props in pset_source.items():
                if not isinstance(props, dict):
                    continue
                for key, value in props.items():
                    key_norm = str(key).strip().lower()
                    if key_norm in ("system/group", "system / group", "system"):
                        add(value)
        return values

    if normalized in ("name", "item.name"):
        add(getattr(element, "name", None))
        if isinstance(item_meta, dict):
            add(item_meta.get("Name"))
        return values

    if normalized in ("type.name", "typename", "type_name"):
        add(getattr(element, "type_name", None))
        if isinstance(type_meta, dict):
            add(type_meta.get("Name"))
        return values

    if normalized in ("item.ifctype", "ifctype"):
        add(getattr(element, "type", None))
        if isinstance(item_meta, dict):
            add(item_meta.get("ifcType"))
        return values

    if isinstance(meta, dict):
        for candidate in _try_meta_path(meta, path):
            add(candidate)
    return values


def _try_meta_path(meta: Dict[str, Any], path: str) -> List[str]:
    raw_parts = [part for part in re.split(r"[/.]", path) if part]
    if not raw_parts:
        return []
    current: List[Any] = [meta]
    for part in raw_parts:
        next_values: List[Any] = []
        key_norm = part.strip().lower()
        for value in current:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if str(key).strip().lower() == key_norm:
                        next_values.append(nested)
        if not next_values:
            return []
        current = next_values
    out: List[str] = []
    for value in current:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                text = str(item or "").strip()
                if text and text not in out:
                    out.append(text)
        else:
            text = str(value or "").strip()
            if text and text not in out:
                out.append(text)
    return out


def _element_class_id(element: Any) -> Optional[str]:
    if element is None:
        return None
    class_name = str(getattr(element, "class_name", "") or "").strip()
    if class_name and class_name.lower() != "unknown":
        return class_name
    utility = str(getattr(element, "utility_type", "") or "").strip()
    if utility and utility.lower() != "unknown":
        return utility
    return None


def _normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def _relation_norm(value: Optional[str]) -> str:
    relation = str(value or "").strip().lower()
    if relation in ("parallel", "crossing", "any"):
        return relation
    if not relation:
        return "any"
    return "any"


def _ensure_list(value: object) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
