from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import hashlib
import math
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from clash_detection import Bounds
from models import Element, Issue

from .grouping import LevelInterval, build_clash_groups, level_for_point_z, midpoint_proximity_cell
from .broadphase import CandidatePair, broadphase
from .narrowphase_v1 import clash_verdict_v1, run_narrowphase_v1
from .models import (
    ClashGroup,
    ClashResult,
    ClashResultStatus,
    ClashTest,
    ClashType,
    IGNORE_IFCTYPE_IN,
    IGNORE_NAME_PATTERN,
    IGNORE_SAME_ELEMENT,
    IGNORE_SAME_FILE,
    IGNORE_SAME_SYSTEM,
    Viewpoint,
    ignore_rule_enabled,
)
from .proxy_builder import GeometryProxy, ProxyBuilder


@dataclass(frozen=True)
class ClashRunOutput:
    issues: List[Issue]
    results: List[ClashResult]
    groups: List[ClashGroup]
    viewpoints: List[Viewpoint]
    skipped_ignored: int


@dataclass
class ClashRunCache:
    proxy_by_identity: Dict[str, GeometryProxy] = field(default_factory=dict)
    guid_identity_map: Dict[str, str] = field(default_factory=dict)
    guid_fingerprint_map: Dict[str, Tuple[str, str, Tuple[Any, ...]]] = field(default_factory=dict)
    candidate_pairs_cache: "OrderedDict[str, List[Tuple[str, str, str, str]]]" = field(default_factory=OrderedDict)
    narrowphase_cache: "OrderedDict[str, Dict[str, Any]]" = field(default_factory=OrderedDict)
    clash_key_cache: "OrderedDict[str, str]" = field(default_factory=OrderedDict)
    issue_lookup: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    max_candidate_cache_entries: int = 6
    max_narrowphase_cache_entries: int = 250_000
    max_clash_key_cache_entries: int = 250_000

    def clear(self) -> None:
        self.proxy_by_identity.clear()
        self.guid_identity_map.clear()
        self.guid_fingerprint_map.clear()
        self.candidate_pairs_cache.clear()
        self.narrowphase_cache.clear()
        self.clash_key_cache.clear()
        self.issue_lookup.clear()


def _midpoint(p_a: Optional[Tuple[float, float, float]], p_b: Optional[Tuple[float, float, float]]) -> Optional[Tuple[float, float, float]]:
    if p_a is None or p_b is None:
        return None
    return (
        (float(p_a[0]) + float(p_b[0])) * 0.5,
        (float(p_a[1]) + float(p_b[1])) * 0.5,
        (float(p_a[2]) + float(p_b[2])) * 0.5,
    )


def _aabb_center(aabb: Tuple[float, float, float, float, float, float]) -> Tuple[float, float, float]:
    return (
        (float(aabb[0]) + float(aabb[3])) * 0.5,
        (float(aabb[1]) + float(aabb[4])) * 0.5,
        (float(aabb[2]) + float(aabb[5])) * 0.5,
    )


def _fallback_midpoint(aabb_a: Tuple[float, float, float, float, float, float], aabb_b: Tuple[float, float, float, float, float, float]) -> Tuple[float, float, float]:
    c_a = _aabb_center(aabb_a)
    c_b = _aabb_center(aabb_b)
    return (
        (float(c_a[0]) + float(c_b[0])) * 0.5,
        (float(c_a[1]) + float(c_b[1])) * 0.5,
        (float(c_a[2]) + float(c_b[2])) * 0.5,
    )


def _hash_payload(payload: str) -> str:
    return hashlib.sha1(str(payload or "").encode("utf-8")).hexdigest()


def _quantize(value: float, step: float = 0.01) -> float:
    q_step = max(1.0e-6, float(step or 0.01))
    return round(float(value) / q_step) * q_step


def _quantized_point(point: Tuple[float, float, float], step: float = 0.01) -> Tuple[float, float, float]:
    return (
        float(_quantize(point[0], step)),
        float(_quantize(point[1], step)),
        float(_quantize(point[2], step)),
    )


def _proxy_dimensions(proxy: GeometryProxy) -> Tuple[float, float, float]:
    return (
        float(proxy.aabb.max[0]) - float(proxy.aabb.min[0]),
        float(proxy.aabb.max[1]) - float(proxy.aabb.min[1]),
        float(proxy.aabb.max[2]) - float(proxy.aabb.min[2]),
    )


def _element_signature(proxy: GeometryProxy, *, quant_step_m: float = 0.01) -> str:
    dims = _proxy_dimensions(proxy)
    centroid_q = _quantized_point(proxy.centroid, quant_step_m)
    payload = (
        f"elementKey={str(proxy.elementKey or '')}|"
        f"dims={dims[0]:.3f},{dims[1]:.3f},{dims[2]:.3f}|"
        f"centroid={centroid_q[0]:.3f},{centroid_q[1]:.3f},{centroid_q[2]:.3f}"
    )
    return f"esig:{_hash_payload(payload)}"


def _clash_key(
    *,
    proxy_a: GeometryProxy,
    proxy_b: GeometryProxy,
    clash_type: ClashType,
    centroid: Tuple[float, float, float],
    quant_step_m: float = 0.01,
) -> Tuple[str, str, str, Tuple[float, float, float]]:
    sig_a = _element_signature(proxy_a, quant_step_m=quant_step_m)
    sig_b = _element_signature(proxy_b, quant_step_m=quant_step_m)
    left, right = sorted((sig_a, sig_b))
    centroid_q = _quantized_point(centroid, quant_step_m)
    payload = (
        f"elements={left}|{right}|"
        f"centroid={centroid_q[0]:.3f},{centroid_q[1]:.3f},{centroid_q[2]:.3f}|"
        f"type={str(clash_type.value)}"
    )
    return f"clash:{_hash_payload(payload)}", sig_a, sig_b, centroid_q


def _cache_set_limited(ordered_map: "OrderedDict[str, Any]", key: str, value: Any, max_entries: int) -> None:
    if key in ordered_map:
        ordered_map.move_to_end(key)
    ordered_map[key] = value
    limit = max(1, int(max_entries or 1))
    while len(ordered_map) > limit:
        ordered_map.popitem(last=False)


def _element_geometry_fingerprint(bound: Bounds) -> Tuple[Any, ...]:
    aabb = tuple(float(v) for v in tuple(getattr(bound, "aabbWorld", ()) or ()))
    centerline_raw = getattr(bound, "centerlineWorld", None)
    centerline: Tuple[float, ...] = ()
    if isinstance(centerline_raw, (list, tuple)) and len(centerline_raw) == 2:
        p0 = centerline_raw[0] if isinstance(centerline_raw[0], (list, tuple)) else ()
        p1 = centerline_raw[1] if isinstance(centerline_raw[1], (list, tuple)) else ()
        if len(p0) == 3 and len(p1) == 3:
            centerline = tuple(float(v) for v in (p0[0], p0[1], p0[2], p1[0], p1[1], p1[2]))
    radius = getattr(bound, "radiusWorld", None)
    try:
        radius_value = float(radius) if radius is not None else 0.0
    except Exception:
        radius_value = 0.0
    return (
        aabb,
        centerline,
        float(radius_value),
        1 if bool(getattr(bound, "hasRenderableGeometry", False)) else 0,
    )


def _element_geometry_signature(bound: Bounds) -> str:
    payload = repr(_element_geometry_fingerprint(bound))
    return f"geom:{_hash_payload(payload)}"


def _element_key_for_cache(guid: str, elem: Optional[Element]) -> str:
    if elem is not None:
        meta = dict(getattr(elem, "ifc_meta", {}) or {})
        for key in ("elementKey", "element_key"):
            value = str(meta.get(key, "") or "").strip()
            if value:
                return value
    return str(guid or "").strip()


def _model_key_for_cache(elem: Optional[Element], default_model_ref: str = "") -> str:
    model_ref = _element_model_ref(elem)
    if model_ref:
        return model_ref
    return str(default_model_ref or "").strip().lower()


def _proxy_identity_key(guid: str, elem: Optional[Element], bound: Bounds, default_model_ref: str = "") -> str:
    model_key = _model_key_for_cache(elem, default_model_ref=default_model_ref)
    element_key = _element_key_for_cache(guid, elem)
    geometry_sig = _element_geometry_signature(bound)
    return f"{model_key}|{element_key}|{geometry_sig}"


def _element_system(elem: Optional[Element]) -> str:
    if elem is None:
        return ""
    systems = list(elem.system_group_names or elem.systems or [])
    if systems:
        return str(systems[0] or "").strip().lower()
    system_value = str(elem.system or "").strip().lower()
    if system_value:
        return system_value
    utility_type = str(getattr(elem, "utility_type", "") or "").strip().lower()
    if utility_type:
        return utility_type
    class_name = str(getattr(elem, "class_name", "") or "").strip().lower()
    if class_name:
        return class_name
    meta = dict(getattr(elem, "ifc_meta", {}) or {})
    for key in ("system", "System", "system_name", "systemName"):
        value = str(meta.get(key, "") or "").strip().lower()
        if value:
            return value
    return ""


def _element_model_ref(elem: Optional[Element]) -> str:
    if elem is None:
        return ""
    meta = dict(elem.ifc_meta or {})
    for key in ("modelKey", "model_key", "source_file", "sourceFile", "model", "model_id", "modelId"):
        value = meta.get(key)
        if value:
            return str(value).strip().lower()
    item = dict(meta.get("item") or {})
    for key in ("Model", "SourceFile", "File"):
        value = item.get(key)
        if value:
            return str(value).strip().lower()
    return ""


def _enabled_rule(test: ClashTest, key: str) -> Optional[Dict[str, Any]]:
    wanted = str(key or "").strip().lower()
    for rule in list(test.ignore_rules or []):
        if str(rule.key or "").strip().lower() != wanted:
            continue
        if not bool(rule.enabled):
            return None
        return dict(rule.params or {})
    return None


def _split_tokens(values: Any) -> List[str]:
    out: List[str] = []
    if isinstance(values, str):
        candidates = [v.strip() for v in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        candidates = [str(v).strip() for v in values]
    else:
        candidates = []
    for token in candidates:
        normalized = str(token or "").strip().lower()
        if normalized:
            out.append(normalized)
    deduped: List[str] = []
    seen: Set[str] = set()
    for token in out:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _element_name(elem: Optional[Element]) -> str:
    if elem is None:
        return ""
    return str(getattr(elem, "name", "") or "").strip().lower()


def _element_ifc_type(elem: Optional[Element]) -> str:
    if elem is None:
        return ""
    return str(getattr(elem, "type", "") or "").strip().lower()


def should_ignore_pair(
    guid_a: str,
    guid_b: str,
    *,
    test: ClashTest,
    elem_a: Optional[Element],
    elem_b: Optional[Element],
    default_model_ref: str = "",
) -> Tuple[bool, str]:
    if ignore_rule_enabled(test.ignore_rules, IGNORE_SAME_ELEMENT) and str(guid_a) == str(guid_b):
        return True, "same_element"

    if ignore_rule_enabled(test.ignore_rules, IGNORE_SAME_SYSTEM):
        sys_a = _element_system(elem_a)
        sys_b = _element_system(elem_b)
        if sys_a and sys_b and sys_a == sys_b:
            return True, "same_system"

    if ignore_rule_enabled(test.ignore_rules, IGNORE_SAME_FILE):
        model_a = _element_model_ref(elem_a) or str(default_model_ref or "").strip().lower()
        model_b = _element_model_ref(elem_b) or str(default_model_ref or "").strip().lower()
        if model_a and model_b and model_a == model_b:
            return True, "same_file"

    name_rule = _enabled_rule(test, IGNORE_NAME_PATTERN)
    if name_rule is not None:
        patterns = _split_tokens(name_rule.get("patterns"))
        if patterns:
            name_a = _element_name(elem_a)
            name_b = _element_name(elem_b)
            for pattern in patterns:
                if (name_a and pattern in name_a) or (name_b and pattern in name_b):
                    return True, "name_pattern"

    ifc_rule = _enabled_rule(test, IGNORE_IFCTYPE_IN)
    if ifc_rule is not None:
        excluded_types = set(_split_tokens(ifc_rule.get("types")))
        if excluded_types:
            type_a = _element_ifc_type(elem_a)
            type_b = _element_ifc_type(elem_b)
            if (type_a and type_a in excluded_types) or (type_b and type_b in excluded_types):
                return True, "ifc_type_in"

    return False, ""


def build_level_intervals(ifc_repo: Any) -> List[LevelInterval]:
    if ifc_repo is None:
        return []
    model = getattr(ifc_repo, "model", None)
    if model is None or not hasattr(model, "by_type"):
        return []

    length_unit_m = float(getattr(ifc_repo, "length_unit_m", 1.0) or 1.0)
    rows: List[Tuple[float, str]] = []
    try:
        storeys = list(model.by_type("IfcBuildingStorey") or [])
    except Exception:
        storeys = []

    for storey in storeys:
        name = str(getattr(storey, "Name", None) or getattr(storey, "GlobalId", None) or "Storey").strip()
        try:
            elev_raw = getattr(storey, "Elevation", None)
            elev_m = float(elev_raw) * float(length_unit_m) if elev_raw is not None else math.nan
        except Exception:
            elev_m = math.nan
        if math.isfinite(elev_m):
            rows.append((elev_m, name or "Storey"))

    if not rows:
        return []

    rows.sort(key=lambda it: (it[0], it[1]))
    levels: List[LevelInterval] = []
    for idx, (elev_m, level_id) in enumerate(rows):
        prev_mid = -1.0e6
        next_mid = 1.0e6
        if idx > 0:
            prev_mid = (rows[idx - 1][0] + elev_m) * 0.5
        if idx < len(rows) - 1:
            next_mid = (elev_m + rows[idx + 1][0]) * 0.5
        levels.append(LevelInterval(level_id=str(level_id), min_z=float(prev_mid), max_z=float(next_mid)))
    return levels


def _normalize(vec: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
    mag = math.sqrt((x * x) + (y * y) + (z * z))
    if mag <= 1.0e-9:
        return (1.0, 0.0, 0.0)
    return (x / mag, y / mag, z / mag)


def _build_viewpoint(
    result_id: str,
    test_id: str,
    midpoint: Tuple[float, float, float],
    aabb_a: Tuple[float, float, float, float, float, float],
    aabb_b: Tuple[float, float, float, float, float, float],
) -> Viewpoint:
    minx = min(float(aabb_a[0]), float(aabb_b[0]))
    miny = min(float(aabb_a[1]), float(aabb_b[1]))
    minz = min(float(aabb_a[2]), float(aabb_b[2]))
    maxx = max(float(aabb_a[3]), float(aabb_b[3]))
    maxy = max(float(aabb_a[4]), float(aabb_b[4]))
    maxz = max(float(aabb_a[5]), float(aabb_b[5]))
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    radius = max(0.5, math.sqrt((dx * dx) + (dy * dy) + (dz * dz)) * 0.9)

    look_at = (float(midpoint[0]), float(midpoint[1]), float(midpoint[2]))
    view_dir = _normalize((1.0, 1.0, 0.8))
    position = (
        float(look_at[0]) + (view_dir[0] * radius),
        float(look_at[1]) + (view_dir[1] * radius),
        float(look_at[2]) + (view_dir[2] * radius),
    )
    direction = _normalize(
        (
            float(look_at[0]) - float(position[0]),
            float(look_at[1]) - float(position[1]),
            float(look_at[2]) - float(position[2]),
        )
    )
    up = (0.0, 0.0, 1.0)
    return Viewpoint(
        id=f"view:{result_id}",
        test_id=str(test_id),
        result_id=str(result_id),
        camera_position=position,
        camera_direction=direction,
        camera_up=up,
        camera_type="perspective",
        look_at=look_at,
    )


def captureScreenshot(viewpoint: Viewpoint) -> Dict[str, Optional[str]]:
    _ = viewpoint
    return {
        "status": "todo",
        "path": None,
        "note": "TODO: captureScreenshot(viewpoint) not implemented yet.",
    }


def _element_label(elem: Optional[Element], fallback: str) -> str:
    if elem is None:
        return fallback
    name = str(elem.name or "").strip()
    if name:
        return name
    type_name = str(elem.type or "").strip()
    if type_name:
        return type_name
    return fallback


def run_clash_test(
    *,
    test: ClashTest,
    guids_a: Iterable[str],
    guids_b: Iterable[str],
    bounds_map: Dict[str, Bounds],
    elements: Dict[str, Element],
    set_names_a: Optional[Dict[str, List[str]]] = None,
    set_names_b: Optional[Dict[str, List[str]]] = None,
    level_intervals: Optional[Sequence[LevelInterval]] = None,
    model_unit_to_meter: float = 1.0,
    default_model_ref: str = "",
    broadphase_padding_m: float = 0.01,
    broadphase_cell_size_m: float = 2.0,
    eps: float = 1.0e-4,
    now_ts: Optional[float] = None,
    log: Optional[Callable[[str], None]] = None,
    profile: Optional[Dict[str, Any]] = None,
    yield_callback: Optional[Callable[[], None]] = None,
    cache: Optional[ClashRunCache] = None,
) -> ClashRunOutput:
    start_clock = time.perf_counter()
    ids_a = sorted({str(v) for v in list(guids_a or []) if v})
    ids_b = sorted({str(v) for v in list(guids_b or []) if v})
    if not ids_a or not ids_b:
        if isinstance(profile, dict):
            profile.clear()
            profile.update(
                {
                    "timingsMs": {
                        "buildProxies": 0.0,
                        "broadphase": 0.0,
                        "narrowphase": 0.0,
                        "grouping": 0.0,
                        "total": 0.0,
                    },
                    "counts": {
                        "elementsA": len(ids_a),
                        "elementsB": len(ids_b),
                        "proxiesBuilt": 0,
                        "proxiesTotal": 0,
                        "proxyCacheHits": 0,
                        "changedElements": 0,
                        "pairsScanned": 0,
                        "candidates": 0,
                        "confirmedClashes": 0,
                        "candidateCacheHit": 0,
                        "spatialIndexRebuilt": 0,
                        "narrowphaseCacheHits": 0,
                        "clashKeyCacheHits": 0,
                    },
                    "cache": {
                        "proxyCacheHits": 0,
                        "candidateCacheHit": False,
                        "spatialIndexRebuilt": False,
                        "narrowphaseCacheHits": 0,
                        "clashKeyCacheHits": 0,
                        "changedElementsCount": 0,
                    },
                }
            )
        return ClashRunOutput(issues=[], results=[], groups=[], viewpoints=[], skipped_ignored=0)

    threshold_m = max(0.0, float(test.threshold_mm or 0.0) / 1000.0)
    now = float(now_ts if now_ts is not None else time.time())

    cache_obj = cache if isinstance(cache, ClashRunCache) else None
    ids_union = sorted(set(ids_a) | set(ids_b))
    relevant_bounds: Dict[str, Bounds] = {}
    build_proxies_clock = time.perf_counter()
    proxy_builder = ProxyBuilder(default_model_key=str(default_model_ref or ""))
    proxies_by_guid: Dict[str, GeometryProxy] = {}
    current_guid_identity: Dict[str, str] = {}
    current_guid_fingerprint: Dict[str, Tuple[str, str, Tuple[Any, ...]]] = {}
    changed_build_ids: List[str] = []
    proxy_cache_hits = 0
    proxies_rebuilt = 0
    previous_guid_identity = dict(cache_obj.guid_identity_map) if cache_obj is not None else {}
    previous_guid_fingerprint = dict(cache_obj.guid_fingerprint_map) if cache_obj is not None else {}

    for guid in ids_union:
        bound = bounds_map.get(guid)
        if not isinstance(bound, Bounds):
            continue
        elem = elements.get(guid)
        model_key = _model_key_for_cache(elem, default_model_ref=default_model_ref)
        element_key = _element_key_for_cache(guid, elem)
        geom_fingerprint = _element_geometry_fingerprint(bound)
        fingerprint_key = (model_key, element_key, geom_fingerprint)
        current_guid_fingerprint[guid] = fingerprint_key
        identity_key = ""
        if cache_obj is not None and previous_guid_fingerprint.get(guid) == fingerprint_key:
            identity_key = str(previous_guid_identity.get(guid, "") or "")
        if not identity_key:
            geometry_sig = f"geom:{_hash_payload(repr(geom_fingerprint))}"
            identity_key = f"{model_key}|{element_key}|{geometry_sig}"
        current_guid_identity[guid] = identity_key
        if cache_obj is not None:
            cached_proxy = cache_obj.proxy_by_identity.get(identity_key)
            if cached_proxy is not None:
                proxies_by_guid[guid] = cached_proxy
                proxy_cache_hits += 1
                continue
        changed_build_ids.append(guid)

    if changed_build_ids:
        built = proxy_builder.build(
            element_ids=changed_build_ids,
            bounds_map=bounds_map,
            elements=elements,
        )
        for guid, proxy in built.items():
            proxies_by_guid[guid] = proxy
            proxies_rebuilt += 1
            if cache_obj is not None:
                identity_key = current_guid_identity.get(guid)
                if identity_key:
                    cache_obj.proxy_by_identity[identity_key] = proxy

    for guid, proxy in proxies_by_guid.items():
        bound = bounds_map.get(guid)
        if not isinstance(bound, Bounds):
            continue
        # Keep the current clash behavior for now: require renderable geometry.
        if not bool(proxy.hasRenderableGeometry):
            continue
        relevant_bounds[guid] = bound

    if cache_obj is not None:
        cache_obj.guid_identity_map = dict(current_guid_identity)
        cache_obj.guid_fingerprint_map = dict(current_guid_fingerprint)
    changed_elements_count = int(
        len(
            set(g for g in current_guid_identity if previous_guid_identity.get(g) != current_guid_identity[g])
            | (set(previous_guid_identity.keys()) - set(current_guid_identity.keys()))
        )
    )
    build_proxies_ms = (time.perf_counter() - build_proxies_clock) * 1000.0

    set_a = set(ids_a)
    set_b = set(ids_b)
    same_scope = set_a == set_b
    seen: Set[Tuple[str, str]] = set()
    skipped_ignored = 0
    results: List[ClashResult] = []
    viewpoints: List[Viewpoint] = []
    pairs_scanned = 0
    candidates = 0
    narrowphase_seconds = 0.0
    narrowphase_cache_hits = 0
    clash_key_cache_hits = 0

    initial_padding = max(float(broadphase_padding_m), threshold_m if test.clash_type == ClashType.CLEARANCE else 0.01)
    broadphase_clock = time.perf_counter()
    proxies_a = [proxies_by_guid[guid] for guid in ids_a if guid in proxies_by_guid and guid in relevant_bounds]
    proxies_b = [proxies_by_guid[guid] for guid in ids_b if guid in proxies_by_guid and guid in relevant_bounds]
    left_tokens = [f"{guid}:{current_guid_identity.get(guid, '')}" for guid in ids_a if guid in relevant_bounds]
    right_tokens = [f"{guid}:{current_guid_identity.get(guid, '')}" for guid in ids_b if guid in relevant_bounds]
    candidate_cache_key = _hash_payload(
        "broadphase|"
        f"cell={float(broadphase_cell_size_m or 2.0):.4f}|"
        f"pad={float(initial_padding):.6f}|"
        f"same={1 if same_scope else 0}|"
        f"A={'|'.join(left_tokens)}|B={'|'.join(right_tokens)}"
    )
    candidate_pairs: List[CandidatePair] = []
    broadphase_cache_hit = False
    spatial_index_rebuilt = True
    if cache_obj is not None:
        raw_pairs = cache_obj.candidate_pairs_cache.get(candidate_cache_key)
        if raw_pairs is not None:
            broadphase_cache_hit = True
            spatial_index_rebuilt = False
            for guid_a, guid_b, a_key, b_key in list(raw_pairs or []):
                proxy_a = proxies_by_guid.get(str(guid_a))
                proxy_b = proxies_by_guid.get(str(guid_b))
                if proxy_a is None or proxy_b is None:
                    continue
                candidate_pairs.append(
                    CandidatePair(
                        aKey=str(a_key or proxy_a.elementKey or guid_a),
                        bKey=str(b_key or proxy_b.elementKey or guid_b),
                        aProxy=proxy_a,
                        bProxy=proxy_b,
                    )
                )
    if not candidate_pairs:
        candidate_pairs = broadphase(
            proxies_a,
            proxies_b,
            cell_size_m=float(broadphase_cell_size_m or 2.0),
            padding_m=float(initial_padding),
            same_set=bool(same_scope),
            batch_size=512,
            on_batch=(lambda _i, _n: yield_callback()) if callable(yield_callback) else None,
        )
        if cache_obj is not None:
            raw_pairs: List[Tuple[str, str, str, str]] = []
            for pair in candidate_pairs:
                raw_pairs.append(
                    (
                        str(pair.aProxy.elementId or ""),
                        str(pair.bProxy.elementId or ""),
                        str(pair.aKey or ""),
                        str(pair.bKey or ""),
                    )
                )
            _cache_set_limited(
                cache_obj.candidate_pairs_cache,
                candidate_cache_key,
                raw_pairs,
                max_entries=int(cache_obj.max_candidate_cache_entries),
            )
    for pair in candidate_pairs:
        pairs_scanned += 1
        guid_a = str(pair.aProxy.elementId or "")
        guid_b = str(pair.bProxy.elementId or "")
        if not guid_a or not guid_b:
            continue

        pair_key = tuple(sorted((guid_a, guid_b)))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        elem_a = elements.get(guid_a)
        elem_b = elements.get(guid_b)
        ignore_hit, ignore_reason = should_ignore_pair(
            guid_a,
            guid_b,
            test=test,
            elem_a=elem_a,
            elem_b=elem_b,
            default_model_ref=default_model_ref,
        )
        if ignore_hit:
            skipped_ignored += 1
            continue

        bound_a = relevant_bounds.get(guid_a)
        bound_b = relevant_bounds.get(guid_b)
        if bound_a is None or bound_b is None:
            continue

        candidates += 1
        id_sig_a = current_guid_identity.get(guid_a, "")
        id_sig_b = current_guid_identity.get(guid_b, "")
        narrow_cache_key = _hash_payload(
            "narrowphase|"
            f"a={id_sig_a}|b={id_sig_b}|"
            f"type={test.clash_type.value}|"
            f"threshold={float(threshold_m):.6f}|"
            f"eps={float(eps):.6f}"
        )
        narrow_cached = cache_obj.narrowphase_cache.get(narrow_cache_key) if cache_obj is not None else None
        if narrow_cached:
            narrowphase_cache_hits += 1
            min_distance = float(narrow_cached.get("minDistance") or 0.0)
            overlap_depth = float(narrow_cached.get("overlapDepth") or 0.0)
            point = tuple(narrow_cached.get("point") or ()) or None
            point_a = tuple(narrow_cached.get("pointA") or ()) or None
            point_b = tuple(narrow_cached.get("pointB") or ()) or None
            method = str(narrow_cached.get("method") or "aabb")
            is_clash = bool(narrow_cached.get("isClash"))
            midpoint = tuple(narrow_cached.get("midpoint") or ()) or None
        else:
            narrow_clock = time.perf_counter()
            narrow = run_narrowphase_v1(bound_a.aabbWorld, bound_b.aabbWorld)
            narrowphase_seconds += max(0.0, time.perf_counter() - narrow_clock)
            min_distance = float(narrow.minDistance)
            overlap_depth = float(narrow.overlapDepth)
            point = tuple(float(v) for v in narrow.point) if narrow.point else None
            point_a = tuple(float(v) for v in narrow.pointA) if narrow.pointA else None
            point_b = tuple(float(v) for v in narrow.pointB) if narrow.pointB else None
            method = str(narrow.method)
            is_clash = clash_verdict_v1(
                min_distance_m=min_distance,
                overlap_depth_m=overlap_depth,
                clash_type=test.clash_type,
                threshold_m=threshold_m,
                eps=float(eps),
            )
            midpoint = _midpoint(point_a, point_b)
            if midpoint is None:
                midpoint = _fallback_midpoint(bound_a.aabbWorld, bound_b.aabbWorld)
            if cache_obj is not None:
                _cache_set_limited(
                    cache_obj.narrowphase_cache,
                    narrow_cache_key,
                    {
                        "minDistance": min_distance,
                        "overlapDepth": overlap_depth,
                        "point": point,
                        "pointA": point_a,
                        "pointB": point_b,
                        "method": method,
                        "isClash": bool(is_clash),
                        "midpoint": midpoint,
                    },
                    max_entries=int(cache_obj.max_narrowphase_cache_entries),
                )
        if not is_clash:
            continue

        if midpoint is None:
            midpoint = _fallback_midpoint(bound_a.aabbWorld, bound_b.aabbWorld)

        if cache_obj is not None:
            clash_key_cached = cache_obj.clash_key_cache.get(narrow_cache_key)
        else:
            clash_key_cached = None
        if clash_key_cached:
            clash_key_cache_hits += 1
            clash_key = str(clash_key_cached)
            elem_sig_a = _element_signature(pair.aProxy, quant_step_m=0.01)
            elem_sig_b = _element_signature(pair.bProxy, quant_step_m=0.01)
            centroid_q = _quantized_point(midpoint, 0.01)
        else:
            clash_key, elem_sig_a, elem_sig_b, centroid_q = _clash_key(
                proxy_a=pair.aProxy,
                proxy_b=pair.bProxy,
                clash_type=test.clash_type,
                centroid=midpoint,
                quant_step_m=0.01,
            )
            if cache_obj is not None:
                _cache_set_limited(
                    cache_obj.clash_key_cache,
                    narrow_cache_key,
                    str(clash_key),
                    max_entries=int(cache_obj.max_clash_key_cache_entries),
                )
        result_id = str(clash_key)
        elementA_key = str(pair.aKey or guid_a or guid_b or "")
        proximity_cell = midpoint_proximity_cell(midpoint, float(test.proximity_meters or 6.0))
        level_id = level_for_point_z(midpoint[2] if midpoint else None, list(level_intervals or []))

        clash_result = ClashResult(
            id=result_id,
            clash_key=str(clash_key),
            test_id=str(test.id),
            elementA_id=str(guid_a),
            elementB_id=str(guid_b),
            elementA_guid=str(guid_a),
            elementB_guid=str(guid_b),
            rule_triggered=f"{test.clash_type.value}:{test.id}",
            min_distance_m=float(min_distance),
            penetration_depth_m=float(overlap_depth),
            method=str(method),
            timestamp=float(now),
            level_id=str(level_id),
            proximity_cell=str(proximity_cell),
            elementA_key=str(elementA_key),
            status=ClashResultStatus.NEW,
            tags=[],
            clash_midpoint=midpoint,
            first_seen_at=float(now),
            last_seen_at=float(now),
            diagnostics={
                "ignoreReason": ignore_reason,
                "identity": {
                    "clashKey": str(clash_key),
                    "elementSignatureA": str(elem_sig_a),
                    "elementSignatureB": str(elem_sig_b),
                    "centroidQ": tuple(float(v) for v in centroid_q),
                    "quantStepM": 0.01,
                },
                "narrowphase": {
                    "method": str(method),
                    "minDistance": float(min_distance),
                    "overlapDepth": float(overlap_depth),
                    "point": tuple(float(v) for v in point) if point else None,
                    "pointA": tuple(float(v) for v in point_a) if point_a else None,
                    "pointB": tuple(float(v) for v in point_b) if point_b else None,
                    "details": {},
                },
                "clash": {
                    "key": str(clash_key),
                    "aKey": str(pair.aKey or guid_a),
                    "bKey": str(pair.bKey or guid_b),
                    "type": str(test.clash_type.value),
                    "minDistance": float(min_distance),
                    "overlapDepth": float(overlap_depth),
                    "point": tuple(float(v) for v in point) if point else None,
                    "method": "aabb",
                },
                "clashType": str(test.clash_type.value),
                "thresholdM": float(threshold_m),
                "eps": float(eps),
            },
        )
        results.append(clash_result)

        if test.auto_viewpoint:
            vp = _build_viewpoint(
                result_id=result_id,
                test_id=test.id,
                midpoint=midpoint,
                aabb_a=bound_a.aabbWorld,
                aabb_b=bound_b.aabbWorld,
            )
            if test.auto_screenshot:
                snap = captureScreenshot(vp)
                vp.screenshot_status = str(snap.get("status") or "todo")
                vp.screenshot_path = snap.get("path")
                if log and vp.screenshot_status == "todo":
                    log("TODO: captureScreenshot(viewpoint) is stubbed; viewpoint stored without image.")
            viewpoints.append(vp)
        if callable(yield_callback) and (pairs_scanned % 1000 == 0):
            try:
                yield_callback()
            except Exception:
                pass
    broadphase_total_seconds = max(0.0, time.perf_counter() - broadphase_clock)
    broadphase_seconds = max(0.0, broadphase_total_seconds - narrowphase_seconds)

    if not level_intervals and "level" in [str(v).lower() for v in list(test.grouping_order or [])] and log:
        log("TODO: Level grouping fallback to UnknownLevel; import/store IfcBuildingStorey elevation ranges.")

    element_labels: Dict[str, str] = {}
    for guid in set(ids_a) | set(ids_b):
        elem = elements.get(guid)
        element_labels[str(guid)] = _element_label(elem, str(guid)[:8])

    grouping_clock = time.perf_counter()
    groups = build_clash_groups(
        results,
        test_id=test.id,
        grouping_order=test.grouping_order,
        element_labels=element_labels,
    )
    grouping_ms = (time.perf_counter() - grouping_clock) * 1000.0
    group_lookup = {group.id: group for group in groups}
    viewpoint_lookup = {vp.result_id: vp for vp in viewpoints}

    issues: List[Issue] = []
    unit_scale = max(float(model_unit_to_meter or 1.0), 1.0e-9)
    for result in results:
        if test.clash_type == ClashType.CLEARANCE:
            required_clearance_m = threshold_m
        else:
            required_clearance_m = 0.0
        clearance_margin_m = float(result.min_distance_m) - float(required_clearance_m)

        issue = Issue(
            guid_a=str(result.elementA_id),
            guid_b=str(result.elementB_id),
            rule_id=str(test.id),
            severity="High",
            clearance=float(clearance_margin_m / unit_scale),
            p_a=tuple(result.diagnostics.get("narrowphase", {}).get("pointA") or ()) or None,
            p_b=tuple(result.diagnostics.get("narrowphase", {}).get("pointB") or ()) or None,
            clash_center=result.clash_midpoint,
            issue_id=str(result.clash_key or result.id),
            title=str(result.clash_name or ""),
            group_id=result.group_id,
            search_set_names_a=list((set_names_a or {}).get(result.elementA_id, [])),
            search_set_names_b=list((set_names_b or {}).get(result.elementB_id, [])),
        )
        issue.min_distance_world = float(result.min_distance_m)
        issue.required_clearance_world = float(required_clearance_m)
        issue.detection_method = str(result.method)

        vp = viewpoint_lookup.get(result.id)
        if vp is not None:
            issue.viewpoint = {
                "camera": {
                    "position": tuple(float(v) for v in vp.camera_position),
                    "direction": tuple(float(v) for v in vp.camera_direction),
                    "up": tuple(float(v) for v in vp.camera_up),
                    "type": str(vp.camera_type),
                    "scale": float(vp.camera_scale) if vp.camera_scale is not None else None,
                },
                "lookAt": tuple(float(v) for v in vp.look_at) if vp.look_at else None,
                "result_id": result.id,
                "view_id": vp.id,
                "screenshot": {
                    "status": vp.screenshot_status,
                    "path": vp.screenshot_path,
                },
            }

        group = group_lookup.get(str(result.group_id)) if result.group_id else None
        issue.clash_diagnostics = {
            "test": {
                "id": test.id,
                "name": test.name,
                "clashType": test.clash_type.value,
                "thresholdMm": float(test.threshold_mm),
            },
            "result": {
                "id": result.id,
                "clashKey": str(result.clash_key or result.id),
                "kind": "clash",
                "status": result.status.value,
                "reopened": bool(result.reopened),
                "reopenCount": int(result.reopen_count or 0),
                "firstSeenAt": float(result.first_seen_at) if result.first_seen_at is not None else None,
                "lastSeenAt": float(result.last_seen_at) if result.last_seen_at is not None else None,
                "assignee": result.assignee,
                "tags": list(result.tags or []),
                "method": result.method,
                "minDistance": float(result.min_distance_m),
                "penetrationDepth": float(result.penetration_depth_m),
            },
            "group": {
                "id": result.group_id,
                "name": result.group_name,
                "elementAKey": result.elementA_key,
                "proximityCell": result.proximity_cell,
                "levelId": result.level_id,
                "size": len(group.result_ids) if group else 1,
            },
            "view": {
                "viewId": vp.id if vp else None,
                "screenshotStatus": vp.screenshot_status if vp else None,
                "screenshotPath": vp.screenshot_path if vp else None,
            },
            "narrowphase": dict(result.diagnostics.get("narrowphase") or {}),
            "verdict": "CLASH",
        }
        issues.append(issue)

    issues.sort(key=lambda i: (str(i.group_id or ""), str(i.guid_a or ""), str(i.guid_b or "")))
    total_ms = (time.perf_counter() - start_clock) * 1000.0
    if isinstance(profile, dict):
        profile.clear()
        profile.update(
            {
                "timingsMs": {
                    "buildProxies": float(build_proxies_ms),
                    "broadphase": float(broadphase_seconds * 1000.0),
                    "narrowphase": float(narrowphase_seconds * 1000.0),
                    "grouping": float(grouping_ms),
                    "total": float(total_ms),
                },
                "counts": {
                    "elementsA": int(len(ids_a)),
                    "elementsB": int(len(ids_b)),
                    "proxiesBuilt": int(proxies_rebuilt),
                    "proxiesTotal": int(len(proxies_by_guid)),
                    "proxyCacheHits": int(proxy_cache_hits),
                    "changedElements": int(changed_elements_count),
                    "pairsScanned": int(pairs_scanned),
                    "candidates": int(candidates),
                    "confirmedClashes": int(len(results)),
                    "candidateCacheHit": 1 if broadphase_cache_hit else 0,
                    "spatialIndexRebuilt": 1 if spatial_index_rebuilt else 0,
                    "narrowphaseCacheHits": int(narrowphase_cache_hits),
                    "clashKeyCacheHits": int(clash_key_cache_hits),
                },
                "cache": {
                    "proxyCacheHits": int(proxy_cache_hits),
                    "candidateCacheHit": bool(broadphase_cache_hit),
                    "spatialIndexRebuilt": bool(spatial_index_rebuilt),
                    "narrowphaseCacheHits": int(narrowphase_cache_hits),
                    "clashKeyCacheHits": int(clash_key_cache_hits),
                    "changedElementsCount": int(changed_elements_count),
                },
            }
        )
    return ClashRunOutput(
        issues=issues,
        results=results,
        groups=groups,
        viewpoints=viewpoints,
        skipped_ignored=int(skipped_ignored),
    )
