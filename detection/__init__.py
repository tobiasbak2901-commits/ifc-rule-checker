from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from geometry import aabb_distance_and_points, aabb_expand, aabb_intersects, normalize
from models import Issue


AABB = Tuple[float, float, float, float, float, float]


@dataclass
class SpatialIndex:
    cell: float
    buckets: Dict[Tuple[int, int, int], List[Tuple[str, AABB]]]

    def insert(self, guid: str, aabb: AABB):
        cx = (aabb[0] + aabb[3]) / 2.0
        cy = (aabb[1] + aabb[4]) / 2.0
        cz = (aabb[2] + aabb[5]) / 2.0
        key = (int(cx // self.cell), int(cy // self.cell), int(cz // self.cell))
        self.buckets.setdefault(key, []).append((guid, aabb))

    def query(self, aabb: AABB) -> Iterable[Tuple[str, AABB]]:
        cx = (aabb[0] + aabb[3]) / 2.0
        cy = (aabb[1] + aabb[4]) / 2.0
        cz = (aabb[2] + aabb[5]) / 2.0
        kx, ky, kz = int(cx // self.cell), int(cy // self.cell), int(cz // self.cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for item in self.buckets.get((kx + dx, ky + dy, kz + dz), []):
                        yield item


def build_spatial_index(aabbs: Dict[str, AABB], cell: float = 2.0) -> SpatialIndex:
    index = SpatialIndex(cell=cell, buckets={})
    for guid, aabb in aabbs.items():
        index.insert(guid, aabb)
    return index


def evaluate_pair(
    guid_a: str,
    guid_b: str,
    aabb_a: AABB,
    aabb_b: AABB,
    respect: float,
    tolerance: float,
    rule_id: str,
    severity: str,
    base_issue: Optional[Issue] = None,
) -> Issue:
    dist, p_a, p_b = aabb_distance_and_points(aabb_a, aabb_b)
    clearance = dist - respect
    direction = normalize((p_a[0] - p_b[0], p_a[1] - p_b[1], p_a[2] - p_b[2]))
    issue = Issue(
        guid_a=guid_a,
        guid_b=guid_b,
        rule_id=rule_id,
        severity=severity,
        clearance=clearance,
        p_a=p_a,
        p_b=p_b,
        direction=direction,
        clash_center=((p_a[0] + p_b[0]) / 2.0, (p_a[1] + p_b[1]) / 2.0, (p_a[2] + p_b[2]) / 2.0),
    )
    if base_issue:
        issue.issue_id = base_issue.issue_id
        issue.title = base_issue.title
        issue.viewpoint = base_issue.viewpoint
        issue.snapshot_bytes = base_issue.snapshot_bytes
        issue.snapshot_mime = base_issue.snapshot_mime
        issue.bcf_description = base_issue.bcf_description
        issue.bcf_comments = base_issue.bcf_comments
        issue.movable_guid = base_issue.movable_guid
        issue.movable_discipline = base_issue.movable_discipline
        issue.movable_type = base_issue.movable_type
        issue.element_a = base_issue.element_a
        issue.element_b = base_issue.element_b
        issue.utility_a = base_issue.utility_a
        issue.utility_b = base_issue.utility_b
        issue.relation = base_issue.relation
        issue.is_bound = base_issue.is_bound
    return issue


def generate_issues_from_bcf(
    issues: List[Issue],
    aabbs: Dict[str, AABB],
    respect: float,
    tolerance: float,
    log: Optional[Callable[[str], None]] = None,
) -> List[Issue]:
    enriched: List[Issue] = []
    for issue in issues:
        if issue.guid_a in aabbs and issue.guid_b in aabbs:
            enriched.append(
                evaluate_pair(
                    issue.guid_a,
                    issue.guid_b,
                    aabbs[issue.guid_a],
                    aabbs[issue.guid_b],
                    respect,
                    tolerance,
                    issue.rule_id,
                    issue.severity,
                    base_issue=issue,
                )
            )
        else:
            if log:
                missing = []
                if issue.guid_a not in aabbs:
                    missing.append(issue.guid_a or "<empty>")
                if issue.guid_b not in aabbs:
                    missing.append(issue.guid_b or "<empty>")
                log(f"BCF GUID missing in IFC: {', '.join(missing)} (issue {issue.issue_id or ''})")
    return enriched


def generate_issues_from_ifc(
    elements: Dict[str, object],
    aabbs: Dict[str, AABB],
    respect: float,
    tolerance: float,
    rule_id: str = "IFC_RULES",
    severity: str = "High",
) -> List[Issue]:
    index = build_spatial_index(aabbs)
    issues: List[Issue] = []
    seen: Set[Tuple[str, str]] = set()
    for guid_a, elem_a in elements.items():
        aabb_a = aabbs.get(guid_a)
        if not aabb_a:
            continue
        query_box = aabb_expand(aabb_a, respect + tolerance)
        for guid_b, aabb_b in index.query(query_box):
            if guid_a == guid_b:
                continue
            key = tuple(sorted((guid_a, guid_b)))
            if key in seen:
                continue
            seen.add(key)
            if not aabb_intersects(query_box, aabb_b):
                continue
            issues.append(
                evaluate_pair(
                    guid_a,
                    guid_b,
                    aabb_a,
                    aabb_b,
                    respect,
                    tolerance,
                    rule_id,
                    severity,
                )
            )
    return issues


def aabb_overlap_size(aabb_a: AABB, aabb_b: AABB) -> Tuple[float, float, float]:
    overlap_x = max(0.0, min(aabb_a[3], aabb_b[3]) - max(aabb_a[0], aabb_b[0]))
    overlap_y = max(0.0, min(aabb_a[4], aabb_b[4]) - max(aabb_a[1], aabb_b[1]))
    overlap_z = max(0.0, min(aabb_a[5], aabb_b[5]) - max(aabb_a[2], aabb_b[2]))
    return overlap_x, overlap_y, overlap_z


def generate_issues_from_search_sets(
    set_a_guids: Iterable[str],
    set_b_guids: Iterable[str],
    aabbs: Dict[str, AABB],
    set_names_a: Optional[Dict[str, List[str]]] = None,
    set_names_b: Optional[Dict[str, List[str]]] = None,
    rule_id: str = "SEARCH_SET_CLASH",
    severity: str = "High",
) -> List[Issue]:
    guids_a = [guid for guid in set_a_guids if guid in aabbs]
    guids_b = [guid for guid in set_b_guids if guid in aabbs]
    if not guids_a or not guids_b:
        return []

    index = build_spatial_index({guid: aabbs[guid] for guid in guids_b})
    issues: List[Issue] = []
    seen: Set[Tuple[str, str]] = set()

    for guid_a in guids_a:
        aabb_a = aabbs.get(guid_a)
        if not aabb_a:
            continue
        for guid_b, aabb_b in index.query(aabb_a):
            if guid_a == guid_b:
                continue
            key = tuple(sorted((guid_a, guid_b)))
            if key in seen:
                continue
            seen.add(key)
            if not aabb_intersects(aabb_a, aabb_b):
                continue
            issue = evaluate_pair(
                guid_a=guid_a,
                guid_b=guid_b,
                aabb_a=aabb_a,
                aabb_b=aabb_b,
                respect=0.0,
                tolerance=0.0,
                rule_id=rule_id,
                severity=severity,
            )
            issue.bbox_overlap = aabb_overlap_size(aabb_a, aabb_b)
            issue.approx_distance = issue.clearance
            issue.approx_clearance = issue.clearance
            issue.search_set_names_a = list((set_names_a or {}).get(guid_a, []))
            issue.search_set_names_b = list((set_names_b or {}).get(guid_b, []))
            issues.append(issue)
    return issues
