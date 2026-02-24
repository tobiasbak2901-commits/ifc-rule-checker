from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from geometry import aabb_distance_and_points

from .models import ClashType

AABB = Tuple[float, float, float, float, float, float]
Point3 = Tuple[float, float, float]


@dataclass(frozen=True)
class AABBNarrowphaseResult:
    minDistance: float
    overlapDepth: float
    point: Optional[Point3]
    pointA: Optional[Point3]
    pointB: Optional[Point3]
    method: str = "aabb"


def run_narrowphase_v1(aabb_a: AABB, aabb_b: AABB) -> AABBNarrowphaseResult:
    min_distance, p_a, p_b = aabb_distance_and_points(aabb_a, aabb_b)
    overlap_depth = overlap_depth_aabb(aabb_a, aabb_b)
    centroid = _pair_centroid(aabb_a, aabb_b)
    return AABBNarrowphaseResult(
        minDistance=float(min_distance),
        overlapDepth=float(overlap_depth),
        point=centroid,
        pointA=tuple(float(v) for v in p_a) if p_a else None,
        pointB=tuple(float(v) for v in p_b) if p_b else None,
        method="aabb",
    )


def clash_verdict_v1(
    *,
    clash_type: ClashType,
    min_distance_m: float,
    overlap_depth_m: float,
    threshold_m: float,
    eps: float,
) -> bool:
    threshold = max(0.0, float(threshold_m or 0.0))
    min_distance = float(min_distance_m or 0.0)
    overlap_depth = max(0.0, float(overlap_depth_m or 0.0))
    margin = max(0.0, float(eps or 0.0))

    if clash_type == ClashType.HARD:
        # Hard clash if AABB overlap.
        return bool(overlap_depth > margin)
    if clash_type == ClashType.CLEARANCE:
        # Clearance clash if minimum distance is below required clearance.
        return bool(min_distance < (threshold - margin))
    if clash_type == ClashType.TOLERANCE:
        # Tolerance clash if overlap depth exceeds tolerance.
        return bool(overlap_depth > (threshold + margin))
    return False


def overlap_depth_aabb(aabb_a: AABB, aabb_b: AABB) -> float:
    overlap_x = max(0.0, min(float(aabb_a[3]), float(aabb_b[3])) - max(float(aabb_a[0]), float(aabb_b[0])))
    overlap_y = max(0.0, min(float(aabb_a[4]), float(aabb_b[4])) - max(float(aabb_a[1]), float(aabb_b[1])))
    overlap_z = max(0.0, min(float(aabb_a[5]), float(aabb_b[5])) - max(float(aabb_a[2]), float(aabb_b[2])))
    if overlap_x <= 0.0 or overlap_y <= 0.0 or overlap_z <= 0.0:
        return 0.0
    return float(min(overlap_x, overlap_y, overlap_z))


def _pair_centroid(aabb_a: AABB, aabb_b: AABB) -> Point3:
    ax = (float(aabb_a[0]) + float(aabb_a[3])) * 0.5
    ay = (float(aabb_a[1]) + float(aabb_a[4])) * 0.5
    az = (float(aabb_a[2]) + float(aabb_a[5])) * 0.5
    bx = (float(aabb_b[0]) + float(aabb_b[3])) * 0.5
    by = (float(aabb_b[1]) + float(aabb_b[4])) * 0.5
    bz = (float(aabb_b[2]) + float(aabb_b[5])) * 0.5
    return (
        (ax + bx) * 0.5,
        (ay + by) * 0.5,
        (az + bz) * 0.5,
    )
