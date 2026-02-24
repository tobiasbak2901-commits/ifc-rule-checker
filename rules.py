from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations_with_replacement
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from taxonomy import UtilityTaxonomy


RULEPACK_FILES = ("classifiers.yaml", "policy.yaml", "constraints.yaml", "clearances.yaml", "rules.yaml")


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


_TEXT_TRANSLATION = str.maketrans(
    {
        "\u00e6": "ae",  # æ
        "\u00f8": "oe",  # ø
        "\u00e5": "aa",  # å
    }
)


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return text.translate(_TEXT_TRANSLATION)


@dataclass
class UtilityDistanceRule:
    rule_id: str
    utility_a: str
    utility_b: str
    relation: str
    min_distance_m: float
    measure: str = "clear_distance"
    apply_to_set: Optional[str] = None
    apply_to_types: List[str] = field(default_factory=list)
    source: Dict[str, object] = field(default_factory=dict)
    standard_refs: List[str] = field(default_factory=list)


@dataclass
class RulePack:
    default_clearance_mm: float = 0.0
    clearance_tolerance_mm: float = 0.0
    default_max_move_mm: float = 0.0
    clearance_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    move_priority: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {"discipline": {}, "type": {}, "class": {}}
    )
    max_move: Dict[str, float] = field(default_factory=dict)
    protected_classes: List[str] = field(default_factory=list)
    allowed_axes: Dict[str, List[str]] = field(default_factory=dict)
    z_allowed: Dict[str, bool] = field(default_factory=dict)
    slope_enabled: bool = False
    min_slope_permille: float = 0.0
    slope_classes: List[str] = field(default_factory=list)
    classifiers: List[Dict] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)
    taxonomy: UtilityTaxonomy = field(default_factory=UtilityTaxonomy)
    utility_rules: List[UtilityDistanceRule] = field(default_factory=list)
    debug_classification: bool = False
    classification_classes: List[Dict[str, object]] = field(default_factory=list)
    generated_rules: List[Dict[str, object]] = field(default_factory=list)

    def clearance_mm(self, type_a: Optional[str], type_b: Optional[str]) -> float:
        value, _ = self.resolve_clearance_mm(type_a, type_b)
        return value

    def resolve_clearance_mm(self, type_a: Optional[str], type_b: Optional[str]) -> Tuple[float, str]:
        ta = _norm(type_a)
        tb = _norm(type_b)
        key = (ta, tb)
        if key in self.clearance_matrix:
            return self.clearance_matrix[key], f"{ta}|{tb}"
        key_rev = (tb, ta)
        if key_rev in self.clearance_matrix:
            return self.clearance_matrix[key_rev], f"{tb}|{ta}"
        wildcard_a = ("*", tb)
        if wildcard_a in self.clearance_matrix:
            return self.clearance_matrix[wildcard_a], f"*|{tb}"
        wildcard_b = (ta, "*")
        if wildcard_b in self.clearance_matrix:
            return self.clearance_matrix[wildcard_b], f"{ta}|*"
        wildcard = ("*", "*")
        if wildcard in self.clearance_matrix:
            return self.clearance_matrix[wildcard], "*|*"
        return self.default_clearance_mm, "defaultClearanceMm"

    def move_weight(self, discipline: Optional[str], ifc_type: Optional[str], class_name: Optional[str] = None) -> float:
        weight, _ = self.resolve_move_weight(discipline, ifc_type, class_name)
        return weight

    def resolve_move_weight(
        self, discipline: Optional[str], ifc_type: Optional[str], class_name: Optional[str] = None
    ) -> Tuple[float, List[Tuple[str, str, float]]]:
        d = _norm(discipline)
        t = _norm(ifc_type)
        c = _norm(class_name)
        weight = 0.0
        sources: List[Tuple[str, str, float]] = []
        if c and c in self.move_priority.get("class", {}):
            value = float(self.move_priority["class"][c])
            weight += value
            sources.append(("class", c, value))
        if d in self.move_priority.get("discipline", {}):
            value = float(self.move_priority["discipline"][d])
            weight += value
            sources.append(("discipline", d, value))
        if t in self.move_priority.get("type", {}):
            value = float(self.move_priority["type"][t])
            weight += value
            sources.append(("type", t, value))
        return weight, sources

    def max_move_mm(self, ifc_type: Optional[str], class_name: Optional[str] = None) -> float:
        value, _ = self.resolve_max_move_mm(ifc_type, class_name)
        return value

    def resolve_max_move_mm(self, ifc_type: Optional[str], class_name: Optional[str] = None) -> Tuple[float, str]:
        t = _norm(ifc_type)
        c = _norm(class_name)
        if c and c in self.max_move:
            return float(self.max_move[c]), c
        if t and t in self.max_move:
            return float(self.max_move[t]), t
        if "*" in self.max_move:
            return float(self.max_move["*"]), "*"
        return self.default_max_move_mm, "defaultMaxMoveMm"

    def allowed_axes_for(self, class_name: Optional[str], ifc_type: Optional[str] = None) -> Optional[List[str]]:
        axes, _ = self.resolve_allowed_axes(class_name, ifc_type)
        return axes

    def resolve_allowed_axes(self, class_name: Optional[str], ifc_type: Optional[str] = None) -> Tuple[Optional[List[str]], str]:
        c = _norm(class_name)
        t = _norm(ifc_type)
        if c and c in self.allowed_axes:
            return list(self.allowed_axes[c]), c
        if t and t in self.allowed_axes:
            return list(self.allowed_axes[t]), t
        if "*" in self.allowed_axes:
            return list(self.allowed_axes["*"]), "*"
        return None, "<none>"

    def z_allowed_for(self, class_name: Optional[str], ifc_type: Optional[str] = None) -> Optional[bool]:
        value, _ = self.resolve_z_allowed(class_name, ifc_type)
        return value

    def resolve_z_allowed(self, class_name: Optional[str], ifc_type: Optional[str] = None) -> Tuple[Optional[bool], str]:
        c = _norm(class_name)
        t = _norm(ifc_type)
        if c and c in self.z_allowed:
            return bool(self.z_allowed[c]), c
        if t and t in self.z_allowed:
            return bool(self.z_allowed[t]), t
        if "*" in self.z_allowed:
            return bool(self.z_allowed["*"]), "*"
        return None, "<none>"

    def slope_applies_to(self, class_name: Optional[str], ifc_type: Optional[str] = None) -> bool:
        if not self.slope_enabled:
            return False
        if not self.slope_classes:
            return True
        c = _norm(class_name)
        t = _norm(ifc_type)
        if c and c in self.slope_classes:
            return True
        if t and t in self.slope_classes:
            return True
        return "*" in self.slope_classes

    def is_protected(self, ifc_type: Optional[str]) -> bool:
        t = _norm(ifc_type)
        return t in self.protected_classes

    def utility_label(self, utility_key: Optional[str]) -> str:
        return self.taxonomy.label_for(utility_key)

    def has_utility_rules(self) -> bool:
        return bool(self.utility_rules)

    def resolve_min_distance_m(
        self, utility_a: Optional[str], utility_b: Optional[str], relation: Optional[str]
    ) -> Tuple[Optional[float], Optional[UtilityDistanceRule]]:
        rule = self.resolve_utility_rule(utility_a, utility_b, relation)
        if not rule:
            return None, None
        return float(rule.min_distance_m), rule

    def resolve_utility_rule(
        self, utility_a: Optional[str], utility_b: Optional[str], relation: Optional[str]
    ) -> Optional[UtilityDistanceRule]:
        ua = _norm(utility_a)
        ub = _norm(utility_b)
        rel = _relation_norm(relation)
        if not ua or not ub:
            return None
        best: Optional[UtilityDistanceRule] = None
        best_score = (-1, -1.0)
        for rule in self.utility_rules:
            pair = {rule.utility_a, rule.utility_b}
            if {ua, ub} != pair:
                continue
            relation_score = _relation_score(rel, rule.relation)
            if relation_score < 0:
                continue
            score = (relation_score, float(rule.min_distance_m))
            if score > best_score:
                best = rule
                best_score = score
        return best

    def classify(self, element) -> Dict:
        if self.taxonomy.enabled:
            utility_key, confidence, reasons = self.taxonomy.classify(element)
            if utility_key != "unknown":
                return {
                    "className": utility_key,
                    "utilityType": utility_key,
                    "confidence": confidence,
                    "reasons": reasons,
                }
        return _classify_element(element, self.classifiers)

    @classmethod
    def from_dict(cls, data: Dict) -> "RulePack":
        default_clearance_mm = float(data.get("defaultClearanceMm", data.get("default_clearance_mm", 0.0)))
        clearance_tolerance_mm = float(
            data.get("clearanceToleranceMm", data.get("clearance_tolerance_mm", 0.0)) or 0.0
        )
        default_max_move_mm = float(data.get("defaultMaxMoveMm", data.get("default_max_move_mm", 0.0)))
        matrix = _parse_clearance_matrix(data.get("clearanceMatrix", {}))
        move_priority = _parse_move_priority(data.get("movePriority", {}))
        max_move = _parse_max_move(data.get("maxMove", {}))
        allowed_axes = _parse_allowed_axes(data.get("allowedAxes", data.get("allowed_axes", {})))
        z_allowed = _parse_z_allowed(data.get("zAllowed", data.get("z_allowed", {})))
        slope_enabled, min_slope_permille, slope_classes = _parse_slope(data.get("slope", {}))
        protected = [_norm(v) for v in data.get("protectedClasses", []) if isinstance(v, str)]
        classification_classes = _parse_classification_classes(data.get("classification", {}))
        classifiers = _parse_classifiers(data.get("classifiers", {}))
        if not classifiers and classification_classes:
            classifiers = _classifiers_from_class_specs(classification_classes)
        metadata: Dict[str, object] = {}
        if isinstance(data.get("rulepack"), dict):
            metadata.update(data.get("rulepack"))
        if isinstance(data.get("metadata"), dict):
            metadata.update(data.get("metadata"))
        taxonomy = UtilityTaxonomy.from_dict(data.get("classification", {}))
        default_unit = _default_length_unit(data.get("defaults"))
        generated_rules = _parse_generated_rules(data.get("rules", []))
        utility_rules = _parse_utility_rules(data.get("rules", []), default_unit)
        utility_rules.extend(_utility_rules_from_generated_rules(generated_rules))
        debug_classification = _parse_debug_classification(metadata)
        return cls(
            default_clearance_mm=default_clearance_mm,
            clearance_tolerance_mm=clearance_tolerance_mm,
            default_max_move_mm=default_max_move_mm,
            clearance_matrix=matrix,
            move_priority=move_priority,
            max_move=max_move,
            protected_classes=protected,
            allowed_axes=allowed_axes,
            z_allowed=z_allowed,
            slope_enabled=slope_enabled,
            min_slope_permille=min_slope_permille,
            slope_classes=slope_classes,
            classifiers=classifiers,
            metadata=metadata,
            taxonomy=taxonomy,
            utility_rules=utility_rules,
            debug_classification=debug_classification,
            classification_classes=classification_classes,
            generated_rules=generated_rules,
        )


def _parse_clearance_matrix(raw) -> Dict[Tuple[str, str], float]:
    matrix: Dict[Tuple[str, str], float] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            type_a = _norm(item.get("typeA"))
            type_b = _norm(item.get("typeB"))
            value = item.get("mm")
            if type_a and type_b and isinstance(value, (int, float)):
                matrix[(type_a, type_b)] = float(value)
        return matrix
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                type_a = _norm(key)
                for key_b, val in value.items():
                    if isinstance(val, (int, float)):
                        matrix[(type_a, _norm(key_b))] = float(val)
                continue
            if isinstance(value, (int, float)):
                type_a, type_b = _split_pair(key)
                if type_a and type_b:
                    matrix[(type_a, type_b)] = float(value)
        return matrix
    return matrix


def _split_pair(key) -> Tuple[str, str]:
    if not isinstance(key, str):
        return "", ""
    for sep in ("|", ","):
        if sep in key:
            left, right = key.split(sep, 1)
            return _norm(left), _norm(right)
    return "", ""


def _parse_move_priority(raw) -> Dict[str, Dict[str, float]]:
    result = {"discipline": {}, "type": {}, "class": {}}
    if not isinstance(raw, dict):
        return result
    for group in ("discipline", "type", "class"):
        group_map = raw.get(group, {})
        if isinstance(group_map, dict):
            for key, value in group_map.items():
                if isinstance(value, (int, float)):
                    result[group][_norm(key)] = float(value)
    # Support flat keys like "discipline:Plumbing"
    for key, value in raw.items():
        if not isinstance(value, (int, float)) or not isinstance(key, str):
            continue
        if key.lower().startswith("discipline:"):
            result["discipline"][_norm(key.split(":", 1)[1])] = float(value)
        if key.lower().startswith("type:"):
            result["type"][_norm(key.split(":", 1)[1])] = float(value)
        if key.lower().startswith("class:"):
            result["class"][_norm(key.split(":", 1)[1])] = float(value)
    return result


def _parse_max_move(raw) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return result
    for key, value in raw.items():
        if isinstance(value, (int, float)):
            result[_norm(key)] = float(value)
    return result


def _parse_allowed_axes(raw) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    if not isinstance(raw, dict):
        return result
    for key, value in raw.items():
        axes = _normalize_axes(value)
        if axes:
            result[_norm(key)] = axes
    return result


def _parse_z_allowed(raw) -> Dict[str, bool]:
    result: Dict[str, bool] = {}
    if not isinstance(raw, dict):
        return result
    for key, value in raw.items():
        if isinstance(value, bool):
            result[_norm(key)] = value
    return result


def _parse_slope(raw) -> Tuple[bool, float, List[str]]:
    if isinstance(raw, dict):
        enabled = bool(raw.get("enabled", False))
        min_permille = float(raw.get("minSlopePermille", raw.get("min_slope_permille", 0.0)) or 0.0)
        classes = [_norm(v) for v in _ensure_list(raw.get("classes")) if isinstance(v, str) and _norm(v)]
        return enabled, min_permille, classes
    if isinstance(raw, bool):
        return raw, 0.0, []
    return False, 0.0, []


def _parse_utility_rules(raw, default_unit: str = "m") -> List[UtilityDistanceRule]:
    if not isinstance(raw, list):
        return []
    out: List[UtilityDistanceRule] = []
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        if _norm(item.get("type")) != "min_distance_between_utilities":
            continue
        applies = item.get("applies_to")
        constraint = item.get("constraint")
        if not isinstance(applies, dict) or not isinstance(constraint, dict):
            continue
        utility_a = _norm(applies.get("utility_a"))
        utility_b = _norm(applies.get("utility_b"))
        relation = _relation_norm(applies.get("relation"))
        if not utility_a or not utility_b:
            continue
        min_distance = constraint.get("min_distance")
        if not isinstance(min_distance, (int, float)):
            continue
        unit = _norm(constraint.get("unit") or default_unit or "m")
        measure = str(constraint.get("measure") or "clear_distance")
        min_distance_m = _to_meters(float(min_distance), unit)
        if min_distance_m <= 0:
            continue
        apply_to_set_raw = (
            item.get("applyToSet")
            or item.get("apply_to_set")
            or applies.get("applyToSet")
            or applies.get("apply_to_set")
        )
        apply_to_set = str(apply_to_set_raw).strip() if apply_to_set_raw else None
        apply_to_types_raw = (
            item.get("applyToTypes")
            or item.get("apply_to_types")
            or applies.get("applyToTypes")
            or applies.get("apply_to_types")
        )
        apply_to_types = [_norm(v) for v in _ensure_list(apply_to_types_raw) if _norm(v)]
        rule_id = str(item.get("rule_id") or item.get("id") or item.get("name") or f"utility_rule_{idx}")
        standard_refs_raw = list(item.get("standard_refs") or [])
        source_raw = dict(item.get("source") or {}) if isinstance(item.get("source"), dict) else {}
        if isinstance(source_raw, dict):
            standard_refs_raw.extend(list(source_raw.get("standard_refs") or []))
        standard_refs = [str(ref).strip() for ref in standard_refs_raw if str(ref).strip()]
        out.append(
            UtilityDistanceRule(
                rule_id=rule_id,
                utility_a=utility_a,
                utility_b=utility_b,
                relation=relation,
                min_distance_m=min_distance_m,
                measure=measure,
                apply_to_set=apply_to_set,
                apply_to_types=apply_to_types,
                source=source_raw,
                standard_refs=standard_refs,
            )
        )
    return out


def _default_length_unit(raw_defaults: object) -> str:
    if not isinstance(raw_defaults, dict):
        return "m"
    units = raw_defaults.get("units")
    if not isinstance(units, dict):
        return "m"
    return _norm(units.get("length") or "m")


def _to_meters(value: float, unit: str) -> float:
    u = _norm(unit)
    if u in ("m", "meter", "meters", "metre", "metres"):
        return value
    if u in ("mm", "millimeter", "millimeters", "millimetre", "millimetres"):
        return value / 1000.0
    if u in ("cm", "centimeter", "centimeters", "centimetre", "centimetres"):
        return value / 100.0
    return value


def _relation_norm(value: Optional[str]) -> str:
    raw = _norm(value)
    if raw in ("", "any", "*", "unknown"):
        return "any"
    if raw in ("parallel", "crossing"):
        return raw
    return "any"


def _relation_score(requested: str, available: str) -> int:
    req = _relation_norm(requested)
    have = _relation_norm(available)
    if have == req:
        return 3
    if have == "any":
        return 2
    if req == "any":
        return 1
    return -1


def _parse_debug_classification(metadata: Dict[str, object]) -> bool:
    if not isinstance(metadata, dict):
        return False
    direct = metadata.get("debug_classification")
    if isinstance(direct, bool):
        return direct
    debug = metadata.get("debug")
    if isinstance(debug, dict):
        nested = debug.get("classification")
        if isinstance(nested, bool):
            return nested
    return False


def _normalize_axes(value) -> List[str]:
    if value is None:
        return []
    items: List[str]
    if isinstance(value, str):
        items = [v.strip() for v in value.replace(",", " ").split()]
    elif isinstance(value, list):
        items = [str(v).strip() for v in value]
    else:
        return []
    axes = []
    for item in items:
        axis = item.lower()
        if axis in ("x", "y", "z"):
            axes.append(axis)
    return axes


def _parse_classifiers(raw) -> List[Dict]:
    if isinstance(raw, list):
        return [_normalize_classifier(item) for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("rules"), list):
            return _parse_classifiers(raw.get("rules"))
        for group_key in ("disciplines", "classes"):
            group = raw.get(group_key)
            if isinstance(group, dict):
                return _legacy_classifiers_to_rules(group)
    return []


def _parse_classification_classes(raw: object) -> List[Dict[str, object]]:
    if not isinstance(raw, dict):
        return []
    classes = raw.get("classes")
    if not isinstance(classes, list):
        return []
    out: List[Dict[str, object]] = []
    for item in classes:
        if not isinstance(item, dict):
            continue
        class_id = str(item.get("id") or "").strip()
        class_name = str(item.get("name") or class_id).strip() or class_id
        if not class_id:
            continue
        signals: List[Dict[str, object]] = []
        match = item.get("match")
        if isinstance(match, dict):
            any_rules = match.get("any")
            if isinstance(any_rules, list):
                for signal in any_rules:
                    if not isinstance(signal, dict):
                        continue
                    spec = signal.get("property_contains_any")
                    if not isinstance(spec, dict):
                        continue
                    paths = [str(v).strip() for v in _ensure_list(spec.get("path_candidates")) if str(v).strip()]
                    values = [str(v).strip() for v in _ensure_list(spec.get("values")) if str(v).strip()]
                    if paths and values:
                        signals.append(
                            {
                                "signalType": "property_contains_any",
                                "path_candidates": paths,
                                "keywords": values,
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
        if signals:
            out.append(
                {
                    "id": class_id,
                    "name": class_name,
                    "signals": signals,
                }
            )
    return out


def _classifiers_from_class_specs(class_specs: List[Dict[str, object]]) -> List[Dict]:
    classifiers: List[Dict] = []
    for spec in class_specs:
        class_id = str(spec.get("id") or "").strip()
        if not class_id:
            continue
        matchers: List[Dict] = []
        for signal in _ensure_list(spec.get("signals")):
            if not isinstance(signal, dict):
                continue
            path_candidates = [str(v).strip() for v in _ensure_list(signal.get("path_candidates")) if str(v).strip()]
            keywords = [str(v).strip() for v in _ensure_list(signal.get("keywords")) if str(v).strip()]
            if path_candidates and keywords:
                matchers.append(
                    {
                        "propertyContainsAny": {
                            "path_candidates": path_candidates,
                            "values": keywords,
                        }
                    }
                )
        if matchers:
            classifiers.append({"className": class_id, "matchers": matchers})
    return classifiers


def _parse_generated_rules(raw: object) -> List[Dict[str, object]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        applies_to = item.get("applies_to")
        check = item.get("check")
        if not isinstance(applies_to, dict) or not isinstance(check, dict):
            continue
        class_in = [str(v).strip() for v in _ensure_list(applies_to.get("class_in")) if str(v).strip()]
        relation = _relation_norm(applies_to.get("relation"))
        check_type = _norm(check.get("type"))
        if not class_in or check_type != "min_clearance":
            continue
        min_distance_m = check.get("min_distance_m")
        if not isinstance(min_distance_m, (int, float)):
            continue
        if float(min_distance_m) < 0:
            continue
        out.append(
            {
                "id": str(item.get("id") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "class_in": class_in,
                "relation": relation,
                "severity": str(item.get("severity") or "").strip(),
                "check_type": "min_clearance",
                "threshold": {"min_distance_m": float(min_distance_m)},
                "explain_short": str((item.get("explain") or {}).get("short") if isinstance(item.get("explain"), dict) else ""),
                "source": dict(item.get("source") or {}) if isinstance(item.get("source"), dict) else {},
                "standard_refs": [str(v).strip() for v in list(item.get("standard_refs") or []) if str(v).strip()],
            }
        )
    return out


def _utility_rules_from_generated_rules(generated_rules: List[Dict[str, object]]) -> List[UtilityDistanceRule]:
    out: List[UtilityDistanceRule] = []
    for item in generated_rules:
        class_in = [_norm(v) for v in _ensure_list(item.get("class_in")) if _norm(v)]
        if not class_in:
            continue
        relation = _relation_norm(item.get("relation"))
        threshold = item.get("threshold")
        if not isinstance(threshold, dict):
            continue
        min_distance_m = threshold.get("min_distance_m")
        if not isinstance(min_distance_m, (int, float)):
            continue
        standard_refs = [str(v).strip() for v in list(item.get("standard_refs") or []) if str(v).strip()]
        source = dict(item.get("source") or {}) if isinstance(item.get("source"), dict) else {}
        standard_refs.extend([str(v).strip() for v in list(source.get("standard_refs") or []) if str(v).strip()])
        for left, right in combinations_with_replacement(class_in, 2):
            out.append(
                UtilityDistanceRule(
                    rule_id=str(item.get("id") or "generated_rule"),
                    utility_a=left,
                    utility_b=right,
                    relation=relation,
                    min_distance_m=float(min_distance_m),
                    source=source,
                    standard_refs=standard_refs,
                )
            )
    return out


def _legacy_classifiers_to_rules(group: Dict) -> List[Dict]:
    rules: List[Dict] = []
    for name, spec in group.items():
        if not isinstance(spec, dict):
            continue
        matchers: List[Dict] = []
        ifc_types = spec.get("ifc_types") or spec.get("ifcTypeIn")
        if ifc_types:
            matchers.append({"ifcTypeIn": ifc_types})
        keywords = spec.get("keywords") or spec.get("nameContainsAny")
        if keywords:
            matchers.append({"nameContainsAny": keywords})
        systems = spec.get("systems") or spec.get("systemContainsAny")
        if systems:
            matchers.append({"systemContainsAny": systems})
        if matchers:
            rules.append({"className": name, "matchers": matchers})
    return rules


def _normalize_classifier(item: Dict) -> Dict:
    class_name = item.get("className") or item.get("name")
    matchers = item.get("matchers", [])
    if not isinstance(matchers, list):
        matchers = []
    return {"className": class_name, "matchers": matchers}


def _classify_element(element, classifiers: List[Dict]) -> Dict:
    best = {"className": "Unknown", "utilityType": "unknown", "confidence": 0.0, "reasons": []}
    for rule in classifiers:
        class_name = rule.get("className")
        matchers = rule.get("matchers", [])
        if not class_name or not isinstance(matchers, list) or not matchers:
            continue
        matched_reasons: List[str] = []
        for matcher in matchers:
            ok, reason = _eval_matcher(element, matcher)
            if ok and reason:
                matched_reasons.append(reason)
        if not matched_reasons:
            continue
        confidence = len(matched_reasons) / float(len(matchers))
        if confidence > best["confidence"]:
            class_name_text = str(class_name)
            best = {
                "className": class_name_text,
                "utilityType": _norm(class_name_text) if class_name_text else "unknown",
                "confidence": confidence,
                "reasons": matched_reasons,
            }
    return best


def _eval_matcher(element, matcher: Dict) -> Tuple[bool, str]:
    if not isinstance(matcher, dict) or not matcher:
        return False, ""
    key = next(iter(matcher.keys()))
    value = matcher.get(key)
    if key == "ifcTypeIn":
        return _match_ifc_type_in(element, value)
    if key == "nameContainsAny":
        return _match_contains_any("nameContainsAny", getattr(element, "name", ""), value)
    if key == "systemContainsAny":
        system_value = getattr(element, "system", None) or _system_from_psets(getattr(element, "psets", {}))
        return _match_contains_any("systemContainsAny", system_value, value)
    if key == "systemNameContainsAny":
        systems = getattr(element, "systems", None) or []
        return _match_contains_any("systemNameContainsAny", systems, value)
    if key == "systemGroupNameContainsAny":
        systems = getattr(element, "system_group_names", None) or []
        return _match_contains_any("systemGroupNameContainsAny", systems, value)
    if key == "systemGroupNameNotContainsAny":
        systems = getattr(element, "system_group_names", None) or []
        return _match_contains_any_negative("systemGroupNameContainsAny", systems, value)
    if key == "typeNameContainsAny":
        type_name = getattr(element, "type_name", None) or _type_name_from_meta(getattr(element, "ifc_meta", {}))
        return _match_contains_any("typeNameContainsAny", type_name, value)
    if key == "psetEqualsAny":
        return _match_pset_equals_any(element, value)
    if key == "psetValueContainsAny":
        return _match_pset_value_contains_any(element, value)
    if key in ("propertyContainsAny", "property_contains_any"):
        return _match_property_contains_any(element, value)
    return False, ""


def _match_ifc_type_in(element, values) -> Tuple[bool, str]:
    items = _ensure_list(values)
    if not items:
        return False, ""
    ifc_type = getattr(element, "type", "") or ""
    for item in items:
        if _norm(ifc_type) == _norm(str(item)):
            return True, f"ifcTypeIn: {ifc_type}"
    return False, ""


def _match_contains_any(label: str, haystack, values) -> Tuple[bool, str]:
    if not haystack:
        return False, ""
    items = _ensure_list(values)
    if not items:
        return False, ""
    if isinstance(haystack, (list, tuple, set)):
        candidates = [(str(v), _normalize_text(v)) for v in haystack if v]
    else:
        candidates = [(str(haystack), _normalize_text(haystack))]
    for item in items:
        needle = _normalize_text(item)
        needle_raw = str(item)
        if not needle:
            continue
        for candidate_raw, candidate_norm in candidates:
            if needle in candidate_norm:
                return True, f"{label}: '{needle_raw}' in '{candidate_raw}'"
    return False, ""


def _match_contains_any_negative(label: str, haystack, values) -> Tuple[bool, str]:
    ok, reason = _match_contains_any(label, haystack, values)
    if not ok:
        return False, ""
    return True, f"NEG: {reason}"


def _match_property_contains_any(element, spec) -> Tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, ""
    paths = [str(v).strip() for v in _ensure_list(spec.get("path_candidates")) if str(v).strip()]
    values = [str(v).strip() for v in _ensure_list(spec.get("values")) if str(v).strip()]
    if not paths or not values:
        return False, ""
    for path in paths:
        for candidate in _property_path_values(element, path):
            candidate_norm = _normalize_text(candidate)
            for keyword in values:
                keyword_norm = _normalize_text(keyword)
                if not keyword_norm:
                    continue
                if keyword_norm in candidate_norm:
                    return True, f"propertyContainsAny: '{keyword}' in {path}='{candidate}'"
    return False, ""


def _property_path_values(element, path: str) -> List[str]:
    values: List[str] = []
    if not path:
        return values

    def add(value):
        text = str(value or "").strip()
        if text and text not in values:
            values.append(text)

    def add_many(items):
        if isinstance(items, (list, tuple, set)):
            for item in items:
                add(item)
        elif items is not None:
            add(items)

    normalized = path.strip().lower()
    meta = getattr(element, "ifc_meta", {}) or {}
    item_meta = meta.get("item") if isinstance(meta, dict) else {}
    type_meta = meta.get("type") if isinstance(meta, dict) else {}

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
        add_many(_meta_path_values(meta, path))
    return values


def _meta_path_values(meta: Dict[str, Any], path: str) -> List[str]:
    parts = [part for part in path.replace("/", ".").split(".") if part]
    if not parts:
        return []
    current: List[Any] = [meta]
    for part in parts:
        key_norm = part.strip().lower()
        next_values: List[Any] = []
        for value in current:
            if not isinstance(value, dict):
                continue
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
            continue
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _type_name_from_meta(meta: Dict) -> str:
    if not isinstance(meta, dict):
        return ""
    type_meta = meta.get("type") or {}
    name = type_meta.get("Name")
    return str(name) if name else ""


def _match_pset_value_contains_any(element, spec) -> Tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, ""
    keys = _ensure_list(spec.get("keys"))
    values = _ensure_list(spec.get("values"))
    if not keys or not values:
        return False, ""
    keys_norm = [str(k).lower() for k in keys]
    values_norm = [(_normalize_text(v), str(v)) for v in values]
    pset_sources = []
    psets = getattr(element, "psets", {}) or {}
    type_psets = getattr(element, "type_psets", {}) or {}
    if isinstance(psets, dict):
        pset_sources.append(("pset", psets))
    if isinstance(type_psets, dict):
        pset_sources.append(("type_pset", type_psets))
    for source_name, source in pset_sources:
        for pset_name, props in source.items():
            if not isinstance(props, dict):
                continue
            for key, value in props.items():
                key_str = str(key)
                if key_str.lower() not in keys_norm:
                    continue
                if value is None:
                    continue
                hay = _normalize_text(value)
                for needle_norm, needle_raw in values_norm:
                    if needle_norm and needle_norm in hay:
                        return True, f"{source_name}:{pset_name}.{key_str} contains '{needle_raw}'"
    return False, ""


def _match_pset_equals_any(element, spec) -> Tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, ""
    pset = spec.get("pset")
    prop = spec.get("prop")
    contains_any = spec.get("containsAny")
    if not pset or not prop:
        return False, ""
    value = _pset_prop_value(getattr(element, "psets", {}), str(pset), str(prop))
    if value is None:
        return False, ""
    items = _ensure_list(contains_any)
    if not items:
        return False, ""
    val_text = _normalize_text(value)
    for item in items:
        needle = _normalize_text(item)
        if needle and needle in val_text:
            return True, f"psetEqualsAny: {pset}.{prop}={value}"
    return False, ""


def _ensure_list(values) -> List:
    if values is None:
        return []
    if isinstance(values, list):
        return values
    return [values]


def _pset_prop_value(psets: Dict, pset: str, prop: str):
    if not isinstance(psets, dict):
        return None
    pset_key = None
    for name in psets.keys():
        if isinstance(name, str) and name.lower() == pset.lower():
            pset_key = name
            break
    if not pset_key:
        return None
    props = psets.get(pset_key)
    if not isinstance(props, dict):
        return None
    for key, value in props.items():
        if isinstance(key, str) and key.lower() == prop.lower():
            return value
    return None


def _system_from_psets(psets: Dict) -> Optional[str]:
    if not isinstance(psets, dict):
        return None
    for props in psets.values():
        if not isinstance(props, dict):
            continue
        for key, value in props.items():
            if value is None:
                continue
            if "system" in str(key).lower():
                return str(value)
    return None


def load_rulepack(path: Path) -> RulePack:
    data = _load_rulepack_data(path)
    return RulePack.from_dict(data)


def _load_rulepack_data(path: Path) -> Dict:
    if path.is_dir():
        return _load_rulepack_bundle(path)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yml", ".yaml"):
        try:
            import yaml
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("YAML rulepack requires PyYAML (pip install pyyaml)") from exc
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("RulePack YAML must be a mapping")
        return data
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("RulePack JSON must be a mapping")
    return data


def _load_rulepack_bundle(path: Path) -> Dict:
    default_dir = path / "default" if (path / "default").is_dir() else path
    override_dir = None
    for candidate in (path / "override", path / "overrides"):
        if candidate.is_dir():
            override_dir = candidate
            break

    try:
        import yaml
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("YAML rulepack requires PyYAML (pip install pyyaml)") from exc

    data: Dict = {}
    for filename in RULEPACK_FILES:
        base_part = _load_yaml_mapping(default_dir / filename, yaml)
        override_part = _load_yaml_mapping(override_dir / filename, yaml) if override_dir else {}
        merged_part = _deep_merge(base_part, override_part)
        data = _deep_merge(data, merged_part)
    return data


def _load_yaml_mapping(path: Optional[Path], yaml_module) -> Dict:
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data = yaml_module.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"RulePack YAML must be a mapping ({path})")
    return data


def _deep_merge(base: Dict, override: Dict) -> Dict:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_rulepack(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists() and path.is_file():
            return path
        if path.exists() and path.is_dir() and _looks_like_rulepack_dir(path):
            return path
    return None


def _looks_like_rulepack_dir(path: Path) -> bool:
    for root in (path, path / "default"):
        if not root.is_dir():
            continue
        for filename in RULEPACK_FILES:
            if (root / filename).exists():
                return True
    return False
