from models import Element
from search_sets import evaluate_query


def _element(**overrides):
    base = Element(
        guid="g1",
        type="IfcFlowSegment",
        discipline="Plumbing",
        geom_ref="g1",
        name="Drain Pipe",
        system="Sanitary",
        psets={},
        type_psets={},
        ifc_meta={"item": {"PredefinedType": "PIPESEGMENT"}},
        class_name="Drainage",
        utility_type="drainage",
        layers=["MEP-DRAIN"],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_search_set_query_matches_predefined_pipe_segment():
    elem = _element()
    query = [
        {
            "ifcTypeIn": ["IfcFlowSegment"],
            "psetEquals": {
                "pset": "item",
                "prop": "PredefinedType",
                "value": "PIPESEGMENT",
                "ifAvailable": True,
            },
        },
        {"nameContainsAny": ["drain"]},
    ]
    ok, details = evaluate_query(elem, query, diameter_mm=110.0)
    assert ok is True
    assert len(details) == 2


def test_search_set_pset_equals_if_available_does_not_fail_when_missing():
    elem = _element(ifc_meta={"item": {}}, type="IfcPipeSegment")
    query = [
        {
            "ifcTypeIn": ["IfcPipeSegment", "IfcFlowSegment"],
            "psetEquals": {
                "pset": "item",
                "prop": "PredefinedType",
                "value": "PIPESEGMENT",
                "ifAvailable": True,
            },
        }
    ]
    ok, _ = evaluate_query(elem, query, diameter_mm=90.0)
    assert ok is True


def test_search_set_query_supports_invert_min_max_classification_and_layer():
    elem = _element()
    query_ok = [
        {"minDiameter": 100.0, "maxDiameter": 150.0},
        {"classificationContainsAny": ["drain"]},
        {"layerContainsAny": ["mep"]},
    ]
    ok, _ = evaluate_query(elem, query_ok, diameter_mm=120.0)
    assert ok is True

    query_fail = [{"nameContainsAny": ["drain"], "invert": True}]
    ok_inverted, _ = evaluate_query(elem, query_fail, diameter_mm=120.0)
    assert ok_inverted is False
