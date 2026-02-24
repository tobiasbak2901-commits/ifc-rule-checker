from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from models import Element
from viewer.auto_fit import aabb_to_bounds_xyz, combine_bounds

AABB = Tuple[float, float, float, float, float, float]
BoundsXYZ = Tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class ModelElementPayload:
    id: str
    globalId: str
    className: str
    name: str
    props: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelMeshPayload:
    id: str
    elementId: str
    vertices: Tuple[float, ...]
    indices: Tuple[int, ...]
    normals: Tuple[float, ...] = tuple()
    material: Optional[Dict[str, object]] = None
    aabb: Optional[BoundsXYZ] = None


@dataclass(frozen=True)
class ModelPayload:
    sourcePath: str
    repository: Any
    elementRefs: Dict[str, Element]
    elements: List[ModelElementPayload]
    elementsParsed: int
    meshes: List[ModelMeshPayload]
    aabbs: Dict[str, AABB]
    bboxWorld: Optional[BoundsXYZ]
    warnings: Tuple[str, ...] = tuple()


def bbox_diagonal(bounds: Optional[BoundsXYZ]) -> float:
    if not bounds:
        return 0.0
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    dx = float(max_x) - float(min_x)
    dy = float(max_y) - float(min_y)
    dz = float(max_z) - float(min_z)
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def _triangles_from_faces(faces: Any, n_verts: int) -> List[Tuple[int, int, int]]:
    tris: List[Tuple[int, int, int]] = []
    if n_verts <= 0:
        return tris

    def _triangles_from_stream(index_values: Sequence[int]) -> List[Tuple[int, int, int]]:
        out: List[Tuple[int, int, int]] = []
        for j in range(0, len(index_values) - 2, 3):
            a = int(index_values[j])
            b = int(index_values[j + 1])
            c = int(index_values[j + 2])
            if 0 <= a < n_verts and 0 <= b < n_verts and 0 <= c < n_verts:
                out.append((a, b, c))
        return out

    if faces is None:
        return tris
    try:
        if hasattr(faces, "shape") and len(getattr(faces, "shape", ())) == 2:
            for face in faces.tolist():
                if len(face) < 3:
                    continue
                idx = [int(v) for v in face]
                if any(v < 0 or v >= n_verts for v in idx):
                    continue
                for i in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[i], idx[i + 1]))
            return tris
        if len(faces) > 0 and isinstance(faces[0], (list, tuple)):
            for face in faces:
                if len(face) < 3:
                    continue
                idx = [int(v) for v in face]
                if any(v < 0 or v >= n_verts for v in idx):
                    continue
                for i in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[i], idx[i + 1]))
            return tris
    except Exception:
        pass

    # IFC faces are often run-length encoded.
    try:
        face_values = [int(v) for v in faces]
    except Exception:
        return tris
    i = 0
    ok = True
    while i < len(face_values):
        n = int(face_values[i])
        i += 1
        if n < 3 or (i + n) > len(face_values):
            ok = False
            break
        idx = face_values[i : i + n]
        i += n
        if any(v < 0 or v >= n_verts for v in idx):
            ok = False
            break
        for t in range(1, n - 1):
            tris.append((idx[0], idx[t], idx[t + 1]))
    if ok and tris:
        return tris

    max_idx = max(face_values) if face_values else -1
    min_idx = min(face_values) if face_values else 0

    # Try direct triangle stream first, but compare with one-based interpretation
    # when values suggest both could be valid.
    direct_tris = _triangles_from_stream(face_values)
    if min_idx >= 1:
        one_based = [int(v) - 1 for v in face_values]
        one_based_tris = _triangles_from_stream(one_based)
        if len(one_based_tris) > len(direct_tris):
            return one_based_tris
    if direct_tris:
        return direct_tris

    # IFC streams can reference flattened coordinate indices.
    if max_idx >= n_verts and max_idx < (n_verts * 3):
        coord_indices = [int(v) // 3 for v in face_values]
        tris = _triangles_from_stream(coord_indices)
        if tris:
            return tris

    # One-based indexing variants.
    if min_idx >= 1:
        if max_idx > n_verts and max_idx <= (n_verts * 3):
            one_based_coord = [max(0, int(v) - 1) // 3 for v in face_values]
            tris = _triangles_from_stream(one_based_coord)
            if tris:
                return tris

    # Last-resort: consume vertices sequentially.
    sequential = list(range(n_verts - (n_verts % 3)))
    tris = _triangles_from_stream(sequential)
    return tris


def _bounds_from_vertices(vertices: Sequence[float]) -> Optional[BoundsXYZ]:
    if not vertices or len(vertices) < 3:
        return None
    xs = [float(v) for v in vertices[0::3]]
    ys = [float(v) for v in vertices[1::3]]
    zs = [float(v) for v in vertices[2::3]]
    if not xs or not ys or not zs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    n = math.sqrt((v[0] * v[0]) + (v[1] * v[1]) + (v[2] * v[2]))
    if n <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _tube_mesh_from_centerline(
    line: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
    radius: float,
    segments: int = 16,
) -> tuple[Tuple[float, ...], Tuple[int, ...], Tuple[float, ...]]:
    p0 = (float(line[0][0]), float(line[0][1]), float(line[0][2]))
    p1 = (float(line[1][0]), float(line[1][1]), float(line[1][2]))
    axis = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    axis_n = _normalize(axis)
    if axis_n == (0.0, 0.0, 0.0):
        return tuple(), tuple(), tuple()
    ref = (0.0, 0.0, 1.0) if abs(axis_n[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = _normalize(_cross(axis_n, ref))
    v = _normalize(_cross(axis_n, u))
    if u == (0.0, 0.0, 0.0) or v == (0.0, 0.0, 0.0):
        return tuple(), tuple(), tuple()

    segments = max(6, int(segments))
    radius = max(float(radius), 1e-4)
    vertices: List[float] = []
    normals: List[float] = []
    indices: List[int] = []
    for i in range(segments):
        angle = (2.0 * math.pi * float(i)) / float(segments)
        c = math.cos(angle)
        s = math.sin(angle)
        ring_dir = (
            (u[0] * c) + (v[0] * s),
            (u[1] * c) + (v[1] * s),
            (u[2] * c) + (v[2] * s),
        )
        nrm = _normalize(ring_dir)
        start = (
            p0[0] + (ring_dir[0] * radius),
            p0[1] + (ring_dir[1] * radius),
            p0[2] + (ring_dir[2] * radius),
        )
        end = (
            p1[0] + (ring_dir[0] * radius),
            p1[1] + (ring_dir[1] * radius),
            p1[2] + (ring_dir[2] * radius),
        )
        vertices.extend((start[0], start[1], start[2], end[0], end[1], end[2]))
        normals.extend((nrm[0], nrm[1], nrm[2], nrm[0], nrm[1], nrm[2]))

    for i in range(segments):
        j = (i + 1) % segments
        a0 = 2 * i
        a1 = a0 + 1
        b0 = 2 * j
        b1 = b0 + 1
        indices.extend((a0, a1, b1, a0, b1, b0))

    return tuple(vertices), tuple(indices), tuple(normals)


def _centerline_from_bounds(bounds: Optional[BoundsXYZ]) -> Optional[tuple[tuple[float, float, float], tuple[float, float, float], float]]:
    if not bounds:
        return None
    min_x, max_x, min_y, max_y, min_z, max_z = bounds
    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5
    dx = float(max_x) - float(min_x)
    dy = float(max_y) - float(min_y)
    dz = float(max_z) - float(min_z)
    if dx <= 0.0 and dy <= 0.0 and dz <= 0.0:
        return None
    if dx >= dy and dx >= dz:
        p0 = (float(min_x), cy, cz)
        p1 = (float(max_x), cy, cz)
        radius = max(min(dy, dz) * 0.5, 1e-4)
    elif dy >= dx and dy >= dz:
        p0 = (cx, float(min_y), cz)
        p1 = (cx, float(max_y), cz)
        radius = max(min(dx, dz) * 0.5, 1e-4)
    else:
        p0 = (cx, cy, float(min_z))
        p1 = (cx, cy, float(max_z))
        radius = max(min(dx, dy) * 0.5, 1e-4)
    return (p0, p1, radius)


def _is_linear_ifc_type(ifc_type: str) -> bool:
    t = str(ifc_type or "").lower()
    return any(token in t for token in ("pipe", "duct", "conduit", "cable", "flowsegment"))


def _element_payload_from_element(elem: Element) -> ModelElementPayload:
    props = {
        "discipline": elem.discipline,
        "system": elem.system,
        "utilityType": elem.utility_type,
        "typeName": elem.type_name,
        "layers": list(elem.layers or []),
    }
    return ModelElementPayload(
        id=str(elem.guid),
        globalId=str(elem.guid),
        className=str(elem.type),
        name=str(elem.name or ""),
        props=props,
    )


def build_model_payload(
    repository: Any,
    *,
    aabbs: Optional[Dict[str, AABB]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ModelPayload:
    if repository is None:
        raise ValueError("repository is required")
    elements_map: Dict[str, Element] = dict(getattr(repository, "elements", {}) or {})
    guids = sorted(elements_map.keys())
    payload_elements = [_element_payload_from_element(elements_map[guid]) for guid in guids]

    aabb_lookup: Dict[str, AABB] = dict(aabbs or {})
    payload_meshes: List[ModelMeshPayload] = []
    warnings: List[str] = []
    mesh_bounds: List[BoundsXYZ] = []
    fallback_bounds: List[BoundsXYZ] = []
    no_representation_samples: List[str] = []
    triangulation_failure_samples: List[str] = []

    total = len(guids)
    for idx, guid in enumerate(guids, start=1):
        if progress_callback and (idx == 1 or idx == total or idx % 200 == 0):
            progress_callback(idx, total)
        try:
            aabb = aabb_lookup.get(guid)
            if aabb is None:
                aabb = repository.get_aabb(guid)
                if aabb:
                    aabb_lookup[guid] = aabb
            if aabb:
                fallback_bounds.append(aabb_to_bounds_xyz(aabb))
        except Exception as exc:
            warnings.append(f"{guid}: AABB failed ({exc})")
            aabb = None

        geom = None
        try:
            geom = repository.get_element_geom(guid)
        except Exception as exc:
            warnings.append(f"{guid}: geometry failed ({exc})")
            if len(triangulation_failure_samples) < 10:
                triangulation_failure_samples.append(f"{guid}: {exc}")
            geom = None
        if not geom:
            reason = None
            if hasattr(repository, "get_shape_error"):
                try:
                    reason = repository.get_shape_error(guid)
                except Exception:
                    reason = None
            if len(warnings) < 200:
                if reason:
                    warnings.append(f"{guid}: {reason}")
                else:
                    warnings.append(f"{guid}: No IFC representation")
            if len(no_representation_samples) < 10:
                elem = elements_map.get(guid)
                elem_type = str(elem.type) if elem else "IfcProduct"
                no_representation_samples.append(f"{elem_type} {guid}")
            continue

        mesh_id = f"mesh:{guid}"
        elem = elements_map.get(guid)
        elem_type = str(elem.type if elem else "")
        linear_type = _is_linear_ifc_type(elem_type)
        aabb_bounds = aabb_to_bounds_xyz(aabb) if aabb else None

        def _append_centerline_fallback(reason_label: str) -> bool:
            if not linear_type:
                return False
            centerline = _centerline_from_bounds(aabb_bounds)
            if not centerline:
                return False
            p0, p1, radius = centerline
            verts_fb, idx_fb, nrm_fb = _tube_mesh_from_centerline((p0, p1), radius)
            if not verts_fb or not idx_fb:
                return False
            bounds_fb = _bounds_from_vertices(verts_fb) or aabb_bounds
            payload_meshes.append(
                ModelMeshPayload(
                    id=f"{mesh_id}:fallback",
                    elementId=guid,
                    vertices=verts_fb,
                    normals=nrm_fb,
                    indices=idx_fb,
                    material=None,
                    aabb=bounds_fb,
                )
            )
            if bounds_fb:
                mesh_bounds.append(bounds_fb)
            warnings.append(f"{guid}: triangulation fallback -> centerline ({reason_label})")
            return True

        if geom.get("kind") == "mesh":
            shape = geom.get("shape")
            if not shape:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: shape missing")
                _append_centerline_fallback("shape missing")
                continue
            verts_raw = getattr(getattr(shape, "geometry", None), "verts", None)
            faces_raw = getattr(getattr(shape, "geometry", None), "faces", None)
            normals_raw = getattr(getattr(shape, "geometry", None), "normals", None)
            if not verts_raw or not faces_raw:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: verts/faces missing")
                _append_centerline_fallback("verts/faces missing")
                continue
            try:
                vertices = tuple(float(v) for v in verts_raw)
            except Exception:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: vertex conversion failed")
                _append_centerline_fallback("vertex conversion failed")
                continue
            if len(vertices) < 9 or len(vertices) % 3 != 0:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: invalid vertex buffer length")
                _append_centerline_fallback("invalid vertex buffer length")
                continue
            tris = _triangles_from_faces(faces_raw, len(vertices) // 3)
            if not tris:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: no triangles")
                _append_centerline_fallback("no triangles")
                continue
            indices = tuple(i for tri in tris for i in tri)
            normals: Tuple[float, ...] = tuple()
            if normals_raw:
                try:
                    normals_candidate = tuple(float(v) for v in normals_raw)
                    if len(normals_candidate) == len(vertices):
                        normals = normals_candidate
                except Exception:
                    normals = tuple()
            bounds = _bounds_from_vertices(vertices) or (aabb_to_bounds_xyz(aabb) if aabb else None)
            payload_meshes.append(
                ModelMeshPayload(
                    id=mesh_id,
                    elementId=guid,
                    vertices=vertices,
                    normals=normals,
                    indices=indices,
                    material=None,
                    aabb=bounds,
                )
            )
            if bounds:
                mesh_bounds.append(bounds)
            continue

        if geom.get("kind") == "centerline":
            line = geom.get("line")
            radius = float(geom.get("radius") or 0.0)
            if not line:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: centerline missing")
                continue
            verts, indices, normals = _tube_mesh_from_centerline(line, radius)
            if not verts or not indices:
                if len(triangulation_failure_samples) < 10:
                    triangulation_failure_samples.append(f"{guid}: centerline triangulation failed")
                continue
            bounds = _bounds_from_vertices(verts) or (aabb_to_bounds_xyz(aabb) if aabb else None)
            payload_meshes.append(
                ModelMeshPayload(
                    id=mesh_id,
                    elementId=guid,
                    vertices=verts,
                    normals=normals,
                    indices=indices,
                    material=None,
                    aabb=bounds,
                )
            )
            if bounds:
                mesh_bounds.append(bounds)

    if no_representation_samples:
        warnings.append(
            "No IFC representation samples: " + "; ".join(no_representation_samples[:10])
        )
    if triangulation_failure_samples:
        warnings.append(
            "Triangulation failure samples: " + "; ".join(triangulation_failure_samples[:10])
        )

    bbox_world = combine_bounds(mesh_bounds if mesh_bounds else fallback_bounds)
    return ModelPayload(
        sourcePath=str(getattr(repository, "path", "") or ""),
        repository=repository,
        elementRefs=elements_map,
        elements=payload_elements,
        elementsParsed=len(payload_elements),
        meshes=payload_meshes,
        aabbs=aabb_lookup,
        bboxWorld=bbox_world,
        warnings=tuple(warnings),
    )
