from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_card.engine import build_ai_card, build_clash_groups, rank_fix_candidates
from ai_card.workflow import AiCardStateStore, AiStep, FixCandidate


def _minimal_issue_context() -> dict:
    return {
        "issue_id": "ISSUE-1",
        "guid_a": "A",
        "guid_b": "B",
        "class_a": "IfcPipeSegment",
        "class_b": "IfcDuctSegment",
        "class_confidence_a": 0.9,
        "class_confidence_b": 0.8,
        "discipline_a": "VVS",
        "discipline_b": "Ventilation",
        "rule_id": "RULE-1",
        "metrics": {
            "method": "AABB",
            "min_distance_m": -0.001,
            "required_clearance_m": 0.05,
            "overlap_m": 0.001,
            "eps": 0.0001,
            "padding": 0.01,
            "bbox_a": [0, 0, 0, 1, 1, 1],
            "bbox_b": [0.8, 0.0, 0.0, 1.8, 1.0, 1.0],
        },
        "constraints": {
            "A": {"max_move_m": 0.15, "z_allowed": True, "protected": False, "movability": "Free"},
            "B": {"max_move_m": 0.10, "z_allowed": False, "protected": False, "movability": "Limited"},
        },
    }


def _minimal_project_context() -> dict:
    return {
        "issues": [
            {
                "issue_id": "ISSUE-1",
                "guid_a": "A",
                "guid_b": "B",
                "class_a": "IfcPipeSegment",
                "class_b": "IfcDuctSegment",
                "discipline_a": "VVS",
                "discipline_b": "Ventilation",
                "required_clearance_m": 0.05,
                "constraints": {
                    "A": {"max_move_m": 0.15, "z_allowed": True, "protected": False},
                    "B": {"max_move_m": 0.10, "z_allowed": False, "protected": False},
                },
            }
        ],
        "aabbs": {
            "A": (0.0, 0.0, 0.0, 1.0, 1.0, 1.0),
            "B": (0.8, 0.0, 0.0, 1.8, 1.0, 1.0),
            "C": (5.0, 5.0, 0.0, 6.0, 6.0, 1.0),
        },
        "rulepack_ids": ["core-v1"],
        "camera_label": "-",
        "fix_cache": {},
    }


def test_state_init_and_persistence_roundtrip(tmp_path):
    store = AiCardStateStore(tmp_path)
    state = store.load_state("ISSUE-1")
    assert state.issue_id == "ISSUE-1"
    assert state.active_step == AiStep.CREATED
    state.chosen_owner = "VVS"
    state.completed_steps.add(AiStep.RESPONSIBILITY)
    state.notes["RESPONSIBILITY"] = "Owner confirmed"
    store.save_state(state)

    loaded = store.load_state("ISSUE-1")
    assert loaded.chosen_owner == "VVS"
    assert AiStep.RESPONSIBILITY in loaded.completed_steps
    assert loaded.notes["RESPONSIBILITY"] == "Owner confirmed"


def test_blocked_step_behavior_adds_unlock_checklist(tmp_path):
    issue_context = {
        "issue_id": "ISSUE-BLOCKED",
        "guid_a": "A",
        "guid_b": "B",
        "class_a": "Unknown",
        "class_b": "Unknown",
        "discipline_a": "",
        "discipline_b": "",
        "rule_id": "RULE-MISSING",
        "metrics": {},
        "constraints": {"A": {}, "B": {}},
    }
    project_context = {"issues": [], "aabbs": {}, "rulepack_ids": [], "fix_cache": {}}
    store = AiCardStateStore(tmp_path)
    store.patch_state("ISSUE-BLOCKED", active_step=AiStep.RESPONSIBILITY)
    state, payload = build_ai_card(
        issue_context=issue_context,
        project_context=project_context,
        rulepacks=None,
        geometry_engine={},
        store=store,
    )
    assert state.active_step == AiStep.RESPONSIBILITY
    step_status = {item.step: item.status for item in payload.stepper}
    assert step_status[AiStep.RESPONSIBILITY] == "blocked"
    assert step_status[AiStep.RULE_BASIS] == "blocked"
    assert any(getattr(block, "kind", "") == "checklist" for block in payload.blocks)


def test_grouping_creates_expected_components():
    issues = [
        {"issue_id": "I1", "guid_a": "A", "guid_b": "B", "discipline_a": "VVS", "discipline_b": "EL"},
        {"issue_id": "I2", "guid_a": "B", "guid_b": "C", "discipline_a": "VVS", "discipline_b": "EL"},
        {"issue_id": "I3", "guid_a": "X", "guid_b": "Y", "discipline_a": "Vent", "discipline_b": "EL"},
    ]
    aabbs = {
        "A": (0.0, 0.0, 0.0, 1.0, 1.0, 1.0),
        "B": (0.8, 0.0, 0.0, 1.8, 1.0, 1.0),
        "C": (1.5, 0.0, 0.0, 2.5, 1.0, 1.0),
        "X": (10.0, 10.0, 0.0, 11.0, 11.0, 1.0),
        "Y": (11.5, 10.0, 0.0, 12.5, 11.0, 1.0),
    }
    grouped = build_clash_groups(issues, aabbs, distance_threshold_m=2.0)
    assert grouped["issue_to_group"]["I1"] == grouped["issue_to_group"]["I2"]
    assert grouped["issue_to_group"]["I3"] != grouped["issue_to_group"]["I1"]


def test_ranking_sorts_correctly():
    candidates = [
        FixCandidate(
            fix_id="f-low",
            target_element="A",
            type="translate",
            vector=(0.01, 0.0, 0.0),
            solves_issue_ids=["i1"],
            creates_new_issue_estimate=0,
            min_clearance_after=0.01,
            violates_constraints=[],
            score=10.0,
            explanation=[],
            citations=[],
            preview_payload={},
        ),
        FixCandidate(
            fix_id="f-high",
            target_element="A",
            type="translate",
            vector=(0.02, 0.0, 0.0),
            solves_issue_ids=["i1", "i2"],
            creates_new_issue_estimate=0,
            min_clearance_after=0.02,
            violates_constraints=[],
            score=25.0,
            explanation=[],
            citations=[],
            preview_payload={},
        ),
        FixCandidate(
            fix_id="f-mid-created",
            target_element="A",
            type="translate",
            vector=(0.01, 0.0, 0.0),
            solves_issue_ids=["i1", "i2"],
            creates_new_issue_estimate=2,
            min_clearance_after=0.02,
            violates_constraints=[],
            score=25.0,
            explanation=[],
            citations=[],
            preview_payload={},
        ),
    ]
    ranked = rank_fix_candidates(candidates)
    assert ranked[0].fix_id == "f-high"
    assert ranked[1].fix_id == "f-mid-created"
    assert ranked[2].fix_id == "f-low"


def test_trace_structure_is_stable(tmp_path):
    store = AiCardStateStore(tmp_path)
    issue_context = _minimal_issue_context()
    project_context = _minimal_project_context()
    rulepack = SimpleNamespace(
        generated_rules=[
            {
                "id": "RULE-1",
                "source": {
                    "doc": "DS 475:2012",
                    "section": "§7.2",
                    "quote": "Kort relevant uddrag.",
                },
            }
        ],
        utility_rules=[],
    )
    _state, payload = build_ai_card(
        issue_context=issue_context,
        project_context=project_context,
        rulepacks=rulepack,
        geometry_engine={},
        store=store,
    )
    trace = payload.to_dict()["trace"]
    assert set(["trace_version", "issue_id", "timestamp", "inputs", "steps"]).issubset(trace.keys())
    assert set(["elementA", "elementB", "geometry", "scope"]).issubset(trace["inputs"].keys())
    first_step = trace["steps"][0]
    assert set(["id", "kind", "title", "data", "children", "ok", "warnings", "errors"]).issubset(first_step.keys())
