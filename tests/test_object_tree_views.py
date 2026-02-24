from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Element, Issue
from ui.panels.object_tree_views import build_ai_view_nodes, friendly_item_type_label


def _elem(guid: str, ifc_type: str, *, system: str = "", discipline: str = "MEP") -> Element:
    systems = [system] if system else []
    return Element(
        guid=guid,
        type=ifc_type,
        discipline=discipline,
        geom_ref=guid,
        name=guid,
        system=system or None,
        systems=systems,
        system_group_names=systems,
        ifc_meta={"system_groups": systems} if systems else {},
    )


def _issue(guid_a: str, guid_b: str, *, issue_id: str) -> Issue:
    return Issue(
        guid_a=guid_a,
        guid_b=guid_b,
        rule_id="SEARCH_SET_CLASH",
        severity="high",
        clearance=0.0,
        p_a=None,
        p_b=None,
        issue_id=issue_id,
    )


def test_friendly_item_type_alias_mapping():
    assert friendly_item_type_label("IfcPipeSegment") == "Pipes"
    assert friendly_item_type_label("IfcFlowSegment") == "MEP Segments"
    assert friendly_item_type_label("IfcSlab") == "Slabs"
    assert friendly_item_type_label("IfcDoor") == "IfcDoor"


def test_high_risk_systems_sorted_by_clash_count_desc():
    elements = {
        "A": _elem("A", "IfcPipeSegment", system="Domestic Water", discipline="Plumbing"),
        "B": _elem("B", "IfcPipeSegment", system="Domestic Water", discipline="Plumbing"),
        "C": _elem("C", "IfcDuctSegment", system="Ventilation", discipline="HVAC"),
    }
    issues = [
        _issue("A", "B", issue_id="1"),
        _issue("A", "C", issue_id="2"),
        _issue("B", "C", issue_id="3"),
    ]

    nodes = build_ai_view_nodes(
        elements,
        issues,
        active_test_name="Active test",
        class_labels={"A": "Pipe", "B": "Pipe", "C": "Duct"},
        include_recent=False,
    )
    high_risk = next(node for node in nodes if node.id == "ai:high-risk")

    assert len(high_risk.children) >= 2
    assert high_risk.children[0].label == "System: Domestic Water"
    assert high_risk.children[0].count == 3
    assert high_risk.children[1].label == "System: Ventilation"
    assert high_risk.children[1].count == 2


def test_ai_view_empty_states_for_model_and_clashes_and_unclassified():
    empty_nodes = build_ai_view_nodes(
        {},
        [],
        active_test_name="Active test",
        class_labels={},
        include_recent=False,
    )
    assert empty_nodes[0].label == "Load a model to browse objects"

    elements = {"A": _elem("A", "IfcPipeSegment", system="Supply", discipline="Plumbing")}
    nodes = build_ai_view_nodes(
        elements,
        [],
        active_test_name="Active test",
        class_labels={"A": "Pipe"},
        include_recent=False,
    )
    clashing = next(node for node in nodes if node.id == "ai:clashing")
    unclassified = next(node for node in nodes if node.id == "ai:unclassified")

    assert clashing.children[0].label == "Run a clash test to populate Clashing elements"
    assert unclassified.children[0].label == "All elements classified ✅"
