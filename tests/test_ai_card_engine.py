from ai.ai_card_engine import AICardEngine
from ai.models import (
    AIContext,
    ActiveIssueContext,
    ClassificationSummary,
    FixAvailability,
    RuleTraceEntry,
    ViewerState,
)


def test_engine_adds_neutral_note_when_rule_has_no_standard_refs():
    context = AIContext(
        project_id="demo",
        project_root=".",
        viewer_state=ViewerState(active_mode="Analyze"),
        active_issue=ActiveIssueContext(
            issue_id="ISSUE-1",
            rule_id="SEARCH_SET_CLASH",
            clash_verdict="CLASH",
            clash_type="overlap",
            method="AABB",
            min_distance_m=0.0,
            required_clearance_m=0.1,
            tolerance_m=0.0001,
        ),
        classification_summary=[
            ClassificationSummary(element_id="A", ai_class="Unknown", confidence=0.0),
        ],
        rules_fired=[
            RuleTraceEntry(
                rule_id="SEARCH_SET_CLASH",
                status="fired",
                reason="Rule fired",
                trace_steps=["step"],
                standard_refs=[],
            )
        ],
        standard_refs=[],
        fix_availability=FixAvailability(status="NOT_AVAILABLE", reasons=[]),
    )

    engine = AICardEngine()
    response = engine.generate_card(context, intent="EXPLAIN_CLASH")

    assert any("Ingen standard-kilde knyttet" in line for line in response.assumptions)
    assert all(item.kind != "STANDARD" for item in response.citations)
