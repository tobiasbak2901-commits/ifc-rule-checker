from clash_detection import Bounds
from clash_tests.proxy_builder import ProxyBuilder, build_proxies_for_model
from models import Element


def _element(guid: str, ifc_type: str, *, model_key: str = "model:test") -> Element:
    return Element(
        guid=guid,
        type=ifc_type,
        discipline="MEP",
        geom_ref=guid,
        name=f"{ifc_type} {guid}",
        ifc_meta={"modelKey": model_key},
    )


def _bounds(
    guid: str,
    aabb,
    *,
    centerline=None,
    radius=None,
    renderable=True,
) -> Bounds:
    return Bounds(
        elementId=guid,
        aabbWorld=tuple(aabb),
        centerlineWorld=centerline,
        radiusWorld=radius,
        hasRenderableGeometry=bool(renderable),
        meshVertexCount=24 if renderable else 0,
        meshCount=1 if renderable else 0,
    )


def test_proxy_builder_pipe_with_axis_and_radius():
    elements = {"P1": _element("P1", "IfcPipeSegment")}
    bounds_map = {
        "P1": _bounds(
            "P1",
            (0.0, 0.0, 0.0, 10.0, 2.0, 2.0),
            centerline=((0.0, 1.0, 1.0), (10.0, 1.0, 1.0)),
            radius=0.5,
        )
    }
    proxies = ProxyBuilder().build(element_ids=["P1"], bounds_map=bounds_map, elements=elements)
    proxy = proxies["P1"]
    assert proxy.kind == "pipe"
    assert proxy.axis is not None
    assert proxy.radius is not None
    assert proxy.rect is None
    assert proxy.modelKey == "model:test"
    as_dict = proxy.to_dict()
    assert "axis" in as_dict
    assert "radius" in as_dict


def test_proxy_builder_duct_gets_rect():
    elements = {"D1": _element("D1", "IfcDuctSegment")}
    bounds_map = {
        "D1": _bounds(
            "D1",
            (0.0, 0.0, 0.0, 8.0, 1.2, 0.6),
            centerline=((0.0, 0.6, 0.3), (8.0, 0.6, 0.3)),
        )
    }
    proxies = ProxyBuilder().build(element_ids=["D1"], bounds_map=bounds_map, elements=elements)
    proxy = proxies["D1"]
    assert proxy.kind == "duct"
    assert proxy.rect is not None
    assert proxy.rect.w > 0.0
    assert proxy.rect.h > 0.0


def test_proxy_builder_generic_is_aabb_only():
    elements = {"G1": _element("G1", "IfcWall")}
    bounds_map = {"G1": _bounds("G1", (1.0, 2.0, 3.0, 5.0, 7.0, 9.0))}
    proxies = ProxyBuilder().build(element_ids=["G1"], bounds_map=bounds_map, elements=elements)
    proxy = proxies["G1"]
    assert proxy.kind == "generic"
    assert proxy.axis is None
    assert proxy.radius is None
    assert proxy.rect is None


def test_build_proxies_for_model_returns_list():
    elements = {
        "A": _element("A", "IfcPipeSegment"),
        "B": _element("B", "IfcCableCarrierSegment"),
    }
    bounds_map = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 4.0, 1.0, 1.0)),
        "B": _bounds("B", (5.0, 0.0, 0.0, 8.0, 0.8, 0.4)),
    }
    proxies = build_proxies_for_model(elements=elements, bounds_map=bounds_map, model_key="model:demo")
    assert len(proxies) == 2
    assert all(bool(p.modelKey) for p in proxies)
