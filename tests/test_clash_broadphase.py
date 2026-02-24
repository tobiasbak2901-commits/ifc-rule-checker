from clash_detection import Bounds
from clash_tests.broadphase import broadphase
from clash_tests.proxy_builder import ProxyBuilder
from models import Element


def _element(guid: str, ifc_type: str = "IfcPipeSegment") -> Element:
    return Element(
        guid=guid,
        type=ifc_type,
        discipline="MEP",
        geom_ref=guid,
        name=guid,
        ifc_meta={"modelKey": "model:test"},
    )


def _bound(guid: str, x: float, y: float = 0.0, z: float = 0.0, size: float = 0.8) -> Bounds:
    return Bounds(
        elementId=guid,
        aabbWorld=(x, y, z, x + size, y + size, z + size),
        hasRenderableGeometry=True,
        meshVertexCount=24,
        meshCount=1,
    )


def _proxies(ids, bounds_map, elements):
    return list(ProxyBuilder(default_model_key="model:test").build(element_ids=ids, bounds_map=bounds_map, elements=elements).values())


def test_broadphase_returns_candidate_pair_with_proxy_refs():
    elements = {"A0": _element("A0"), "B0": _element("B0")}
    bounds = {
        "A0": _bound("A0", 0.0),
        "B0": _bound("B0", 0.2),
    }
    proxies_a = _proxies(["A0"], bounds, elements)
    proxies_b = _proxies(["B0"], bounds, elements)
    pairs = broadphase(proxies_a, proxies_b, cell_size_m=2.0)
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.aKey
    assert pair.bKey
    assert pair.aProxy.elementId == "A0"
    assert pair.bProxy.elementId == "B0"


def test_broadphase_candidates_are_much_less_than_cartesian_product():
    n = 200
    elements = {}
    bounds = {}
    ids_a = []
    ids_b = []
    for i in range(n):
        aid = f"A{i:03d}"
        bid = f"B{i:03d}"
        elements[aid] = _element(aid)
        elements[bid] = _element(bid)
        # Spread items so each A mostly only matches one B.
        x = float(i) * 3.0
        bounds[aid] = _bound(aid, x=x, size=0.8)
        bounds[bid] = _bound(bid, x=x + 0.2, size=0.8)
        ids_a.append(aid)
        ids_b.append(bid)

    proxies_a = _proxies(ids_a, bounds, elements)
    proxies_b = _proxies(ids_b, bounds, elements)
    pairs = broadphase(proxies_a, proxies_b, cell_size_m=2.0)
    brute_force = len(proxies_a) * len(proxies_b)
    assert len(pairs) < brute_force
    assert len(pairs) < (len(proxies_a) * 5)


def test_broadphase_same_set_has_no_self_pairs_or_duplicates():
    elements = {"A0": _element("A0"), "A1": _element("A1"), "A2": _element("A2")}
    bounds = {
        "A0": _bound("A0", 0.0),
        "A1": _bound("A1", 0.2),
        "A2": _bound("A2", 3.0),
    }
    proxies = _proxies(["A0", "A1", "A2"], bounds, elements)
    pairs = broadphase(proxies, proxies, cell_size_m=2.0, same_set=True)
    seen = set()
    for pair in pairs:
        assert pair.aProxy.elementId != pair.bProxy.elementId
        key = tuple(sorted((pair.aProxy.elementId, pair.bProxy.elementId)))
        assert key not in seen
        seen.add(key)
