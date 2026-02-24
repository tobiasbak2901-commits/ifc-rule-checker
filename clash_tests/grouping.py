from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import ClashGroup, ClashResult, GROUP_ELEMENT_A, GROUP_LEVEL, GROUP_PROXIMITY


@dataclass(frozen=True)
class LevelInterval:
    level_id: str
    min_z: float
    max_z: float


def midpoint_proximity_cell(midpoint: Optional[Tuple[float, float, float]], proximity_meters: float) -> str:
    if midpoint is None:
        return "0,0,0"
    step = max(1.0e-6, float(proximity_meters or 6.0))
    x = int(math.floor(float(midpoint[0]) / step))
    y = int(math.floor(float(midpoint[1]) / step))
    z = int(math.floor(float(midpoint[2]) / step))
    return f"{x},{y},{z}"


def level_for_point_z(
    point_z: Optional[float],
    level_intervals: Sequence[LevelInterval],
) -> str:
    if point_z is None:
        return "UnknownLevel"
    z = float(point_z)
    for interval in list(level_intervals or []):
        if z >= float(interval.min_z) and z < float(interval.max_z):
            return str(interval.level_id)
    return "UnknownLevel"


def build_clash_groups(
    results: Sequence[ClashResult],
    *,
    test_id: str,
    grouping_order: Sequence[str],
    element_labels: Optional[Dict[str, str]] = None,
) -> List[ClashGroup]:
    groups: Dict[str, ClashGroup] = {}
    labels = dict(element_labels or {})
    order = [str(v) for v in list(grouping_order or []) if str(v).strip()]
    if not order:
        order = [GROUP_ELEMENT_A, GROUP_PROXIMITY]

    for result in list(results or []):
        key_parts: List[str] = []
        if GROUP_ELEMENT_A in order:
            key_parts.append(f"a={result.elementA_key or '-'}")
        if GROUP_PROXIMITY in order:
            key_parts.append(f"p={result.proximity_cell or '0,0,0'}")
        if GROUP_LEVEL in order:
            key_parts.append(f"l={result.level_id or 'UnknownLevel'}")
        group_id = f"grp:{test_id}:{'|'.join(key_parts)}"

        left = labels.get(result.elementA_key or "", result.elementA_key or "ElementA")
        right = labels.get(result.elementB_id or "", result.elementB_id or "ElementB")
        level = result.level_id or "UnknownLevel"
        group_name = f"{left} {level}".strip()
        clash_name = f"{left} vs {right}"

        result.group_id = group_id
        result.group_name = group_name
        result.clash_name = clash_name

        if group_id not in groups:
            groups[group_id] = ClashGroup(
                id=group_id,
                test_id=str(test_id),
                name=group_name,
                elementA_key=result.elementA_key,
                proximity_cell=result.proximity_cell,
                level_id=result.level_id,
                result_ids=[result.id],
            )
        else:
            groups[group_id].result_ids.append(result.id)

    out = list(groups.values())
    out.sort(key=lambda g: (g.name, g.id))
    for group in out:
        group.result_ids.sort()
    return out


def group_lookup(groups: Iterable[ClashGroup]) -> Dict[str, ClashGroup]:
    return {str(group.id): group for group in list(groups or [])}
