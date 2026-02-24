from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, List, Optional, Tuple


AABB = Tuple[float, float, float, float, float, float]
BoundsXYZ = Tuple[float, float, float, float, float, float]
Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class AutoFitPlan:
    valid: bool
    message: str
    bbox_world: Optional[BoundsXYZ]
    bbox_min: Optional[Vec3]
    bbox_max: Optional[Vec3]
    bbox_center: Optional[Vec3]
    bbox_diagonal: float
    georeferenced: bool
    scene_offset: Optional[Vec3]
    camera_near: Optional[float]
    camera_far: Optional[float]
    camera_target: Optional[Vec3]
    camera_position: Optional[Vec3]
    used_fallback_bounds: bool


def aabb_to_bounds_xyz(aabb: AABB) -> BoundsXYZ:
    return (aabb[0], aabb[3], aabb[1], aabb[4], aabb[2], aabb[5])


def combine_bounds(bounds_list: Iterable[BoundsXYZ]) -> Optional[BoundsXYZ]:
    bounds: Optional[List[float]] = None
    for b in bounds_list:
        if not b or len(b) != 6:
            continue
        min_x, max_x, min_y, max_y, min_z, max_z = b
        if (
            any(v is None for v in b)
            or max_x < min_x
            or max_y < min_y
            or max_z < min_z
        ):
            continue
        if bounds is None:
            bounds = [min_x, max_x, min_y, max_y, min_z, max_z]
        else:
            bounds[0] = min(bounds[0], min_x)
            bounds[1] = max(bounds[1], max_x)
            bounds[2] = min(bounds[2], min_y)
            bounds[3] = max(bounds[3], max_y)
            bounds[4] = min(bounds[4], min_z)
            bounds[5] = max(bounds[5], max_z)
    return tuple(bounds) if bounds else None


def compute_auto_fit_plan(
    mesh_bounds_world: Iterable[BoundsXYZ],
    fallback_bounds_world: Iterable[BoundsXYZ],
    *,
    georef_center_threshold: float = 10_000.0,
    georef_diag_threshold: float = 1.0e7,
    tiny_diag_threshold: float = 1.0e-6,
) -> AutoFitPlan:
    mesh_bounds = [b for b in mesh_bounds_world if b and len(b) == 6]
    fallback_bounds = [b for b in fallback_bounds_world if b and len(b) == 6]
    used_fallback = len(mesh_bounds) == 0
    source = fallback_bounds if used_fallback else mesh_bounds
    world = combine_bounds(source)

    if world is None:
        return AutoFitPlan(
            valid=False,
            message="No renderable geometry (0 meshes)",
            bbox_world=None,
            bbox_min=None,
            bbox_max=None,
            bbox_center=None,
            bbox_diagonal=0.0,
            georeferenced=False,
            scene_offset=None,
            camera_near=None,
            camera_far=None,
            camera_target=None,
            camera_position=None,
            used_fallback_bounds=used_fallback,
        )

    min_x, max_x, min_y, max_y, min_z, max_z = world
    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    diagonal = math.sqrt(dx * dx + dy * dy + dz * dz)
    center = (
        (min_x + max_x) * 0.5,
        (min_y + max_y) * 0.5,
        (min_z + max_z) * 0.5,
    )
    if diagonal < float(tiny_diag_threshold):
        return AutoFitPlan(
            valid=False,
            message=f"Invalid model bounds (diagonal={diagonal:.3e})",
            bbox_world=world,
            bbox_min=(min_x, min_y, min_z),
            bbox_max=(max_x, max_y, max_z),
            bbox_center=center,
            bbox_diagonal=diagonal,
            georeferenced=False,
            scene_offset=None,
            camera_near=None,
            camera_far=None,
            camera_target=None,
            camera_position=None,
            used_fallback_bounds=used_fallback,
        )

    georeferenced = (
        max(abs(center[0]), abs(center[1]), abs(center[2])) > float(georef_center_threshold)
        or diagonal > float(georef_diag_threshold)
    )
    scene_offset = center if georeferenced else None
    near = max(0.01, diagonal / 10_000.0)
    far = max(1000.0, diagonal * 10.0)
    target = (0.0, 0.0, 0.0) if georeferenced else center
    dir_norm = 1.0 / math.sqrt(3.0)
    distance = max(diagonal * 1.2, 1.0)
    cam_pos = (
        target[0] + dir_norm * distance,
        target[1] + dir_norm * distance,
        target[2] + dir_norm * distance,
    )
    return AutoFitPlan(
        valid=True,
        message="OK",
        bbox_world=world,
        bbox_min=(min_x, min_y, min_z),
        bbox_max=(max_x, max_y, max_z),
        bbox_center=center,
        bbox_diagonal=diagonal,
        georeferenced=georeferenced,
        scene_offset=scene_offset,
        camera_near=near,
        camera_far=far,
        camera_target=target,
        camera_position=cam_pos,
        used_fallback_bounds=used_fallback,
    )
