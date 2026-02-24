from __future__ import annotations

from dataclasses import asdict

from rulepack_generator import (
    build_rulepack_yaml,
    build_trace_for_selection,
    validate_rulepack_input,
    validate_rulepack_output,
    write_rulepack_yaml,
)
from rules import RulePack, load_rulepack


class _DummyElement:
    def __init__(
        self,
        *,
        name: str = "Drain Pipe",
        system: str = "Drainage",
        class_name: str | None = None,
        utility_type: str | None = None,
    ):
        self.name = name
        self.system = system
        self.systems = [system]
        self.system_group_names = [system]
        self.type_name = "Pipe"
        self.type = "IfcPipeSegment"
        self.class_name = class_name
        self.utility_type = utility_type
        self.ifc_meta = {
            "item": {"Name": name, "ifcType": "IfcPipeSegment"},
            "systems": [system],
            "system_groups": [system],
        }


def _valid_input() -> dict:
    return {
        "rulepack": {
            "id": "drainage_ds475_v1",
            "name": "Drainage - DS475 (Core)",
            "version": "1.0",
            "author": "MyCompany",
            "description": "Core rules for drainage in ground",
        },
        "classes": [
            {
                "id": "Drainage",
                "name": "Drainage",
                "path_candidates": ["System/Group", "Name"],
                "keywords": ["drain", "drainage"],
            }
        ],
        "defaults": {
            "constraints": {"max_move_m": 0.8, "z_move_allowed": False}
        },
        "rules": [
            {
                "id": "DS475_PARALLEL_001",
                "title": "Minimum distance between parallel lines",
                "class_in": ["Drainage"],
                "relation": "parallel",
                "check": {"type": "min_clearance", "min_distance_m": 0.5},
                "severity": "error",
                "explain_short": "Parallel drainage lines must have min. 0.5 m clearance.",
            }
        ],
    }


def test_valid_input_generates_valid_schema_v1_yaml_data():
    input_data = _valid_input()
    assert validate_rulepack_input(input_data) == []

    output_data = build_rulepack_yaml(input_data)
    assert validate_rulepack_output(output_data) == []
    assert output_data["schema_version"] == 1
    assert output_data["classification"]["classes"][0]["match"]["any"][0]["property_contains_any"]["values"] == [
        "drain",
        "drainage",
    ]
    assert output_data["rules"][0]["applies_to"]["class_in"] == ["Drainage"]
    assert output_data["rules"][0]["check"]["min_distance_m"] == 0.5


def test_write_rulepack_yaml_appends_yaml_extension(tmp_path):
    output_data = build_rulepack_yaml(_valid_input())
    written = write_rulepack_yaml(output_data, tmp_path / "generated.txt")
    assert written.suffix == ".yaml"
    assert written.exists()


def test_input_validation_rejects_invalid_rulepack_id():
    input_data = _valid_input()
    input_data["rulepack"]["id"] = "1invalid"
    errors = validate_rulepack_input(input_data)
    assert any("[rulepack.id]" in err for err in errors)


def test_input_validation_requires_unique_rule_ids():
    input_data = _valid_input()
    input_data["rules"].append(dict(input_data["rules"][0]))
    errors = validate_rulepack_input(input_data)
    assert any("[rules[1].id] must be unique" == err for err in errors)


def test_input_validation_requires_class_keywords_and_paths():
    input_data = _valid_input()
    input_data["classes"][0]["keywords"] = []
    input_data["classes"][0]["path_candidates"] = []
    errors = validate_rulepack_input(input_data)
    assert any("[classes[0].keywords]" in err for err in errors)
    assert any("[classes[0].path_candidates]" in err for err in errors)


def test_input_validation_rejects_invalid_defaults():
    input_data = _valid_input()
    input_data["defaults"]["constraints"]["max_move_m"] = -1.0
    input_data["defaults"]["constraints"]["z_move_allowed"] = "false"
    errors = validate_rulepack_input(input_data)
    assert any("[defaults.constraints.max_move_m]" in err for err in errors)
    assert any("[defaults.constraints.z_move_allowed]" in err for err in errors)


def test_input_validation_rejects_invalid_rule_check_fields():
    input_data = _valid_input()
    input_data["rules"][0]["check"] = {"type": "min_clearance", "min_distance_m": -0.1}
    input_data["rules"][0]["severity"] = "critical"
    errors = validate_rulepack_input(input_data)
    assert any("[rules[0].check.min_distance_m] must be >= 0" == err for err in errors)
    assert any("[rules[0].severity]" in err for err in errors)


def test_output_validation_rejects_wrong_schema_version():
    output_data = build_rulepack_yaml(_valid_input())
    output_data["schema_version"] = 2
    errors = validate_rulepack_output(output_data)
    assert "[schema_version] must be 1" in errors


def test_trace_builder_returns_deterministic_trace():
    output_data = build_rulepack_yaml(_valid_input())
    selected = _DummyElement(name="Drain Pipe", system="Drainage", class_name="Drainage")
    peer = _DummyElement(name="Drain Pipe B", system="Drainage", class_name="Drainage")
    selection = {
        "element": selected,
        "peer": peer,
        "relation": "parallel",
        "measured_clearance_m": 0.6,
    }
    trace_a = build_trace_for_selection(selection, output_data)
    trace_b = build_trace_for_selection(selection, output_data)
    assert asdict(trace_a) == asdict(trace_b)
    assert trace_a.topClassId == "Drainage"
    assert trace_a.ruleApplies[0].applicable is True
    assert trace_a.ruleChecks[0].passed is True


def test_generated_schema_v1_is_usable_by_rulepack_engine():
    output_data = build_rulepack_yaml(_valid_input())
    rulepack = RulePack.from_dict(output_data)

    element = _DummyElement(name="Drain Pipe", system="Drainage")
    classification = rulepack.classify(element)
    assert classification["className"] == "Drainage"

    min_distance, rule = rulepack.resolve_min_distance_m("drainage", "drainage", "parallel")
    assert min_distance == 0.5
    assert rule is not None
    assert rule.rule_id == "DS475_PARALLEL_001"


def test_generated_yaml_file_loads_through_loader(tmp_path):
    output_data = build_rulepack_yaml(_valid_input())
    path = write_rulepack_yaml(output_data, tmp_path / "pack.yaml")
    loaded = load_rulepack(path)

    element = _DummyElement(name="Drain Branch", system="Drainage")
    classification = loaded.classify(element)
    assert classification["className"] == "Drainage"
