from clash_detection import Bounds
from clash_tests.engine import run_clash_test, should_ignore_pair
from clash_tests.grouping import build_clash_groups, midpoint_proximity_cell
from clash_tests.models import (
    ClashResult,
    ClashResultStatus,
    ClashTest,
    ClashType,
    GROUP_ELEMENT_A,
    GROUP_LEVEL,
    GROUP_PROXIMITY,
    IGNORE_IFCTYPE_IN,
    IGNORE_NAME_PATTERN,
    IGNORE_SAME_ELEMENT,
    IGNORE_SAME_FILE,
    IGNORE_SAME_SYSTEM,
    IgnoreRule,
)
from models import Element


def _element(guid: str) -> Element:
    return Element(guid=guid, type="IfcPipeSegment", discipline="Plumbing", geom_ref=guid)


def _bounds(guid: str, aabb):
    return Bounds(
        elementId=guid,
        aabbWorld=tuple(aabb),
        hasRenderableGeometry=True,
        meshVertexCount=24,
        meshCount=1,
    )


def test_clearance_logic_respects_threshold_mm():
    test = ClashTest(
        id="t-clearance",
        name="Clearance test",
        clash_type=ClashType.CLEARANCE,
        threshold_mm=100.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A, GROUP_PROXIMITY],
        proximity_meters=6.0,
    )
    bounds = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),
        "B": _bounds("B", (1.08, 0.0, 0.0, 2.08, 1.0, 1.0)),
    }
    elements = {"A": _element("A"), "B": _element("B")}

    output = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(output.results) == 1

    test.threshold_mm = 50.0
    output_no_clash = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(output_no_clash.results) == 0


def test_proximity_grouping_splits_cells():
    r1 = ClashResult(
        id="r1",
        test_id="t",
        elementA_id="A",
        elementB_id="B",
        elementA_guid="A",
        elementB_guid="B",
        rule_triggered="hard:t",
        min_distance_m=-0.01,
        penetration_depth_m=0.01,
        method="broadphase+aabb",
        timestamp=1.0,
        level_id="L1",
        proximity_cell=midpoint_proximity_cell((1.0, 1.0, 1.0), 6.0),
        elementA_key="A",
        status=ClashResultStatus.NEW,
    )
    r2 = ClashResult(
        id="r2",
        test_id="t",
        elementA_id="A",
        elementB_id="C",
        elementA_guid="A",
        elementB_guid="C",
        rule_triggered="hard:t",
        min_distance_m=-0.02,
        penetration_depth_m=0.02,
        method="broadphase+aabb",
        timestamp=1.0,
        level_id="L1",
        proximity_cell=midpoint_proximity_cell((7.0, 1.0, 1.0), 6.0),
        elementA_key="A",
        status=ClashResultStatus.NEW,
    )

    groups = build_clash_groups(
        [r1, r2],
        test_id="t",
        grouping_order=[GROUP_ELEMENT_A, GROUP_PROXIMITY, GROUP_LEVEL],
        element_labels={"A": "Main Pipe", "B": "Cable Tray", "C": "Vent Duct"},
    )
    assert len(groups) == 2
    assert groups[0].id != groups[1].id


def test_ignore_same_element_rule():
    test = ClashTest(
        id="t-ignore",
        name="Ignore same",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A],
    )
    hit, reason = should_ignore_pair(
        "A",
        "A",
        test=test,
        elem_a=_element("A"),
        elem_b=_element("A"),
    )
    assert hit is True
    assert reason == "same_element"


def test_hard_clash_uses_aabb_overlap_and_reports_aabb_method():
    test = ClashTest(
        id="t-hard-aabb",
        name="Hard AABB",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A],
    )
    bounds = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),
        "B": _bounds("B", (0.8, 0.0, 0.0, 1.8, 1.0, 1.0)),
    }
    elements = {"A": _element("A"), "B": _element("B")}
    output = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(output.results) == 1
    result = output.results[0]
    assert result.method == "aabb"
    assert result.penetration_depth_m > 0.0
    clash_payload = dict(result.diagnostics.get("clash") or {})
    assert clash_payload.get("method") == "aabb"
    assert clash_payload.get("type") == "hard"
    assert float(clash_payload.get("overlapDepth") or 0.0) > 0.0


def test_tolerance_clash_uses_overlap_depth_threshold():
    test = ClashTest(
        id="t-tolerance-aabb",
        name="Tolerance AABB",
        clash_type=ClashType.TOLERANCE,
        threshold_mm=250.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A],
    )
    bounds = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),
        "B": _bounds("B", (0.8, 0.0, 0.0, 1.8, 1.0, 1.0)),
    }
    elements = {"A": _element("A"), "B": _element("B")}
    no_hit = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(no_hit.results) == 0

    test.threshold_mm = 50.0
    hit = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(hit.results) == 1


def test_ignore_same_system_supports_ponker_classification_fallback():
    test = ClashTest(
        id="t-ignore-system",
        name="Ignore same system",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_SYSTEM, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A],
    )
    elem_a = _element("A")
    elem_b = _element("B")
    elem_a.class_name = "DCW"
    elem_b.class_name = "dcw"
    hit, reason = should_ignore_pair(
        "A",
        "B",
        test=test,
        elem_a=elem_a,
        elem_b=elem_b,
    )
    assert hit is True
    assert reason == "same_system"


def test_ignore_same_file_uses_model_key():
    test = ClashTest(
        id="t-ignore-file",
        name="Ignore same file",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_SAME_FILE, enabled=True)],
        grouping_order=[GROUP_ELEMENT_A],
    )
    elem_a = _element("A")
    elem_b = _element("B")
    elem_a.ifc_meta = {"modelKey": "model:abc"}
    elem_b.ifc_meta = {"modelKey": "model:abc"}
    hit, reason = should_ignore_pair(
        "A",
        "B",
        test=test,
        elem_a=elem_a,
        elem_b=elem_b,
    )
    assert hit is True
    assert reason == "same_file"


def test_ignore_name_pattern_and_ifctype_filters():
    elem_a = _element("A")
    elem_b = _element("B")
    elem_a.name = "temp route pipe"
    elem_b.type = "IfcWall"

    name_filter_test = ClashTest(
        id="t-ignore-name",
        name="Ignore name patterns",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_NAME_PATTERN, enabled=True, params={"patterns": ["temp", "demo"]})],
        grouping_order=[GROUP_ELEMENT_A],
    )
    hit_name, reason_name = should_ignore_pair(
        "A",
        "B",
        test=name_filter_test,
        elem_a=elem_a,
        elem_b=elem_b,
    )
    assert hit_name is True
    assert reason_name == "name_pattern"

    type_filter_test = ClashTest(
        id="t-ignore-type",
        name="Ignore ifcType list",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_IFCTYPE_IN, enabled=True, params={"types": ["IfcWall", "IfcSpace"]})],
        grouping_order=[GROUP_ELEMENT_A],
    )
    hit_type, reason_type = should_ignore_pair(
        "A",
        "B",
        test=type_filter_test,
        elem_a=elem_a,
        elem_b=elem_b,
    )
    assert hit_type is True
    assert reason_type == "ifc_type_in"


def test_toggling_ignore_rules_changes_clash_count():
    bounds = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),
        "B": _bounds("B", (0.8, 0.0, 0.0, 1.8, 1.0, 1.0)),
    }
    elem_a = _element("A")
    elem_b = _element("B")
    elem_a.name = "temp route pipe"
    elements = {"A": elem_a, "B": elem_b}

    base = ClashTest(
        id="t-count-base",
        name="Base",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[],
        grouping_order=[GROUP_ELEMENT_A],
    )
    base_out = run_clash_test(
        test=base,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(base_out.results) == 1

    filtered = ClashTest(
        id="t-count-filtered",
        name="Filtered",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=[IgnoreRule(key=IGNORE_NAME_PATTERN, enabled=True, params={"patterns": ["temp"]})],
        grouping_order=[GROUP_ELEMENT_A],
    )
    filtered_out = run_clash_test(
        test=filtered,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
    )
    assert len(filtered_out.results) == 0
