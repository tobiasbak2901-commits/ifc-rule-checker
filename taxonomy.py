from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional, Tuple


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


@dataclass
class UtilityDefinition:
    key: str
    label: str
    patterns: List[re.Pattern] = field(default_factory=list)
    pattern_texts: List[str] = field(default_factory=list)


@dataclass
class UtilityTaxonomy:
    definitions: Dict[str, UtilityDefinition] = field(default_factory=dict)
    order: List[str] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return bool(self.order)

    def class_names(self) -> List[str]:
        return list(self.order)

    def label_for(self, utility_key: Optional[str]) -> str:
        key = _norm(utility_key)
        if not key:
            return "Unknown"
        definition = self.definitions.get(key)
        if definition and definition.label:
            return definition.label
        if key.upper() == key:
            return key
        if len(key) <= 4:
            return key.upper()
        return key.replace("_", " ").title()

    def classify(self, element) -> Tuple[str, float, List[str]]:
        if not self.enabled:
            return "unknown", 0.0, []
        candidates = _candidate_texts(element)
        for key in self.order:
            definition = self.definitions.get(key)
            if not definition:
                continue
            for source_name, source_value in candidates:
                for idx, pattern in enumerate(definition.patterns):
                    if pattern.search(source_value):
                        pattern_text = definition.pattern_texts[idx] if idx < len(definition.pattern_texts) else pattern.pattern
                        reason = f"{source_name}: /{pattern_text}/ in '{source_value}'"
                        return key, 1.0, [reason]
        return "unknown", 0.0, []

    @classmethod
    def from_dict(cls, data: object) -> "UtilityTaxonomy":
        if not isinstance(data, dict):
            return cls()
        raw_utilities = data.get("utilities")
        if isinstance(raw_utilities, dict):
            return _taxonomy_from_utilities_dict(raw_utilities)
        raw_mappings = data.get("mappings")
        if isinstance(raw_mappings, list):
            return _taxonomy_from_mappings_list(raw_mappings)
        return cls()


def _taxonomy_from_utilities_dict(raw_utilities: Dict[object, object]) -> UtilityTaxonomy:
    definitions: Dict[str, UtilityDefinition] = {}
    order: List[str] = []
    for key, spec in raw_utilities.items():
        utility_key = _norm(str(key))
        if not utility_key:
            continue
        label, patterns_text = _parse_utility_spec(utility_key, spec)
        compiled, accepted_texts = _compile_patterns(patterns_text)
        if not compiled:
            continue
        definitions[utility_key] = UtilityDefinition(
            key=utility_key,
            label=label,
            patterns=compiled,
            pattern_texts=accepted_texts,
        )
        order.append(utility_key)
    return UtilityTaxonomy(definitions=definitions, order=order)


def _taxonomy_from_mappings_list(raw_mappings: List[object]) -> UtilityTaxonomy:
    definitions: Dict[str, UtilityDefinition] = {}
    order: List[str] = []
    for item in raw_mappings:
        if not isinstance(item, dict):
            continue
        utility_key = _norm(str(item.get("utility") or ""))
        if not utility_key:
            continue
        default_label = utility_key.upper() if len(utility_key) <= 4 else utility_key.replace("_", " ").title()
        label = str(item.get("label") or default_label)
        patterns_text: List[str] = []
        match = item.get("match")
        if isinstance(match, dict):
            for key in ("any_regex", "regex", "patterns"):
                patterns_text.extend(_as_strings(match.get(key)))
        patterns_text.extend(_as_strings(item.get("regex")))
        compiled, accepted_texts = _compile_patterns(patterns_text)
        if not compiled:
            continue
        definitions[utility_key] = UtilityDefinition(
            key=utility_key,
            label=label,
            patterns=compiled,
            pattern_texts=accepted_texts,
        )
        if utility_key not in order:
            order.append(utility_key)
    return UtilityTaxonomy(definitions=definitions, order=order)


def _compile_patterns(patterns_text: List[str]) -> Tuple[List[re.Pattern], List[str]]:
    compiled: List[re.Pattern] = []
    accepted_texts: List[str] = []
    for pattern_text in patterns_text:
        if not pattern_text:
            continue
        try:
            compiled.append(re.compile(pattern_text, re.IGNORECASE))
            accepted_texts.append(pattern_text)
        except re.error:
            continue
    return compiled, accepted_texts


def _parse_utility_spec(utility_key: str, spec: object) -> Tuple[str, List[str]]:
    label = utility_key.upper() if len(utility_key) <= 4 else utility_key.replace("_", " ").title()
    if isinstance(spec, str):
        return label, [spec]
    if isinstance(spec, list):
        return label, [str(item) for item in spec]
    if not isinstance(spec, dict):
        return label, []
    label = str(spec.get("label") or label)
    patterns: List[str] = []
    for key in (
        "system_group_regex",
        "systemGroupRegex",
        "regex",
        "patterns",
        "matchers",
        "system_regex",
        "systemRegex",
        "group_regex",
        "groupRegex",
    ):
        value = spec.get(key)
        patterns.extend(_as_strings(value))
    return label, patterns


def _as_strings(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _candidate_texts(element) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []

    def add_many(name: str, values: Iterable[object]):
        for value in values:
            text = str(value or "").strip()
            if text:
                out.append((name, text))

    def add_one(name: str, value: object):
        text = str(value or "").strip()
        if text:
            out.append((name, text))

    add_one("system", getattr(element, "system", None))
    add_many("systems", getattr(element, "systems", None) or [])
    add_many("system_group", getattr(element, "system_group_names", None) or [])
    meta = getattr(element, "ifc_meta", {}) or {}
    if isinstance(meta, dict):
        add_many("meta.system_groups", meta.get("system_groups") or [])
        add_many("meta.systems", meta.get("systems") or [])
        item = meta.get("item") or {}
        if isinstance(item, dict):
            add_one("meta.item.Name", item.get("Name"))
            add_one("meta.item.ObjectType", item.get("ObjectType"))
    add_one("type_name", getattr(element, "type_name", None))
    add_one("name", getattr(element, "name", None))
    return out
