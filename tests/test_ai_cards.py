from ai_card_controller import (
    build_issue_ai_card,
    build_selection_ai_card,
    find_rule_source_payload,
    rule_source_to_evidence,
)
from ai_cards import AiContext, AiSectionBox
from models import Issue
from rules import RulePack


def _context(*, issue_id: str | None, selected: list[str]) -> AiContext:
    return AiContext(
        activeMode="Analyze",
        selectedElementIds=list(selected),
        activeIssueId=issue_id,
        searchSetA="pipes",
        searchSetB="ducts",
        camera=None,
        sectionBox=None,
        measurement=None,
        rulepackIdsActive=["core-v1"],
        locale="da-DK",
    )


def _context_with_section(*, issue_id: str | None, selected: list[str], enabled: bool) -> AiContext:
    return AiContext(
        activeMode="Analyze",
        selectedElementIds=list(selected),
        activeIssueId=issue_id,
        searchSetA="pipes",
        searchSetB="ducts",
        camera=None,
        sectionBox=AiSectionBox(enabled=enabled, bounds=None),
        measurement=None,
        rulepackIdsActive=["core-v1"],
        locale="da-DK",
    )


def test_build_issue_ai_card_from_context_contains_summary_actions_and_citations():
    issue = Issue(
        guid_a="A",
        guid_b="B",
        rule_id="DIST_RULE_001",
        severity="High",
        clearance=-0.01,
        p_a=(0.0, 0.0, 0.0),
        p_b=(0.0, 0.0, 0.0),
        search_set_names_a=["Pipes"],
        search_set_names_b=["Ducts"],
    )
    issue.issue_id = "ISSUE-1"
    issue.min_distance_world = -0.0001
    issue.required_clearance_world = 0.1
    issue.detection_method = "centerline-cylinder"
    issue.clash_diagnostics = {
        "broadphase": {"intersects": True, "padding": 0.01},
        "narrowphase": {"eps": 1.0e-4},
    }
    card = build_issue_ai_card(
        _context(issue_id="ISSUE-1", selected=[]),
        issue,
        class_a="Pipes",
        class_b="Ducts",
        rule_source={
            "standard": "DS 475:2012",
            "section": "§7.2",
            "excerpt": "Kort relevant formulering",
            "note": "Intern tolkning",
            "yaml_path": "rules[DIST_RULE_001]",
        },
    )
    assert card.id.startswith("ai:issue:")
    assert "Clash" in card.summary
    assert len(card.recommendedActions) >= 2
    assert any(c.kind == "RULE" for c in card.citations)
    assert any(c.kind == "STANDARD" for c in card.citations)
    assert any("Hvad sker der?" in bullet for bullet in card.bullets)
    assert card.oneLineSummary
    assert len(card.factChips) >= 3
    section_ids = {section.id for section in card.sections}
    assert {"why", "docs", "assumptions", "details"}.issubset(section_ids)
    assert card.title == "Pipes vs Ducts"
    docs_section = [section for section in card.sections if section.id == "docs"][0]
    assert docs_section.title == "Kilde"
    assert any(line.startswith("Standard: DS 475:2012") for line in docs_section.lines)
    assert all(not line.startswith("[") for line in docs_section.lines)


def test_build_selection_ai_card_contains_classification_candidates_and_missing_data():
    card = build_selection_ai_card(
        _context(issue_id=None, selected=["GUID-1"]),
        selected_ids=["GUID-1"],
        class_name="Unknown",
        class_confidence=0.0,
        top_candidates=["1. Pipe (0.42)", "2. Duct (0.30)"],
        applicable_rules=["RULE_A", "RULE_B"],
        missing_data=["mangler diameter", "mangler systemnavn/systemgruppe"],
    )
    assert card.id.startswith("ai:selection:")
    assert "Unknown" in card.summary
    assert any("Top-kandidater" in bullet for bullet in card.bullets)
    assert any("Mangler data" in bullet for bullet in card.bullets)
    assert len(card.recommendedActions) >= 2
    assert card.oneLineSummary
    assert card.factChips
    assert any(section.id == "why" for section in card.sections)


def test_rule_source_mapping_supports_standard_section_excerpt():
    rulepack = RulePack.from_dict(
        {
            "rules": [
                {
                    "id": "DIST_DCW_SAN_P_001",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "parallel"},
                    "constraint": {"min_distance": 0.5, "unit": "m"},
                    "source": {
                        "standard": "DS 475:2012",
                        "section": "§7.2",
                        "excerpt": "Kort formulering",
                        "note": "Intern fortolkning",
                    },
                }
            ]
        }
    )
    payload = find_rule_source_payload(rulepack, "DIST_DCW_SAN_P_001")
    citations = rule_source_to_evidence("DIST_DCW_SAN_P_001", payload)

    assert payload.get("standard") == "DS 475:2012"
    assert payload.get("section") == "§7.2"
    assert payload.get("excerpt") == "Kort formulering"
    assert any(c.kind == "RULE" for c in citations)
    assert any(c.kind == "STANDARD" for c in citations)


def test_ai_actions_switch_to_remove_section_box_when_enabled():
    issue = Issue(
        guid_a="A",
        guid_b="B",
        rule_id="DIST_RULE_001",
        severity="High",
        clearance=-0.01,
        p_a=(0.0, 0.0, 0.0),
        p_b=(0.0, 0.0, 0.0),
    )
    issue.min_distance_world = 0.01
    issue.required_clearance_world = 0.1

    issue_card = build_issue_ai_card(
        _context_with_section(issue_id="ISSUE-2", selected=[], enabled=True),
        issue,
        class_a="Pipes",
        class_b="Pipes",
    )
    sel_card = build_selection_ai_card(
        _context_with_section(issue_id=None, selected=["GUID-1"], enabled=True),
        selected_ids=["GUID-1"],
        class_name="IfcPipeSegment",
        class_confidence=0.8,
        top_candidates=[],
        applicable_rules=[],
        missing_data=[],
    )
    issue_labels = {a.label for a in issue_card.recommendedActions}
    sel_labels = {a.label for a in sel_card.recommendedActions}
    assert "Fjern section box" in issue_labels or "Fjern section omkring clash" in issue_labels
    assert "Fjern section box" in sel_labels
