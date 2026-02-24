from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Element, Issue
from ui.panels.ai_views_model import (
    build_ai_view_cards,
    build_ai_views_model,
    compute_model_health,
    derive_ai_views_workflow_state,
    get_display_name,
)


def _element(
    guid: str,
    ifc_type: str,
    *,
    name: str = "",
    system: str = "",
    discipline: str = "MEP",
    psets: dict | None = None,
) -> Element:
    systems = [system] if system else []
    meta = {
        "psets": psets or {},
        "system_groups": systems,
        "systems": systems,
    }
    return Element(
        guid=guid,
        type=ifc_type,
        discipline=discipline,
        geom_ref=guid,
        name=name,
        system=system or None,
        systems=systems,
        system_group_names=systems,
        ifc_meta=meta,
    )


def _issue(issue_id: str, guid_a: str, guid_b: str) -> Issue:
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


def test_get_display_name_pipe_and_duct_fallbacks_never_show_guid():
    pipe = _element(
        "3f8ca44f-f9fe-41f4-b74d-c34c57c30125",
        "IfcPipeSegment",
        name="Pipe Types:Default:3370",
        psets={"Pset_PipeSegmentCommon": {"NominalDiameter": 0.08}},
    )
    duct = _element(
        "97f73c68-77f2-44f2-b698-4ed9ca7d2a73",
        "IfcDuctSegment",
        name="Port_3570_System_Default",
        psets={"Pset_DuctSegmentTypeCommon": {"Width": 0.4, "Height": 0.2}},
    )

    pipe_name = get_display_name(pipe)
    duct_name = get_display_name(duct)

    assert pipe_name.startswith("Pipe")
    assert "3370" not in pipe_name
    assert pipe.guid not in pipe_name

    assert duct_name.startswith("Duct")
    assert "Port_" not in duct_name
    assert duct.guid not in duct_name


def test_compute_model_health_clamps_score_to_zero_and_hundred():
    low = compute_model_health(
        total_elements=100,
        clashing_elements=9999,
        unclassified_elements=9999,
        high_risk_buckets=999,
        top_risk_label="System: Supply",
    )
    high = compute_model_health(
        total_elements=100,
        clashing_elements=0,
        unclassified_elements=0,
        high_risk_buckets=0,
        top_risk_label="-",
    )

    assert 0 <= low.score <= 100
    assert 0 <= high.score <= 100
    assert low.score == 20
    assert high.score == 100


def test_ai_view_cards_are_sorted_by_priority_order():
    elements = {
        "A": _element("A", "IfcPipeSegment", system="Supply", name="Pipe A"),
        "B": _element("B", "IfcPipeSegment", system="Supply", name="Pipe B"),
        "C": _element("C", "IfcDuctSegment", system="Ventilation", name="Duct C"),
    }
    issues = [
        _issue("1", "A", "B"),
        _issue("2", "A", "C"),
    ]

    cards = build_ai_view_cards(
        model_state={
            "elements": elements,
            "class_labels": {"A": "Pipe", "B": "unknown", "C": "Duct"},
        },
        clash_state={"issues": issues},
        selection_state={"recent_selected": ["A", "B"]},
    )

    assert [card.id for card in cards[:4]] == ["clashing", "unclassified", "high_risk", "recent"]


def test_workflow_starts_with_step_one_only():
    workflow = derive_ai_views_workflow_state(
        total_elements=100,
        has_run=False,
        clashing_count=0,
        unclassified_count=8,
        high_risk_count=0,
    )
    assert workflow.next_step == "classify"
    assert workflow.current_step == 1
    assert workflow.is_complete is False
    assert len(workflow.steps) == 1
    assert workflow.steps[0].number == 1
    assert workflow.steps[0].status == "active"


def test_workflow_uses_quick_start_state_for_next_step():
    workflow = derive_ai_views_workflow_state(
        total_elements=100,
        has_run=False,
        clashing_count=12,
        unclassified_count=0,
        high_risk_count=4,
        quick_start_state={"currentStep": 2, "completedSteps": [1]},
    )
    assert workflow.next_step == "runClash"
    assert workflow.current_step == 2
    assert workflow.completed_steps == (1,)
    assert len(workflow.steps) == 1
    assert workflow.steps[0].number == 2
    assert workflow.steps[0].title == "Run clash test"
    assert workflow.steps[0].action_id == "runClash"


def test_workflow_is_complete_after_all_steps():
    workflow = derive_ai_views_workflow_state(
        total_elements=100,
        has_run=True,
        clashing_count=0,
        unclassified_count=0,
        high_risk_count=0,
        quick_start_state={"currentStep": 5, "completedSteps": [1, 2, 3, 4]},
    )
    assert workflow.next_step == "done"
    assert workflow.is_complete is True
    assert workflow.steps == tuple()
    assert workflow.complete_message == "Quick start complete"


def test_clashing_card_has_disabled_reason_when_no_clashes():
    elements = {
        "A": _element("A", "IfcPipeSegment", system="Supply", name="Pipe A"),
    }
    cards = build_ai_view_cards(
        model_state={"elements": elements, "class_labels": {"A": "Pipe"}},
        clash_state={"issues": [], "has_run": False},
        selection_state={},
    )
    clashing = next(card for card in cards if card.id == "clashing")
    assert clashing.primary_enabled is False
    assert clashing.primary_disabled_reason == "No clashes yet. Run a clash test first."


def test_model_workflow_disabled_reason_contains_open_clashes_rule():
    model = build_ai_views_model(
        model_state={
            "elements": {"A": _element("A", "IfcPipeSegment", system="Supply", name="Pipe A")},
            "class_labels": {"A": "Pipe"},
        },
        clash_state={"issues": [], "has_run": False},
        selection_state={},
    )
    assert model.workflow is not None
    reason_map = dict(model.workflow.disabled_reasons)
    assert reason_map.get("openClashes") == "No clashes yet. Run a clash test first."


def test_unclassified_count_drops_when_classification_label_is_set():
    elements = {
        "A": _element("A", "IfcPipeSegment", system="Drainage", name="Pipe A"),
    }
    before = build_ai_view_cards(
        model_state={"elements": elements, "class_labels": {"A": "unknown"}},
        clash_state={"issues": [], "has_run": False},
        selection_state={},
    )
    after = build_ai_view_cards(
        model_state={"elements": elements, "class_labels": {"A": "Drainage"}},
        clash_state={"issues": [], "has_run": False},
        selection_state={},
    )
    before_unclassified = next(card for card in before if card.id == "unclassified")
    after_unclassified = next(card for card in after if card.id == "unclassified")
    assert before_unclassified.count == 1
    assert after_unclassified.count == 0
