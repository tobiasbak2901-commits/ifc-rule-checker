from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from geometry import aabb_distance_and_points, aabb_expand, aabb_intersects, segment_distance_and_points
from models import Issue


AABB = Tuple[float, float, float, float, float, float]
Point3 = Tuple[float, float, float]
Matrix4 = Tuple[float, ...]

UNITS_SCALE = 1.0
EPS = 1.0e-4


@dataclass(frozen=True)
class DistanceResult:
    method: str
    minDistance: float
    pointA: Optional[Point3]
    pointB: Optional[Point3]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Bounds:
    elementId: str
    aabbWorld: AABB
    aabbLocal: Optional[AABB] = None
    centerlineWorld: Optional[Tuple[Point3, Point3]] = None
    radiusWorld: Optional[float] = None
    meshVertexCount: int = 0
    meshCount: int = 0
    hasRenderableGeometry: bool = False
    worldMatrix: Matrix4 = (
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )
    invalidReason: Optional[str] = None


def _is_finite(v: float) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def _is_valid_aabb(aabb: Optional[AABB]) -> bool:
    if not aabb or len(aabb) != 6:
        return False
    if any(not _is_finite(v) for v in aabb):
        return False
    return bool(aabb[3] >= aabb[0] and aabb[4] >= aabb[1] and aabb[5] >= aabb[2])


def _scale_aabb(aabb: AABB, units_scale: float) -> AABB:
    s = float(units_scale)
    return (
        float(aabb[0]) * s,
        float(aabb[1]) * s,
        float(aabb[2]) * s,
        float(aabb[3]) * s,
        float(aabb[4]) * s,
        float(aabb[5]) * s,
    )


def _bounds_from_vertices(vertices: Sequence[float], units_scale: float) -> Optional[AABB]:
    if not vertices or len(vertices) < 3 or (len(vertices) % 3) != 0:
        return None
    s = float(units_scale)
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    try:
        for i in range(0, len(vertices), 3):
            x = float(vertices[i]) * s
            y = float(vertices[i + 1]) * s
            z = float(vertices[i + 2]) * s
            if not (_is_finite(x) and _is_finite(y) and _is_finite(z)):
                return None
            xs.append(x)
            ys.append(y)
            zs.append(z)
    except Exception:
        return None
    if not xs or not ys or not zs:
        return None
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _centerline_from_aabb(aabb: AABB) -> Tuple[Tuple[Point3, Point3], float]:
    minx, miny, minz, maxx, maxy, maxz = aabb
    cx = (minx + maxx) * 0.5
    cy = (miny + maxy) * 0.5
    cz = (minz + maxz) * 0.5
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    if dx >= dy and dx >= dz:
        line = ((minx, cy, cz), (maxx, cy, cz))
        radius = max(1e-4, min(dy, dz) * 0.5)
    elif dy >= dx and dy >= dz:
        line = ((cx, miny, cz), (cx, maxy, cz))
        radius = max(1e-4, min(dx, dz) * 0.5)
    else:
        line = ((cx, cy, minz), (cx, cy, maxz))
        radius = max(1e-4, min(dx, dy) * 0.5)
    return line, radius


def _is_linear_type(type_name: str) -> bool:
    t = str(type_name or "").lower()
    return any(token in t for token in ("pipe", "duct", "cable", "conduit", "flowsegment"))


def _midpoint(p0: Optional[Point3], p1: Optional[Point3]) -> Optional[Point3]:
    if p0 is None or p1 is None:
        return None
    return (
        (float(p0[0]) + float(p1[0])) * 0.5,
        (float(p0[1]) + float(p1[1])) * 0.5,
        (float(p0[2]) + float(p1[2])) * 0.5,
    )


def _rule_clearance_callable(rules: Any) -> Callable[[str, str], float]:
    if callable(rules):
        return lambda a, b: float(rules(a, b) or 0.0)
    if isinstance(rules, dict):
        fn = rules.get("clearance_for_pair")
        if callable(fn):
            return lambda a, b: float(fn(a, b) or 0.0)
        const = float(rules.get("required_clearance", 0.0) or 0.0)
        return lambda _a, _b: const
    fn = getattr(rules, "clearance_for_pair", None)
    if callable(fn):
        return lambda a, b: float(fn(a, b) or 0.0)
    return lambda _a, _b: 0.0


def _set_name_lookup(raw: Any) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for key, value in raw.items():
        if isinstance(value, (list, tuple)):
            out[str(key)] = [str(v) for v in value if v]
        elif value:
            out[str(key)] = [str(value)]
    return out


def _build_bounds_from_payload(payload: Any) -> Dict[str, Bounds]:
    units_scale = float(getattr(getattr(payload, "repository", None), "units_scale", UNITS_SCALE) or UNITS_SCALE)
    mesh_by_guid: Dict[str, List[Any]] = {}
    for mesh in list(getattr(payload, "meshes", []) or []):
        guid = str(getattr(mesh, "elementId", "") or "")
        if not guid:
            continue
        mesh_by_guid.setdefault(guid, []).append(mesh)

    repo = getattr(payload, "repository", None)
    element_refs = dict(getattr(payload, "elementRefs", {}) or {})
    aabbs = dict(getattr(payload, "aabbs", {}) or {})
    guids = sorted(set(aabbs.keys()) | set(element_refs.keys()) | set(mesh_by_guid.keys()))
    bounds_by_guid: Dict[str, Bounds] = {}

    for guid in guids:
        meshes = mesh_by_guid.get(guid, [])
        mesh_count = len(meshes)
        vertex_count = 0
        mesh_aabbs: List[AABB] = []
        for mesh in meshes:
            verts = tuple(getattr(mesh, "vertices", tuple()) or tuple())
            idx = tuple(getattr(mesh, "indices", tuple()) or tuple())
            if verts and idx:
                vertex_count += int(len(verts) // 3)
            mesh_bounds = _bounds_from_vertices(verts, units_scale)
            if mesh_bounds and _is_valid_aabb(mesh_bounds):
                mesh_aabbs.append(mesh_bounds)

        aabb_world = None
        if mesh_aabbs:
            minx = min(v[0] for v in mesh_aabbs)
            miny = min(v[1] for v in mesh_aabbs)
            minz = min(v[2] for v in mesh_aabbs)
            maxx = max(v[3] for v in mesh_aabbs)
            maxy = max(v[4] for v in mesh_aabbs)
            maxz = max(v[5] for v in mesh_aabbs)
            aabb_world = (minx, miny, minz, maxx, maxy, maxz)
        else:
            raw_aabb = aabbs.get(guid)
            if raw_aabb and len(raw_aabb) == 6:
                aabb_world = _scale_aabb(tuple(raw_aabb), units_scale)

        if not _is_valid_aabb(aabb_world):
            bounds_by_guid[guid] = Bounds(
                elementId=guid,
                aabbWorld=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                meshVertexCount=int(vertex_count),
                meshCount=int(mesh_count),
                hasRenderableGeometry=False,
                invalidReason="SKIPPED_INVALID_GEOMETRY: invalid or missing world bounds",
            )
            continue

        elem = element_refs.get(guid)
        elem_type = str(getattr(elem, "type", "") or "")
        centerline = None
        radius_world = None
        if _is_linear_type(elem_type):
            centerline, radius_guess = _centerline_from_aabb(aabb_world)
            radius_world = radius_guess
            if repo is not None and hasattr(repo, "get_element_diameter"):
                try:
                    diameter_value = repo.get_element_diameter(guid)
                except Exception:
                    diameter_value = None
                if isinstance(diameter_value, (int, float)) and math.isfinite(float(diameter_value)) and float(diameter_value) > 0:
                    radius_world = float(diameter_value) * units_scale * 0.5

        has_renderable_geometry = bool(mesh_count > 0 and vertex_count > 0)
        invalid_reason = None
        if not has_renderable_geometry:
            invalid_reason = "SKIPPED_INVALID_GEOMETRY: zero meshes or zero vertices"

        bounds_by_guid[guid] = Bounds(
            elementId=guid,
            aabbWorld=aabb_world,
            aabbLocal=None,
            centerlineWorld=centerline,
            radiusWorld=radius_world,
            meshVertexCount=int(vertex_count),
            meshCount=int(mesh_count),
            hasRenderableGeometry=has_renderable_geometry,
            invalidReason=invalid_reason,
        )

    return bounds_by_guid


def _as_matrix4(value: Any) -> Matrix4:
    if isinstance(value, (list, tuple)) and len(value) == 16:
        m = tuple(float(v) for v in value)
        return m
    return (
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )


def _scale_matrix_translation(matrix: Matrix4, units_scale: float) -> Matrix4:
    s = float(units_scale)
    return (
        float(matrix[0]),
        float(matrix[1]),
        float(matrix[2]),
        float(matrix[3]) * s,
        float(matrix[4]),
        float(matrix[5]),
        float(matrix[6]),
        float(matrix[7]) * s,
        float(matrix[8]),
        float(matrix[9]),
        float(matrix[10]),
        float(matrix[11]) * s,
        float(matrix[12]),
        float(matrix[13]),
        float(matrix[14]),
        float(matrix[15]),
    )


def _transform_point(matrix: Matrix4, point: Point3) -> Point3:
    x, y, z = float(point[0]), float(point[1]), float(point[2])
    tx = matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3]
    ty = matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7]
    tz = matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11]
    tw = matrix[12] * x + matrix[13] * y + matrix[14] * z + matrix[15]
    if abs(tw) > 1e-12:
        tx /= tw
        ty /= tw
        tz /= tw
    return (tx, ty, tz)


def _transform_aabb(matrix: Matrix4, aabb: AABB) -> AABB:
    x0, y0, z0, x1, y1, z1 = aabb
    corners = (
        (x0, y0, z0),
        (x0, y0, z1),
        (x0, y1, z0),
        (x0, y1, z1),
        (x1, y0, z0),
        (x1, y0, z1),
        (x1, y1, z0),
        (x1, y1, z1),
    )
    ws = [_transform_point(matrix, c) for c in corners]
    xs = [p[0] for p in ws]
    ys = [p[1] for p in ws]
    zs = [p[2] for p in ws]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _build_bounds_from_dict(scene: Dict[str, Any]) -> Dict[str, Bounds]:
    units_scale = float(scene.get("units_scale", UNITS_SCALE) or UNITS_SCALE)
    elements = list(scene.get("elements") or [])
    out: Dict[str, Bounds] = {}
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        guid = str(elem.get("id") or "")
        if not guid:
            continue
        matrix = _scale_matrix_translation(_as_matrix4(elem.get("worldMatrix")), units_scale)
        local_aabb = elem.get("aabbLocal")
        world_aabb = elem.get("aabbWorld")
        if local_aabb and len(local_aabb) == 6:
            local_scaled = _scale_aabb(tuple(local_aabb), units_scale)
            world_aabb = _transform_aabb(matrix, local_scaled)
        elif world_aabb and len(world_aabb) == 6:
            world_aabb = _scale_aabb(tuple(world_aabb), units_scale)
        else:
            world_aabb = None
        centerline_local = elem.get("centerlineLocal")
        centerline_world = elem.get("centerlineWorld")
        if centerline_local and len(centerline_local) == 2:
            p0 = _transform_point(
                matrix,
                (
                    float(centerline_local[0][0]) * units_scale,
                    float(centerline_local[0][1]) * units_scale,
                    float(centerline_local[0][2]) * units_scale,
                ),
            )
            p1 = _transform_point(
                matrix,
                (
                    float(centerline_local[1][0]) * units_scale,
                    float(centerline_local[1][1]) * units_scale,
                    float(centerline_local[1][2]) * units_scale,
                ),
            )
            centerline_world = (p0, p1)
        elif centerline_world and len(centerline_world) == 2:
            centerline_world = (
                (
                    float(centerline_world[0][0]) * units_scale,
                    float(centerline_world[0][1]) * units_scale,
                    float(centerline_world[0][2]) * units_scale,
                ),
                (
                    float(centerline_world[1][0]) * units_scale,
                    float(centerline_world[1][1]) * units_scale,
                    float(centerline_world[1][2]) * units_scale,
                ),
            )
        radius_world = elem.get("radius")
        if isinstance(radius_world, (int, float)):
            radius_world = float(radius_world) * units_scale
        else:
            radius_world = None
        mesh_vertex_count = int(elem.get("meshVertexCount") or 0)
        mesh_count = int(elem.get("meshCount") or (1 if mesh_vertex_count > 0 else 0))
        has_renderable = bool(elem.get("hasRenderableGeometry", mesh_vertex_count > 0))
        invalid_reason = None
        if not has_renderable:
            invalid_reason = "SKIPPED_INVALID_GEOMETRY: zero meshes or zero vertices"
        if not _is_valid_aabb(world_aabb):
            has_renderable = False
            invalid_reason = "SKIPPED_INVALID_GEOMETRY: invalid or missing world bounds"
            world_aabb = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        out[guid] = Bounds(
            elementId=guid,
            aabbWorld=tuple(world_aabb),
            aabbLocal=tuple(local_aabb) if local_aabb and len(local_aabb) == 6 else None,
            centerlineWorld=centerline_world,
            radiusWorld=radius_world,
            meshVertexCount=mesh_vertex_count,
            meshCount=mesh_count,
            hasRenderableGeometry=has_renderable,
            worldMatrix=matrix,
            invalidReason=invalid_reason,
        )
    return out


def build_world_bounds(scene) -> Dict[str, Bounds]:
    if scene is None:
        return {}
    if isinstance(scene, dict):
        return _build_bounds_from_dict(scene)
    if hasattr(scene, "meshes") and hasattr(scene, "aabbs"):
        return _build_bounds_from_payload(scene)
    return {}


def broadphase_pairs(bounds: Dict[str, Bounds], padding: float) -> Iterable[Tuple[str, str]]:
    pad = max(0.0, float(padding))
    items: List[Tuple[str, AABB]] = []
    for guid, b in (bounds or {}).items():
        if not b.hasRenderableGeometry:
            continue
        if not _is_valid_aabb(b.aabbWorld):
            continue
        items.append((str(guid), aabb_expand(b.aabbWorld, pad)))
    items.sort(key=lambda it: (it[1][0], it[1][3], it[0]))
    active: List[Tuple[str, AABB]] = []
    for guid, box in items:
        minx = box[0]
        active = [entry for entry in active if entry[1][3] >= minx]
        for other_guid, other_box in active:
            if aabb_intersects(box, other_box):
                if guid < other_guid:
                    yield (guid, other_guid)
                else:
                    yield (other_guid, guid)
        active.append((guid, box))


def narrowphase_distance(elemA: Bounds, elemB: Bounds) -> DistanceResult:
    if elemA.centerlineWorld and elemB.centerlineWorld:
        p0, p1 = elemA.centerlineWorld
        q0, q1 = elemB.centerlineWorld
        seg_dist, cp_a, cp_b = segment_distance_and_points(p0, p1, q0, q1)
        r_a = max(0.0, float(elemA.radiusWorld or 0.0))
        r_b = max(0.0, float(elemB.radiusWorld or 0.0))
        min_dist = float(seg_dist) - (r_a + r_b)
        return DistanceResult(
            method="centerline-cylinder",
            minDistance=min_dist,
            pointA=cp_a,
            pointB=cp_b,
            details={
                "segmentDistance": float(seg_dist),
                "radiusA": float(r_a),
                "radiusB": float(r_b),
            },
        )

    if _is_valid_aabb(elemA.aabbWorld) and _is_valid_aabb(elemB.aabbWorld):
        dist, p_a, p_b = aabb_distance_and_points(elemA.aabbWorld, elemB.aabbWorld)
        method = "aabb-mesh-proxy" if (elemA.meshVertexCount > 0 and elemB.meshVertexCount > 0) else "aabb-fallback"
        return DistanceResult(
            method=method,
            minDistance=float(dist),
            pointA=p_a,
            pointB=p_b,
            details={},
        )

    return DistanceResult(
        method="none",
        minDistance=float("inf"),
        pointA=None,
        pointB=None,
        details={"reason": "invalid geometry"},
    )


def detect_clashes(searchSetA, searchSetB, rules) -> List[Issue]:
    ids_a = [str(v) for v in (searchSetA or []) if v]
    ids_b = [str(v) for v in (searchSetB or []) if v]
    if not ids_a or not ids_b:
        return []

    if isinstance(rules, dict):
        bounds_map = dict(rules.get("bounds") or {})
        include_invalid = bool(rules.get("include_invalid_geometry", False))
        set_names_a = _set_name_lookup(rules.get("set_names_a"))
        set_names_b = _set_name_lookup(rules.get("set_names_b"))
        rule_id = str(rules.get("rule_id") or "SEARCH_SET_CLASH")
        severity = str(rules.get("severity") or "High")
        broadphase_padding = float(rules.get("broadphase_padding", 0.01) or 0.01)
        eps = float(rules.get("eps", EPS) or EPS)
        model_unit_to_meter = float(rules.get("model_unit_to_meter", 1.0) or 1.0)
        units_scale = float(rules.get("units_scale", UNITS_SCALE) or UNITS_SCALE)
    else:
        bounds_map = {}
        include_invalid = False
        set_names_a = {}
        set_names_b = {}
        rule_id = "SEARCH_SET_CLASH"
        severity = "High"
        broadphase_padding = 0.01
        eps = EPS
        model_unit_to_meter = 1.0
        units_scale = UNITS_SCALE

    clearance_for_pair = _rule_clearance_callable(rules)
    relevant_ids = sorted(set(ids_a) | set(ids_b))
    relevant_bounds: Dict[str, Bounds] = {}
    for guid in relevant_ids:
        b = bounds_map.get(guid)
        if not isinstance(b, Bounds):
            continue
        if not include_invalid and not b.hasRenderableGeometry:
            continue
        if not _is_valid_aabb(b.aabbWorld):
            continue
        relevant_bounds[guid] = b

    issues: List[Issue] = []
    seen: set[Tuple[str, str]] = set()
    ids_a_set = set(ids_a)
    ids_b_set = set(ids_b)
    same_scope = ids_a_set == ids_b_set

    for guid_a, guid_b in broadphase_pairs(relevant_bounds, padding=broadphase_padding):
        if same_scope:
            if guid_a not in ids_a_set or guid_b not in ids_a_set:
                continue
        else:
            if guid_a not in ids_a_set and guid_b in ids_a_set:
                guid_a, guid_b = guid_b, guid_a
            if guid_a not in ids_a_set or guid_b not in ids_b_set:
                continue
        key = tuple(sorted((guid_a, guid_b)))
        if key in seen:
            continue
        seen.add(key)

        elem_a = relevant_bounds.get(guid_a)
        elem_b = relevant_bounds.get(guid_b)
        if elem_a is None or elem_b is None:
            continue

        required_clearance = max(0.0, float(clearance_for_pair(guid_a, guid_b) or 0.0))
        pair_padding = max(float(broadphase_padding), float(required_clearance), 0.01)
        broadphase_hit = aabb_intersects(aabb_expand(elem_a.aabbWorld, pair_padding), aabb_expand(elem_b.aabbWorld, 0.0))
        if not broadphase_hit:
            continue

        result = narrowphase_distance(elem_a, elem_b)
        min_distance = float(result.minDistance)
        is_intersection = bool(min_distance <= float(eps))
        clearance_violation = bool(min_distance < (required_clearance - float(eps)))
        verdict_clash = bool(is_intersection or clearance_violation)
        if not verdict_clash:
            continue

        clearance_margin = float(min_distance - required_clearance)
        clearance_margin_model = clearance_margin / max(float(model_unit_to_meter), 1e-12)
        if min_distance > 0.0:
            overlap_value = -float(min_distance)
        else:
            overlap_value = abs(float(min_distance))

        issue = Issue(
            guid_a=guid_a,
            guid_b=guid_b,
            rule_id=rule_id,
            severity=severity,
            clearance=clearance_margin_model,
            p_a=result.pointA,
            p_b=result.pointB,
            clash_center=_midpoint(result.pointA, result.pointB),
            approx_distance=min_distance,
            approx_clearance=clearance_margin,
            search_set_names_a=list(set_names_a.get(guid_a, [])),
            search_set_names_b=list(set_names_b.get(guid_b, [])),
        )
        issue.min_distance_world = min_distance
        issue.required_clearance_world = required_clearance
        issue.detection_method = result.method
        issue.bbox_overlap = (overlap_value, 0.0, 0.0)
        issue.clash_diagnostics = {
            "unitsScale": float(units_scale),
            "broadphase": {
                "intersects": bool(broadphase_hit),
                "padding": float(pair_padding),
            },
            "narrowphase": {
                "method": str(result.method),
                "minDistance": float(min_distance),
                "requiredClearance": float(required_clearance),
                "eps": float(eps),
                "details": dict(result.details or {}),
            },
            "verdict": "CLASH" if verdict_clash else "NO_CLASH",
            "elements": {
                guid_a: {
                    "aabbWorld": tuple(elem_a.aabbWorld),
                    "worldMatrix": tuple(elem_a.worldMatrix),
                    "centerlineWorld": tuple(elem_a.centerlineWorld) if elem_a.centerlineWorld else None,
                    "meshVertexCount": int(elem_a.meshVertexCount),
                    "meshCount": int(elem_a.meshCount),
                },
                guid_b: {
                    "aabbWorld": tuple(elem_b.aabbWorld),
                    "worldMatrix": tuple(elem_b.worldMatrix),
                    "centerlineWorld": tuple(elem_b.centerlineWorld) if elem_b.centerlineWorld else None,
                    "meshVertexCount": int(elem_b.meshVertexCount),
                    "meshCount": int(elem_b.meshCount),
                },
            },
            "invalidSkipped": [],
        }
        issues.append(issue)

    issues.sort(key=lambda it: (it.guid_a or "", it.guid_b or ""))
    return issues


def load_debug_dataset_two_cylinders(*, separation_m: float = 2.0) -> Dict[str, Any]:
    sep = float(max(separation_m, 0.0))
    return {
        "units_scale": 1.0,
        "elements": [
            {
                "id": "pipe_A",
                "aabbLocal": (0.0, -0.05, -0.05, 2.0, 0.05, 0.05),
                "centerlineLocal": ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0)),
                "radius": 0.05,
                "meshVertexCount": 120,
                "meshCount": 1,
            },
            {
                "id": "pipe_B",
                "aabbLocal": (0.0, -0.05, -0.05, 2.0, 0.05, 0.05),
                "centerlineLocal": ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0)),
                "radius": 0.05,
                "worldMatrix": (
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    sep,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                ),
                "meshVertexCount": 120,
                "meshCount": 1,
            },
        ],
    }
