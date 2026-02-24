from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Dict, Tuple, Optional, List, Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ifc_element
import ifcopenshell.util.unit as ifc_unit

from geometry import aabb_from_verts
from identity_keys import getElementKey, getModelKey
from models import Element

UNITS_SCALE = 1.0


@dataclass
class IfcRepository:
    path: str
    model_key: str
    model: object
    settings: object
    length_unit_m: float
    elements: Dict[str, Element]
    aabbs: Dict[str, Tuple[float, float, float, float, float, float]]
    units_scale: float = 1.0
    skipped_products: int = 0
    skipped_samples: Optional[List[str]] = None
    geometry_pipeline: str = "custom"
    shape_generation_enabled: bool = True
    _shape_cache: Dict[str, Optional[object]] = field(default_factory=dict)
    _shape_failures: Dict[str, str] = field(default_factory=dict)
    _fallback_settings: Optional[object] = None

    def set_shape_generation_enabled(self, enabled: bool) -> None:
        enabled_flag = bool(enabled)
        if enabled_flag == bool(self.shape_generation_enabled):
            return
        self.shape_generation_enabled = enabled_flag
        # Clear cached shape results so mode switches are deterministic.
        self._shape_cache.clear()
        self._shape_failures.clear()

    def get_shape(self, guid):
        if not bool(self.shape_generation_enabled):
            return None
        if guid in self._shape_cache:
            return self._shape_cache[guid]
        entity = self.model.by_guid(guid)
        if not entity:
            self._shape_cache[guid] = None
            self._shape_failures[guid] = "IFC entity not found."
            return None
        representation = getattr(entity, "Representation", None)
        if representation is None:
            self._shape_cache[guid] = None
            self._shape_failures[guid] = "No IFC representation."
            return None

        shape = None
        last_error = None
        for settings in self._iter_geometry_settings():
            try:
                candidate = ifcopenshell.geom.create_shape(settings, entity)
            except Exception as exc:
                last_error = str(exc)
                continue
            if candidate is None:
                continue
            geom = getattr(candidate, "geometry", None)
            verts = getattr(geom, "verts", None) if geom is not None else None
            has_vertices = False
            try:
                has_vertices = bool(verts is not None and len(verts) >= 9)
            except Exception:
                has_vertices = False
            if has_vertices:
                shape = candidate
                break
        self._shape_cache[guid] = shape
        if shape is None and last_error:
            self._shape_failures[guid] = last_error
        return shape

    def get_aabb(self, guid):
        if guid in self.aabbs:
            return self.aabbs[guid]
        entity = self.model.by_guid(guid)
        if not entity:
            return None
        shape = self.get_shape(guid)
        aabb = None
        if shape is not None:
            try:
                aabb = aabb_from_verts(shape.geometry.verts)
            except Exception:
                aabb = None
        if aabb is None:
            aabb = self._fallback_aabb_from_entity(guid, entity)
            if bool(self.shape_generation_enabled) and aabb is not None and guid not in self._shape_failures:
                self._shape_failures[guid] = "Shape triangulation failed; using placement fallback AABB."
        if aabb is None:
            return None
        self.aabbs[guid] = aabb
        return aabb

    def get_element_geom(self, guid):
        elem = self.elements.get(guid)
        if not elem:
            return None
        shape = self.get_shape(guid)
        if shape is not None:
            return {"kind": "mesh", "shape": shape}
        aabb = self.get_aabb(guid)
        if aabb is None:
            return None
        if _is_linear_ifc_type(elem.type):
            line, radius = _centerline_from_aabb(aabb)
            return {"kind": "centerline", "line": line, "radius": radius}
        return None

    def get_shape_error(self, guid: str) -> Optional[str]:
        if not bool(self.shape_generation_enabled):
            return "Shape generation disabled (safe import mode)."
        return self._shape_failures.get(guid)

    def recent_shape_errors(self, limit: int = 5) -> List[str]:
        if not bool(self.shape_generation_enabled):
            return []
        if limit <= 0:
            return []
        values = [f"{guid}: {msg}" for guid, msg in self._shape_failures.items() if msg]
        return values[:limit]

    def _iter_geometry_settings(self):
        yield self.settings
        if self._fallback_settings is None:
            fallback = ifcopenshell.geom.settings()

            def _safe_setting(name: str, value):
                try:
                    fallback.set(name, value)
                except Exception:
                    pass

            _safe_setting("use-world-coords", True)
            _safe_setting("triangulation-type", 1)
            _safe_setting("use-python-opencascade", False)
            self._fallback_settings = fallback
        if self._fallback_settings is not None:
            yield self._fallback_settings

    def _fallback_aabb_from_entity(self, guid: str, entity) -> Optional[Tuple[float, float, float, float, float, float]]:
        origin = self._entity_world_origin(entity)
        if origin is None:
            origin = self._guid_fallback_origin(guid)
        if origin is None:
            return None
        elem = self.elements.get(guid)
        elem_type = str(elem.type if elem else "")
        unit_to_model = 1.0 / max(float(self.length_unit_m or 1.0), 1e-9)
        default_len = max(1.0 * unit_to_model, 0.5)
        default_radius = max(0.05 * unit_to_model, 0.02)
        if _is_linear_ifc_type(elem_type):
            length = self._element_numeric_hint(
                elem,
                tokens=("length", "overall length", "nominal length"),
                fallback=default_len,
            )
            diameter = self._element_numeric_hint(
                elem,
                tokens=("outside diameter", "nominal diameter", "diameter"),
                fallback=default_radius * 2.0,
            )
            radius = max(float(diameter) * 0.5, default_radius)
            half = max(float(length) * 0.5, radius * 2.0)
            return (
                origin[0] - half,
                origin[1] - radius,
                origin[2] - radius,
                origin[0] + half,
                origin[1] + radius,
                origin[2] + radius,
            )
        half_box = max(0.15 * unit_to_model, 0.05)
        return (
            origin[0] - half_box,
            origin[1] - half_box,
            origin[2] - half_box,
            origin[0] + half_box,
            origin[1] + half_box,
            origin[2] + half_box,
        )

    def _element_numeric_hint(
        self,
        elem: Optional[Element],
        *,
        tokens: tuple[str, ...],
        fallback: float,
    ) -> float:
        if elem is None:
            return float(fallback)
        token_set = tuple(t.lower() for t in tokens)
        pools = [elem.qtos, elem.psets, elem.type_qtos, elem.type_psets]
        for pool in pools:
            if not isinstance(pool, dict):
                continue
            for props in pool.values():
                if not isinstance(props, dict):
                    continue
                for key, value in props.items():
                    if not isinstance(value, (int, float)):
                        continue
                    key_l = str(key).lower()
                    if any(token in key_l for token in token_set):
                        numeric = float(value)
                        if numeric > 0.0:
                            return numeric
                    if "radius" in key_l and any("diameter" in t for t in token_set):
                        numeric = float(value) * 2.0
                        if numeric > 0.0:
                            return numeric
        return float(fallback)

    def _entity_world_origin(self, entity) -> Optional[Tuple[float, float, float]]:
        placement = getattr(entity, "ObjectPlacement", None)
        x = y = z = 0.0
        found = False
        depth = 0
        while placement is not None and depth < 32:
            relative = getattr(placement, "RelativePlacement", None)
            location = getattr(relative, "Location", None) if relative is not None else None
            coords = getattr(location, "Coordinates", None) if location is not None else None
            if coords is not None:
                try:
                    vals = [float(v) for v in coords]
                    if vals:
                        x += vals[0]
                        y += vals[1] if len(vals) > 1 else 0.0
                        z += vals[2] if len(vals) > 2 else 0.0
                        found = True
                except Exception:
                    pass
            placement = getattr(placement, "PlacementRelTo", None)
            depth += 1
        if not found:
            return None
        return (x, y, z)

    def _guid_fallback_origin(self, guid: str) -> Optional[Tuple[float, float, float]]:
        if not guid:
            return None
        digest = hashlib.sha1(guid.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        step = max(0.6 / max(float(self.length_unit_m or 1.0), 1e-9), 0.2)
        ix = ((seed >> 0) & 0xF) - 8
        iy = ((seed >> 4) & 0xF) - 8
        iz = ((seed >> 8) & 0x7) - 3
        return (float(ix) * step, float(iy) * step, float(iz) * step)

    def get_element_diameter(self, guid: str) -> Optional[float]:
        ifc_elem = self.model.by_guid(guid)
        if not ifc_elem:
            return None
        try:
            psets = ifc_element.get_psets(ifc_elem)
        except Exception:
            psets = {}
        diameter = None
        for pset in psets.values():
            if not isinstance(pset, dict):
                continue
            for key, value in pset.items():
                if not isinstance(value, (int, float)):
                    continue
                k = str(key).lower()
                if "outside diameter" in k:
                    return float(value)
                if "diameter" in k:
                    diameter = float(value)
                if "radius" in k and diameter is None:
                    diameter = float(value) * 2.0
        if diameter is not None:
            return diameter
        try:
            aabb = self.get_aabb(guid)
        except Exception:
            return None
        if aabb is None:
            return None
        dx = aabb[3] - aabb[0]
        dy = aabb[4] - aabb[1]
        dz = aabb[5] - aabb[2]
        dims = [d for d in (dx, dy, dz) if d > 0]
        if not dims:
            return None
        return min(dims)

    def get_element_length(self, guid: str) -> Optional[float]:
        geom = self.get_element_geom(guid)
        if not geom:
            return None
        if geom.get("kind") == "centerline":
            p0, p1 = geom.get("line") or ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            dx = float(p1[0]) - float(p0[0])
            dy = float(p1[1]) - float(p0[1])
            dz = float(p1[2]) - float(p0[2])
            return (dx * dx + dy * dy + dz * dz) ** 0.5
        try:
            aabb = self.get_aabb(guid)
        except Exception:
            return None
        if aabb is None:
            return None
        dx = float(aabb[3]) - float(aabb[0])
        dy = float(aabb[4]) - float(aabb[1])
        dz = float(aabb[5]) - float(aabb[2])
        return max(dx, dy, dz)


def _safe_name(e) -> str:
    return (getattr(e, "Name", None) or "").strip() or e.is_a()


def _safe_psets(e) -> Dict[str, Dict[str, object]]:
    try:
        psets = ifc_element.get_psets(e)
    except Exception:
        return {}
    if not isinstance(psets, dict):
        return {}
    cleaned: Dict[str, Dict[str, object]] = {}
    for pset_name, props in psets.items():
        if isinstance(pset_name, str) and isinstance(props, dict):
            cleaned[pset_name] = props
    return cleaned


def _safe_attr(e, name: str) -> Optional[object]:
    if not e:
        return None
    value = getattr(e, name, None)
    if callable(value):
        try:
            value = value()
        except Exception:
            value = None
    return value


def _split_psets(psets: Dict[str, Dict[str, object]]):
    prop_sets: Dict[str, Dict[str, object]] = {}
    qtos: Dict[str, Dict[str, object]] = {}
    for name, props in psets.items():
        if isinstance(name, str) and name.startswith("Qto_"):
            qtos[name] = props
        else:
            prop_sets[name] = props
    return prop_sets, qtos


def _extract_system_group_names(e) -> List[str]:
    names: List[str] = []
    try:
        groups = ifc_element.get_groups(e)
    except Exception:
        groups = []
    for group in groups or []:
        for attr in ("Name", "Description"):
            try:
                value = getattr(group, attr, None)
            except Exception:
                value = None
            if value:
                names.append(str(value))
    try:
        assignments = getattr(e, "HasAssignments", None) or []
    except Exception:
        assignments = []
    for rel in assignments:
        try:
            if not rel or not rel.is_a("IfcRelAssignsToGroup"):
                continue
        except Exception:
            continue
        group = getattr(rel, "RelatingGroup", None)
        if not group:
            continue
        for attr in ("Name", "Description"):
            try:
                value = getattr(group, attr, None)
            except Exception:
                value = None
            if value:
                names.append(str(value))
    return sorted({n for n in names if n})


def _extract_layer_names(e) -> List[str]:
    names: List[str] = []
    try:
        layers = ifc_element.get_layers(e)
    except Exception:
        layers = []
    for layer in layers or []:
        for attr in ("Name", "Identifier", "Description"):
            try:
                value = getattr(layer, attr, None)
            except Exception:
                value = None
            if value:
                names.append(str(value))
    return sorted({n for n in names if n})


def _extract_metadata(e, model) -> Dict[str, Any]:
    item = {
        "ifcType": e.is_a() if e else None,
        "GlobalId": _safe_attr(e, "GlobalId"),
        "Name": _safe_attr(e, "Name"),
        "Description": _safe_attr(e, "Description"),
        "ObjectType": _safe_attr(e, "ObjectType"),
        "PredefinedType": _safe_attr(e, "PredefinedType"),
        "Tag": _safe_attr(e, "Tag"),
    }
    type_obj = None
    try:
        type_obj = ifc_element.get_type(e)
    except Exception:
        type_obj = None
    type_item = {}
    if type_obj:
        type_item = {
            "ifcType": type_obj.is_a() if type_obj else None,
            "Name": _safe_attr(type_obj, "Name"),
            "Description": _safe_attr(type_obj, "Description"),
            "ObjectType": _safe_attr(type_obj, "ObjectType"),
            "PredefinedType": _safe_attr(type_obj, "PredefinedType"),
            "Tag": _safe_attr(type_obj, "Tag"),
        }
    psets_raw = _safe_psets(e)
    psets, qtos = _split_psets(psets_raw)
    type_psets_raw = _safe_psets(type_obj) if type_obj else {}
    type_psets, type_qtos = _split_psets(type_psets_raw)
    system_groups = _extract_system_group_names(e)
    layer_names = _extract_layer_names(e)
    return {
        "item": item,
        "type": type_item,
        "system_groups": system_groups,
        "systems": system_groups,
        "layers": layer_names,
        "psets": psets,
        "qtos": qtos,
        "type_psets": type_psets,
        "type_qtos": type_qtos,
    }


def _extract_system_name(psets: Dict[str, Dict[str, object]]) -> Optional[str]:
    for props in psets.values():
        if not isinstance(props, dict):
            continue
        for key, value in props.items():
            if value is None:
                continue
            k = str(key).lower()
            if "system" in k:
                return str(value)
    return None


def _guess_discipline(name: str, ifc_type: str) -> str:
    hay = f"{name} {ifc_type}".lower()
    if "dræn" in hay or "drain" in hay:
        return "Drainage"
    if "pipe" in hay or "rør" in hay or "brugsvand" in hay or "water" in hay:
        return "Plumbing"
    if "duct" in hay or "vent" in hay:
        return "HVAC"
    if "cable" in hay or "elec" in hay:
        return "Electrical"
    if "wall" in hay or "slab" in hay or "beam" in hay or "column" in hay:
        return "Structural"
    return "Unknown"


def _is_linear_ifc_type(ifc_type: str) -> bool:
    hay = str(ifc_type or "").lower()
    return any(token in hay for token in ("pipe", "duct", "conduit", "cable", "flowsegment"))


def _centerline_from_aabb(aabb: Tuple[float, float, float, float, float, float]):
    minx, miny, minz, maxx, maxy, maxz = aabb
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    cz = (minz + maxz) / 2.0
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    if dx >= dy and dx >= dz:
        p0 = (minx, cy, cz)
        p1 = (maxx, cy, cz)
        radius = min(dy, dz) / 2.0
    elif dy >= dx and dy >= dz:
        p0 = (cx, miny, cz)
        p1 = (cx, maxy, cz)
        radius = min(dx, dz) / 2.0
    else:
        p0 = (cx, cy, minz)
        p1 = (cx, cy, maxz)
        radius = min(dx, dy) / 2.0
    return (p0, p1), max(radius, 0.001)


def load_ifc(path: str) -> IfcRepository:
    global UNITS_SCALE
    path = str(path or "").strip()
    if not path:
        raise ValueError("Empty IFC path")
    model = ifcopenshell.open(path)
    settings = ifcopenshell.geom.settings()

    def _safe_setting(name: str, value):
        try:
            settings.set(name, value)
            return True
        except Exception:
            return False

    _safe_setting("use-world-coords", True)
    # Improve tessellation for curved MEP elements, but keep it best-effort
    _safe_setting("circle-segments", 32)
    _safe_setting("mesher-linear-deflection", 0.001)
    _safe_setting("mesher-angular-deflection", 0.2)
    _safe_setting("triangulation-type", 1)
    _safe_setting("use-python-opencascade", False)
    try:
        length_unit_m = float(ifc_unit.calculate_unit_scale(model))
    except Exception:
        length_unit_m = 1.0
    if length_unit_m <= 0:
        length_unit_m = 1.0
    UNITS_SCALE = float(length_unit_m)

    elements: Dict[str, Element] = {}
    skipped_products = 0
    skipped_samples: List[str] = []
    for e in model.by_type("IfcProduct"):
        try:
            guid = getattr(e, "GlobalId", None)
            if not guid:
                continue
            name = _safe_name(e)
            meta = _extract_metadata(e, model)
            psets = meta.get("psets", {})
            qtos = meta.get("qtos", {})
            type_item = meta.get("type", {}) or {}
            type_psets = meta.get("type_psets", {})
            type_qtos = meta.get("type_qtos", {})
            system_groups = meta.get("system_groups", []) or []
            layer_names = meta.get("layers", []) or []
            system = system_groups[0] if system_groups else _extract_system_name(psets)
            ifc_type = e.is_a()
            discipline = _guess_discipline(name, ifc_type)
            elem = Element(
                guid=guid,
                type=ifc_type,
                discipline=discipline,
                geom_ref=guid,
                name=name,
                system=system,
                psets=psets,
                qtos=qtos,
                type_name=type_item.get("Name") or None,
                type_psets=type_psets,
                type_qtos=type_qtos,
                systems=system_groups,
                system_group_names=system_groups,
                ifc_meta=meta,
                layers=layer_names,
            )
            elem.ifc_meta["elementKey"] = getElementKey(elem)
            elements[guid] = elem
        except Exception as exc:
            skipped_products += 1
            if len(skipped_samples) < 5:
                e_type = "IfcProduct"
                try:
                    e_type = e.is_a() if e is not None else "IfcProduct"
                except Exception:
                    pass
                skipped_samples.append(f"{e_type}: {exc}")
            continue

    model_key = getModelKey(elements)
    for elem in elements.values():
        if not isinstance(elem.ifc_meta, dict):
            elem.ifc_meta = {}
        elem.ifc_meta["modelKey"] = model_key

    return IfcRepository(
        path=path,
        model_key=model_key,
        model=model,
        settings=settings,
        length_unit_m=length_unit_m,
        elements=elements,
        aabbs={},
        units_scale=float(UNITS_SCALE),
        skipped_products=skipped_products,
        skipped_samples=skipped_samples,
        geometry_pipeline="custom",
    )
