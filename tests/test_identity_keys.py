from identity_keys import getElementKey, getModelKey
from models import Element


class _Repo:
    def __init__(self, path: str, elements):
        self.path = path
        self.elements = elements


def _element(guid: str, name: str = "") -> Element:
    return Element(
        guid=guid,
        type="IfcPipeSegment",
        discipline="Plumbing",
        geom_ref=guid,
        name=name or guid,
    )


def test_get_model_key_is_content_based_not_path_based():
    elements_a = {
        "A": _element("A"),
        "B": _element("B"),
        "C": _element("C"),
    }
    # Same content, different file names and dict order.
    elements_b = {
        "C": _element("C"),
        "A": _element("A"),
        "B": _element("B"),
    }
    repo_a = _Repo("/tmp/original.ifc", elements_a)
    repo_b = _Repo("/tmp/renamed.ifc", elements_b)

    assert getModelKey(repo_a) == getModelKey(repo_b)


def test_get_element_key_prefers_global_id():
    elem = _element("3hG8NzV5j8Cfx")
    assert getElementKey(elem) == "3hG8NzV5j8Cfx"


def test_get_element_key_fallback_is_stable_when_geometry_is_same():
    # No GlobalId/guid -> fallback hashing path.
    element_a = {
        "ifcType": "IfcCableSegment",
        "name": "  Main cable  ",
        "aabbWorld": (10.0, 5.0, 2.0, 12.0, 7.0, 4.0),
    }
    element_b = {
        "ifcType": "IfcCableSegment",
        "name": "Main cable",
        "aabbWorld": (10.0, 5.0, 2.0, 12.0, 7.0, 4.0),
    }

    assert getElementKey(element_a) == getElementKey(element_b)


def test_get_element_key_fallback_changes_when_geometry_changes():
    element_a = {
        "ifcType": "IfcCableSegment",
        "name": "Main cable",
        "aabbWorld": (10.0, 5.0, 2.0, 12.0, 7.0, 4.0),
    }
    element_b = {
        "ifcType": "IfcCableSegment",
        "name": "Main cable",
        "aabbWorld": (10.0, 5.0, 2.0, 12.4, 7.0, 4.0),
    }

    assert getElementKey(element_a) != getElementKey(element_b)
