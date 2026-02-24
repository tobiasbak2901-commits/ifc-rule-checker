from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from models import Element, Issue


@dataclass(frozen=True)
class ObjectTreeNode:
    id: str
    label: str
    icon: Optional[str] = None
    count: Optional[int] = None
    children: Tuple["ObjectTreeNode", ...] = tuple()
    element_ids: Tuple[str, ...] = tuple()


_FRIENDLY_ITEM_TYPE_ALIASES: Dict[str, str] = {
    "ifcflowsegment": "MEP Segments",
    "ifcpipesegment": "Pipes",
    "ifcductsegment": "Ducts",
    "ifccablecarriersegment": "Cable Trays",
    "ifcflowfitting": "Fittings",
    "ifcvalve": "Valves",
    "ifcpump": "Equipment",
    "ifcfan": "Equipment",
    "ifcwall": "Walls",
    "ifcslab": "Slabs",
}


def friendly_item_type_label(ifc_type: object) -> str:
    raw = str(ifc_type or "").strip()
    if not raw:
        return "Unknown Type"
    return _FRIENDLY_ITEM_TYPE_ALIASES.get(raw.lower(), raw)


def build_by_file_nodes(
    elements: Dict[str, Element],
    *,
    default_file_label: str,
) -> List[ObjectTreeNode]:
    if not elements:
        return [
            ObjectTreeNode(
                id="by-file:empty-model",
                label="Load a model to browse objects",
            )
        ]

    buckets: Dict[str, Dict[str, Dict[str, List[Element]]]] = {}
    for elem in elements.values():
        guid = str(getattr(elem, "guid", "") or "").strip()
        if not guid:
            continue
        file_label = _element_file_label(elem, default_file_label)
        scope_label = _element_scope_label(elem)
        item_type_label = friendly_item_type_label(getattr(elem, "type", ""))
        (
            buckets
            .setdefault(file_label, {})
            .setdefault(scope_label, {})
            .setdefault(item_type_label, [])
            .append(elem)
        )

    root_nodes: List[ObjectTreeNode] = []
    for file_label in sorted(buckets.keys(), key=str.lower):
        scope_map = buckets[file_label]
        scope_nodes: List[ObjectTreeNode] = []
        file_guids: List[str] = []
        for scope_label in sorted(scope_map.keys(), key=str.lower):
            type_map = scope_map[scope_label]
            type_nodes: List[ObjectTreeNode] = []
            scope_guids: List[str] = []
            for item_type_label in sorted(type_map.keys(), key=str.lower):
                elems = sorted(type_map[item_type_label], key=_element_sort_key)
                elem_nodes: List[ObjectTreeNode] = []
                type_guids: List[str] = []
                for elem in elems:
                    guid = str(getattr(elem, "guid", "") or "").strip()
                    if not guid:
                        continue
                    type_guids.append(guid)
                    elem_nodes.append(
                        ObjectTreeNode(
                            id=f"by-file:element:{guid}",
                            label=_element_label(elem),
                            element_ids=(guid,),
                        )
                    )
                scope_guids.extend(type_guids)
                type_nodes.append(
                    ObjectTreeNode(
                        id=f"by-file:type:{file_label}:{scope_label}:{item_type_label}",
                        label=item_type_label,
                        count=len(type_guids),
                        children=tuple(elem_nodes),
                        element_ids=tuple(_dedupe(type_guids)),
                    )
                )
            file_guids.extend(scope_guids)
            scope_nodes.append(
                ObjectTreeNode(
                    id=f"by-file:scope:{file_label}:{scope_label}",
                    label=scope_label,
                    count=len(scope_guids),
                    children=tuple(type_nodes),
                    element_ids=tuple(_dedupe(scope_guids)),
                )
            )
        root_nodes.append(
            ObjectTreeNode(
                id=f"by-file:file:{file_label}",
                label=file_label,
                count=len(file_guids),
                children=tuple(scope_nodes),
                element_ids=tuple(_dedupe(file_guids)),
            )
        )
    return root_nodes


def build_ai_view_nodes(
    elements: Dict[str, Element],
    issues: Sequence[Issue],
    *,
    active_test_name: str,
    class_labels: Dict[str, str],
    recent_selected: Optional[Sequence[str]] = None,
    include_recent: bool = True,
) -> List[ObjectTreeNode]:
    if not elements:
        return [
            ObjectTreeNode(
                id="ai:empty-model",
                label="Load a model to browse objects",
            )
        ]

    nodes: List[ObjectTreeNode] = []
    clashing = _build_clashing_node(elements, list(issues), active_test_name)
    nodes.append(clashing)

    unclassified_guids = [
        guid
        for guid, elem in elements.items()
        if is_element_unclassified(elem, class_labels.get(guid, ""))
    ]
    unclassified_children: List[ObjectTreeNode] = []
    if unclassified_guids:
        for guid in sorted(unclassified_guids, key=lambda current: _element_label(elements.get(current)).lower()):
            elem = elements.get(guid)
            unclassified_children.append(
                ObjectTreeNode(
                    id=f"ai:unclassified:element:{guid}",
                    label=_element_label(elem),
                    element_ids=(guid,),
                )
            )
    else:
        unclassified_children.append(
            ObjectTreeNode(id="ai:unclassified:empty", label="All elements classified ✅")
        )
    nodes.append(
        ObjectTreeNode(
            id="ai:unclassified",
            label="Unclassified elements",
            count=len(unclassified_guids),
            children=tuple(unclassified_children),
            element_ids=tuple(_dedupe(unclassified_guids)),
        )
    )

    nodes.append(_build_high_risk_systems_node(elements, list(issues)))

    if include_recent:
        recent_nodes = _build_recent_node(elements, recent_selected or [])
        if recent_nodes is not None:
            nodes.append(recent_nodes)

    return nodes


def is_element_unclassified(elem: Element, class_label: str) -> bool:
    label = str(class_label or "").strip().lower()
    missing_class = (not label) or label in {"unknown", "classification_unknown", "unclassified", "none"}
    missing_type = not bool(str(getattr(elem, "type", "") or "").strip())
    missing_system = len(_element_system_names(elem)) == 0
    return bool(missing_class or missing_type or missing_system)


def _build_clashing_node(elements: Dict[str, Element], issues: List[Issue], active_test_name: str) -> ObjectTreeNode:
    clashing_guids: List[str] = []
    groups: Dict[str, Dict[str, object]] = {}
    for issue in issues:
        for guid in _issue_guids(issue):
            clashing_guids.append(guid)
        group_label = _issue_group_label(issue)
        entry = groups.setdefault(group_label, {"count": 0, "guids": []})
        entry["count"] = int(entry.get("count", 0)) + 1
        issue_group_guids = [guid for guid in _issue_guids(issue)]
        entry_guids = entry.get("guids") or []
        if isinstance(entry_guids, list):
            entry_guids.extend(issue_group_guids)

    unique_clashing = _dedupe(clashing_guids)
    if not issues:
        return ObjectTreeNode(
            id="ai:clashing",
            label="Clashing elements",
            count=0,
            children=(
                ObjectTreeNode(
                    id="ai:clashing:empty",
                    label="Run a clash test to populate Clashing elements",
                ),
            ),
            element_ids=tuple(),
        )

    top_group_nodes: List[ObjectTreeNode] = []
    sorted_groups = sorted(
        groups.items(),
        key=lambda item: (-int((item[1] or {}).get("count", 0)), str(item[0]).lower()),
    )
    for group_label, data in sorted_groups[:10]:
        raw_guids = list(data.get("guids") or []) if isinstance(data, dict) else []
        top_group_nodes.append(
            ObjectTreeNode(
                id=f"ai:clashing:group:{group_label}",
                label=group_label,
                count=int(data.get("count", 0)) if isinstance(data, dict) else 0,
                element_ids=tuple(_dedupe(raw_guids)),
            )
        )

    clashing_element_nodes: List[ObjectTreeNode] = []
    for guid in sorted(unique_clashing, key=lambda current: _element_label(elements.get(current)).lower()):
        elem = elements.get(guid)
        clashing_element_nodes.append(
            ObjectTreeNode(
                id=f"ai:clashing:element:{guid}",
                label=_element_label(elem),
                element_ids=(guid,),
            )
        )

    test_node = ObjectTreeNode(
        id="ai:clashing:active-test",
        label=f"Active test: {active_test_name}",
        count=len(issues),
        children=(
            ObjectTreeNode(
                id="ai:clashing:top-groups",
                label="Top groups",
                count=len(top_group_nodes),
                children=tuple(top_group_nodes) if top_group_nodes else (
                    ObjectTreeNode(id="ai:clashing:top-groups:none", label="(none)"),
                ),
                element_ids=tuple(unique_clashing),
            ),
            ObjectTreeNode(
                id="ai:clashing:elements",
                label="Elements",
                count=len(unique_clashing),
                children=tuple(clashing_element_nodes),
                element_ids=tuple(unique_clashing),
            ),
        ),
        element_ids=tuple(unique_clashing),
    )

    return ObjectTreeNode(
        id="ai:clashing",
        label="Clashing elements",
        count=len(unique_clashing),
        children=(test_node,),
        element_ids=tuple(unique_clashing),
    )


def _build_high_risk_systems_node(elements: Dict[str, Element], issues: List[Issue]) -> ObjectTreeNode:
    if not issues:
        return ObjectTreeNode(
            id="ai:high-risk",
            label="High-risk systems",
            count=0,
            children=(
                ObjectTreeNode(
                    id="ai:high-risk:empty",
                    label="Run a clash test to populate Clashing elements",
                ),
            ),
            element_ids=tuple(),
        )

    bucket_counts: Dict[str, int] = {}
    bucket_guids: Dict[str, List[str]] = {}
    for issue in issues:
        issue_buckets: set[str] = set()
        issue_guids: List[str] = []
        for guid in _issue_guids(issue):
            elem = elements.get(guid)
            issue_guids.append(guid)
            for bucket in _element_risk_buckets(elem):
                issue_buckets.add(bucket)
                bucket_guids.setdefault(bucket, []).append(guid)
        for bucket in issue_buckets:
            bucket_counts[bucket] = int(bucket_counts.get(bucket, 0)) + 1

    sorted_buckets = sorted(bucket_counts.items(), key=lambda item: (-int(item[1]), str(item[0]).lower()))
    children: List[ObjectTreeNode] = []
    all_bucket_guids: List[str] = []
    for bucket, clash_count in sorted_buckets:
        guids = _dedupe(bucket_guids.get(bucket, []))
        all_bucket_guids.extend(guids)
        children.append(
            ObjectTreeNode(
                id=f"ai:high-risk:bucket:{bucket}",
                label=bucket,
                count=int(clash_count),
                element_ids=tuple(guids),
            )
        )

    if not children:
        children = [ObjectTreeNode(id="ai:high-risk:none", label="(none)")]

    return ObjectTreeNode(
        id="ai:high-risk",
        label="High-risk systems",
        count=len(children) if children and children[0].id != "ai:high-risk:none" else 0,
        children=tuple(children),
        element_ids=tuple(_dedupe(all_bucket_guids)),
    )


def _build_recent_node(elements: Dict[str, Element], recent_selected: Sequence[str]) -> Optional[ObjectTreeNode]:
    recent = [guid for guid in _dedupe(recent_selected) if guid in elements][:10]
    if not recent:
        return None
    children = [
        ObjectTreeNode(
            id=f"ai:recent:element:{guid}",
            label=_element_label(elements.get(guid)),
            element_ids=(guid,),
        )
        for guid in recent
    ]
    return ObjectTreeNode(
        id="ai:recent",
        label="Recently selected",
        count=len(children),
        children=tuple(children),
        element_ids=tuple(recent),
    )


def _element_file_label(elem: Element, default_file_label: str) -> str:
    meta = getattr(elem, "ifc_meta", {}) or {}
    if isinstance(meta, dict):
        for key in (
            "source_file",
            "sourceFile",
            "model_file",
            "modelFile",
            "model_ref",
            "modelRef",
            "ifc_file",
            "ifcFile",
            "file",
            "source",
        ):
            value = str(meta.get(key, "") or "").strip()
            if value:
                return Path(value).name or value
    value = str(default_file_label or "").strip()
    return value or "Model file"


def _element_scope_label(elem: Element) -> str:
    systems = _element_system_names(elem)
    if systems:
        return f"System: {systems[0]}"
    discipline = str(getattr(elem, "discipline", "") or "").strip()
    if discipline and discipline.lower() != "unknown":
        return f"Discipline: {discipline}"
    return "Discipline: Unassigned"


def _element_label(elem: Optional[Element]) -> str:
    if elem is None:
        return "(unknown element)"
    guid = str(getattr(elem, "guid", "") or "").strip()
    name = str(getattr(elem, "name", "") or "").strip()
    if name and guid and name != guid:
        return f"{name} ({guid})"
    if guid:
        return guid
    return "(unknown element)"


def _element_sort_key(elem: Element) -> Tuple[str, str]:
    return (
        str(getattr(elem, "name", "") or "").strip().lower(),
        str(getattr(elem, "guid", "") or "").strip().lower(),
    )


def _issue_guids(issue: Issue) -> List[str]:
    guids: List[str] = []
    guid_a = str(getattr(issue, "guid_a", "") or "").strip()
    guid_b = str(getattr(issue, "guid_b", "") or "").strip()
    if guid_a:
        guids.append(guid_a)
    if guid_b:
        guids.append(guid_b)
    return guids


def _issue_group_label(issue: Issue) -> str:
    diag = getattr(issue, "clash_diagnostics", {}) or {}
    if not isinstance(diag, dict):
        return "Ungrouped"
    group = diag.get("group") or {}
    if not isinstance(group, dict):
        return "Ungrouped"
    name = str(group.get("name", "") or "").strip()
    if name:
        return name
    level = str(group.get("levelId", "") or "").strip()
    if level:
        return f"Level: {level}"
    proximity = str(group.get("proximityCell", "") or "").strip()
    if proximity:
        return f"Proximity: {proximity}"
    return "Ungrouped"


def _element_risk_buckets(elem: Optional[Element]) -> List[str]:
    if elem is None:
        return ["Type: Unknown Type"]
    systems = _element_system_names(elem)
    if systems:
        return [f"System: {systems[0]}"]
    discipline = str(getattr(elem, "discipline", "") or "").strip()
    if discipline and discipline.lower() != "unknown":
        return [f"Discipline: {discipline}"]
    type_label = friendly_item_type_label(getattr(elem, "type", ""))
    return [f"Type: {type_label}"]


def _element_system_names(elem: Element) -> List[str]:
    names: List[str] = []
    systems = getattr(elem, "systems", None)
    if isinstance(systems, list):
        names.extend(str(value).strip() for value in systems if str(value).strip())
    groups = getattr(elem, "system_group_names", None)
    if isinstance(groups, list):
        names.extend(str(value).strip() for value in groups if str(value).strip())
    system = str(getattr(elem, "system", "") or "").strip()
    if system:
        names.append(system)
    meta = getattr(elem, "ifc_meta", {}) or {}
    if isinstance(meta, dict):
        meta_systems = meta.get("system_groups") or meta.get("systems") or []
        if isinstance(meta_systems, list):
            names.extend(str(value).strip() for value in meta_systems if str(value).strip())
    return _dedupe(names)


def _dedupe(values: Iterable[str]) -> List[str]:
    ordered: List[str] = []
    for value in values:
        current = str(value or "").strip()
        if current and current not in ordered:
            ordered.append(current)
    return ordered
