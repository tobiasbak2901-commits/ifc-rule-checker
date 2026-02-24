from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from clash_detection import Bounds, build_world_bounds
from identity_keys import getElementKey
from models import Element

Point3 = Tuple[float, float, float]
AABB = Tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class ProxyAABB:
    min: Point3
    max: Point3


@dataclass(frozen=True)
class ProxyAxis:
    p0: Point3
    p1: Point3


@dataclass(frozen=True)
class ProxyRect:
    w: float
    h: float


@dataclass(frozen=True)
class GeometryProxy:
    elementId: str
    elementKey: str
    modelKey: str
    ifcType: str
    aabb: ProxyAABB
    centroid: Point3
    kind: str
    hasRenderableGeometry: bool
    axis: Optional[ProxyAxis] = None
    radius: Optional[float] = None
    rect: Optional[ProxyRect] = None

    def to_dict(self) -> Dict[str, object]:
        out: Dict[str, object] = {
            "elementKey": str(self.elementKey),
            "modelKey": str(self.modelKey),
            "ifcType": str(self.ifcType),
            "aabb": {
                "min": tuple(float(v) for v in self.aabb.min),
                "max": tuple(float(v) for v in self.aabb.max),
            },
            "centroid": tuple(float(v) for v in self.centroid),
            "kind": str(self.kind),
        }
        if self.axis is not None:
            out["axis"] = {
                "p0": tuple(float(v) for v in self.axis.p0),
                "p1": tuple(float(v) for v in self.axis.p1),
            }
        if self.radius is not None:
            out["radius"] = float(self.radius)
        if self.rect is not None:
            out["rect"] = {"w": float(self.rect.w), "h": float(self.rect.h)}
        return out


def build_proxies_for_model(
    *,
    elements: Dict[str, Element],
    bounds_map: Dict[str, Bounds],
    model_key: str = "",
) -> List[GeometryProxy]:
    ids = sorted(set(str(v) for v in list(elements.keys()) + list(bounds_map.keys()) if v))
    builder = ProxyBuilder(default_model_key=str(model_key or ""))
    by_id = builder.build(element_ids=ids, bounds_map=bounds_map, elements=elements)
    return [by_id[g] for g in sorted(by_id.keys())]


def build_proxies_from_payload(payload: Any, *, model_key: str = "") -> List[GeometryProxy]:
    if payload is None:
        return []
    bounds_map = build_world_bounds(payload)
    elements = dict(getattr(payload, "elementRefs", {}) or {})
    repository = getattr(payload, "repository", None)
    default_model_key = str(model_key or getattr(repository, "model_key", "") or "")
    return build_proxies_for_model(
        elements=elements,
        bounds_map=bounds_map,
        model_key=default_model_key,
    )


class ProxyBuilder:
    def __init__(self, *, default_model_key: str = ""):
        self.default_model_key = str(default_model_key or "").strip()

    def build(
        self,
        *,
        element_ids: Iterable[str],
        bounds_map: Dict[str, Bounds],
        elements: Dict[str, Element],
    ) -> Dict[str, GeometryProxy]:
        out: Dict[str, GeometryProxy] = {}
        for guid in sorted(set(str(v) for v in list(element_ids or []) if v)):
            bound = bounds_map.get(guid)
            if not isinstance(bound, Bounds):
                continue
            proxy = self._build_one(guid=guid, bound=bound, element=elements.get(guid))
            if proxy is not None:
                out[guid] = proxy
        return out

    def _build_one(
        self,
        *,
        guid: str,
        bound: Bounds,
        element: Optional[Element],
    ) -> Optional[GeometryProxy]:
        aabb = _safe_aabb(getattr(bound, "aabbWorld", None))
        if aabb is None:
            return None
        min_x, min_y, min_z, max_x, max_y, max_z = aabb
        centroid: Point3 = (
            (min_x + max_x) * 0.5,
            (min_y + max_y) * 0.5,
            (min_z + max_z) * 0.5,
        )
        extents = (
            abs(max_x - min_x),
            abs(max_y - min_y),
            abs(max_z - min_z),
        )
        ifc_type = str(getattr(element, "type", "") or "").strip() or "IfcProduct"
        kind = _infer_kind(ifc_type)
        model_key = self._resolve_model_key(element)
        element_key = self._resolve_element_key(guid, element)

        axis = None
        radius = None
        rect = None
        axis_points = _safe_axis(getattr(bound, "centerlineWorld", None))
        if axis_points is None and kind in ("pipe", "duct", "cabletray"):
            axis_points = _axis_from_aabb(aabb)
        if axis_points is not None:
            axis = ProxyAxis(p0=axis_points[0], p1=axis_points[1])

        primary_axis = _primary_axis(axis_points, extents)
        orth_dims = _orthogonal_dims(extents, primary_axis)
        bound_radius = _safe_positive_float(getattr(bound, "radiusWorld", None))
        if kind == "pipe":
            fallback_radius = min(orth_dims) * 0.5 if orth_dims else 0.0
            chosen_radius = bound_radius if bound_radius is not None else fallback_radius
            if chosen_radius > 0.0:
                radius = float(chosen_radius)
        elif kind in ("duct", "cabletray"):
            if len(orth_dims) == 2 and orth_dims[0] > 0.0 and orth_dims[1] > 0.0:
                rect = ProxyRect(w=float(orth_dims[0]), h=float(orth_dims[1]))
            if bound_radius is not None and bound_radius > 0.0:
                radius = float(bound_radius)

        # For "generic" elements we intentionally keep only AABB+centroid.
        return GeometryProxy(
            elementId=str(guid),
            elementKey=str(element_key),
            modelKey=str(model_key),
            ifcType=str(ifc_type),
            aabb=ProxyAABB(min=(min_x, min_y, min_z), max=(max_x, max_y, max_z)),
            centroid=centroid,
            kind=str(kind),
            hasRenderableGeometry=bool(getattr(bound, "hasRenderableGeometry", False)),
            axis=axis,
            radius=radius,
            rect=rect,
        )

    def _resolve_model_key(self, element: Optional[Element]) -> str:
        if element is None:
            return self.default_model_key
        meta = dict(getattr(element, "ifc_meta", {}) or {})
        for key in ("modelKey", "model_key", "modelId", "model_id", "model"):
            value = str(meta.get(key, "") or "").strip()
            if value:
                return value
        return self.default_model_key

    def _resolve_element_key(self, guid: str, element: Optional[Element]) -> str:
        if element is not None:
            meta = dict(getattr(element, "ifc_meta", {}) or {})
            for key in ("elementKey", "element_key"):
                value = str(meta.get(key, "") or "").strip()
                if value:
                    return value
            candidate = str(getElementKey(element) or "").strip()
            if candidate:
                return candidate
        return str(guid or "").strip()


def _safe_positive_float(value: object) -> Optional[float]:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except Exception:
        return None
    if numeric <= 0.0:
        return None
    return numeric


def _safe_aabb(value: object) -> Optional[AABB]:
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        return None
    out: List[float] = []
    for item in value:
        try:
            out.append(float(item))
        except Exception:
            return None
    if out[3] < out[0] or out[4] < out[1] or out[5] < out[2]:
        return None
    return (out[0], out[1], out[2], out[3], out[4], out[5])


def _safe_axis(value: object) -> Optional[Tuple[Point3, Point3]]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    p0 = value[0]
    p1 = value[1]
    if not isinstance(p0, (list, tuple)) or not isinstance(p1, (list, tuple)):
        return None
    if len(p0) != 3 or len(p1) != 3:
        return None
    try:
        q0 = (float(p0[0]), float(p0[1]), float(p0[2]))
        q1 = (float(p1[0]), float(p1[1]), float(p1[2]))
    except Exception:
        return None
    return (q0, q1)


def _infer_kind(ifc_type: str) -> str:
    t = str(ifc_type or "").lower()
    if "pipe" in t:
        return "pipe"
    if "duct" in t:
        return "duct"
    if "cabletray" in t or "cable tray" in t:
        return "cabletray"
    return "generic"


def _axis_from_aabb(aabb: AABB) -> Optional[Tuple[Point3, Point3]]:
    min_x, min_y, min_z, max_x, max_y, max_z = [float(v) for v in aabb]
    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5
    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    if dx <= 0.0 and dy <= 0.0 and dz <= 0.0:
        return None
    if dx >= dy and dx >= dz:
        return ((min_x, cy, cz), (max_x, cy, cz))
    if dy >= dx and dy >= dz:
        return ((cx, min_y, cz), (cx, max_y, cz))
    return ((cx, cy, min_z), (cx, cy, max_z))


def _primary_axis(axis: Optional[Tuple[Point3, Point3]], extents: Tuple[float, float, float]) -> int:
    if axis is not None:
        p0, p1 = axis
        delta = (
            abs(float(p1[0]) - float(p0[0])),
            abs(float(p1[1]) - float(p0[1])),
            abs(float(p1[2]) - float(p0[2])),
        )
        if delta[0] >= delta[1] and delta[0] >= delta[2]:
            return 0
        if delta[1] >= delta[0] and delta[1] >= delta[2]:
            return 1
        return 2
    if extents[0] >= extents[1] and extents[0] >= extents[2]:
        return 0
    if extents[1] >= extents[0] and extents[1] >= extents[2]:
        return 1
    return 2


def _orthogonal_dims(extents: Tuple[float, float, float], primary_axis: int) -> Tuple[float, float]:
    if primary_axis == 0:
        return (float(extents[1]), float(extents[2]))
    if primary_axis == 1:
        return (float(extents[0]), float(extents[2]))
    return (float(extents[0]), float(extents[1]))
