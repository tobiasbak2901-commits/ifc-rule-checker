from __future__ import annotations

import hashlib
from typing import Iterable, List, Optional, Sequence, Tuple

AABB = Tuple[float, float, float, float, float, float]


def getElementKey(element: object) -> str:
    """Return a stable key for an element.

    Priority:
    1) IFC GlobalId (or equivalent GUID/id field)
    2) hash(ifcType + bbox center + bbox size + trimmed name)
    """
    global_id = _extract_global_id(element)
    if global_id:
        return global_id

    ifc_type = _normalize_text(_extract_value(element, ("ifcType", "ifc_type", "type", "className")) or "Unknown")
    name = _normalize_text(str(_extract_value(element, ("name", "Name")) or "").strip())
    bbox = _extract_bbox(element)
    center, size = _bbox_center_and_size(bbox)

    payload = (
        f"type={ifc_type}|"
        f"center={_fmt(center[0])},{_fmt(center[1])},{_fmt(center[2])}|"
        f"size={_fmt(size[0])},{_fmt(size[1])},{_fmt(size[2])}|"
        f"name={name}"
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"elem:{digest}"


def getModelKey(model: object) -> str:
    """Return a stable content-based model key.

    The key is based on sorted stable element identities and element count.
    """
    element_keys = sorted(set(_iter_model_element_keys(model)))
    payload = "count=" + str(len(element_keys))
    if element_keys:
        payload += "\n" + "\n".join(element_keys)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"model:{digest}"


def get_element_key(element: object) -> str:
    return getElementKey(element)


def get_model_key(model: object) -> str:
    return getModelKey(model)


def _iter_model_element_keys(model: object) -> Iterable[str]:
    # IfcRepository-like object
    elements_attr = getattr(model, "elements", None)
    if isinstance(elements_attr, dict):
        for _k, element in sorted(elements_attr.items(), key=lambda kv: str(kv[0])):
            key = getElementKey(element)
            if key:
                yield key
        return

    # Raw map
    if isinstance(model, dict):
        if isinstance(model.get("elements"), dict):
            for _k, element in sorted((model.get("elements") or {}).items(), key=lambda kv: str(kv[0])):
                key = getElementKey(element)
                if key:
                    yield key
            return
        for _k, element in sorted(model.items(), key=lambda kv: str(kv[0])):
            key = getElementKey(element)
            if key:
                yield key
        return

    # IFC model fallback
    if hasattr(model, "by_type"):
        try:
            products = list(model.by_type("IfcProduct") or [])
        except Exception:
            products = []
        for item in products:
            key = getElementKey(item)
            if key:
                yield key
        return

    # Generic iterable fallback
    if isinstance(model, (list, tuple, set)):
        for item in model:
            key = getElementKey(item)
            if key:
                yield key


def _extract_global_id(element: object) -> str:
    value = _extract_value(
        element,
        (
            "GlobalId",
            "globalId",
            "global_id",
            "guid",
            "Guid",
            "id",
            "elementId",
            "element_id",
        ),
    )
    text = str(value or "").strip()
    return text


def _extract_bbox(element: object) -> Optional[AABB]:
    raw = _extract_value(
        element,
        (
            "aabbWorld",
            "aabb",
            "bbox",
            "bounds",
            "aabb_world",
        ),
    )
    box = _to_bbox(raw)
    if box is not None:
        return box
    meta = _extract_value(element, ("ifc_meta", "meta"))
    if isinstance(meta, dict):
        for key in ("aabbWorld", "aabb", "bbox", "bounds"):
            box = _to_bbox(meta.get(key))
            if box is not None:
                return box
    return None


def _to_bbox(raw: object) -> Optional[AABB]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 6:
        return None
    out: List[float] = []
    for value in raw:
        try:
            out.append(float(value))
        except Exception:
            return None
    return (out[0], out[1], out[2], out[3], out[4], out[5])


def _bbox_center_and_size(bbox: Optional[AABB]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not bbox:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    min_x, min_y, min_z, max_x, max_y, max_z = [float(v) for v in bbox]
    center = (
        (min_x + max_x) * 0.5,
        (min_y + max_y) * 0.5,
        (min_z + max_z) * 0.5,
    )
    size = (
        abs(max_x - min_x),
        abs(max_y - min_y),
        abs(max_z - min_z),
    )
    return center, size


def _extract_value(source: object, keys: Sequence[str]) -> object:
    if isinstance(source, dict):
        for key in keys:
            if key in source:
                return source.get(key)
        return None

    for key in keys:
        if not hasattr(source, key):
            continue
        value = getattr(source, key, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value is not None:
            return value
    return None


def _normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


def _fmt(value: float) -> str:
    return f"{float(value):.6f}"
