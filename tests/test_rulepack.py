from rules import RulePack


def test_rulepack_resolves_constraints_from_data():
    rulepack = RulePack.from_dict(
        {
            "defaultClearanceMm": 123.0,
            "maxMove": {"Drainage": 650.0, "IfcPipeSegment": 500.0},
            "allowedAxes": {"Drainage": ["x", "y"]},
            "zAllowed": {"Drainage": False},
            "slope": {"enabled": True, "minSlopePermille": 5.0, "classes": ["Drainage"]},
            "clearanceMatrix": [
                {"typeA": "Drainage", "typeB": "Drainage", "mm": 275.0},
            ],
        }
    )

    clearance, clearance_rule = rulepack.resolve_clearance_mm("Drainage", "Drainage")
    assert clearance == 275.0
    assert clearance_rule == "drainage|drainage"

    max_move, max_move_rule = rulepack.resolve_max_move_mm("IfcPipeSegment", "Drainage")
    assert max_move == 650.0
    assert max_move_rule == "drainage"

    allowed_axes, allowed_axes_rule = rulepack.resolve_allowed_axes("Drainage", "IfcPipeSegment")
    assert allowed_axes == ["x", "y"]
    assert allowed_axes_rule == "drainage"

    z_allowed, z_allowed_rule = rulepack.resolve_z_allowed("Drainage", "IfcPipeSegment")
    assert z_allowed is False
    assert z_allowed_rule == "drainage"

    assert rulepack.slope_applies_to("Drainage", "IfcPipeSegment") is True
    assert rulepack.slope_applies_to("Unknown", "IfcPipeSegment") is False


def test_max_move_falls_back_to_type_when_class_has_no_override():
    rulepack = RulePack.from_dict({"maxMove": {"IfcPipeSegment": 480.0}})
    max_move, source = rulepack.resolve_max_move_mm("IfcPipeSegment", "NotConfiguredClass")
    assert max_move == 480.0
    assert source == "ifcpipesegment"


def test_clearance_default_is_rulepack_value_not_hardcoded():
    rulepack = RulePack.from_dict({"defaultClearanceMm": 42.0})
    clearance, source = rulepack.resolve_clearance_mm("UnmappedA", "UnmappedB")
    assert clearance == 42.0
    assert source == "defaultClearanceMm"


class _DummyElement:
    def __init__(self, system: str):
        self.system = system
        self.systems = [system]
        self.system_group_names = [system]
        self.ifc_meta = {"system_groups": [system], "systems": [system], "item": {"Name": "Pipe"}}
        self.type_name = "Pipe"
        self.name = "Pipe"


def test_classification_utility_regex_mapping():
    rulepack = RulePack.from_dict(
        {
            "classification": {
                "utilities": {
                    "dcw": {"system_group_regex": [r"domestic\s*cold\s*water", r"\bdcw\b"]},
                    "sanitary": {"system_group_regex": [r"\bsanitary\b"]},
                }
            }
        }
    )
    result_a = rulepack.classify(_DummyElement("Domestic Cold Water"))
    result_b = rulepack.classify(_DummyElement("Sanitary"))
    assert result_a["utilityType"] == "dcw"
    assert result_b["utilityType"] == "sanitary"


def test_utility_rule_match_is_symmetric_and_relation_aware():
    rulepack = RulePack.from_dict(
        {
            "rules": [
                {
                    "id": "dcw_sanitary_parallel",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "parallel"},
                    "constraint": {"min_distance": 0.5, "unit": "m", "measure": "clear_distance"},
                },
                {
                    "id": "dcw_sanitary_crossing",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "crossing"},
                    "constraint": {"min_distance": 0.1, "unit": "m", "measure": "clear_distance"},
                },
            ]
        }
    )
    min_parallel, rule_parallel = rulepack.resolve_min_distance_m("sanitary", "dcw", "parallel")
    min_crossing, rule_crossing = rulepack.resolve_min_distance_m("dcw", "sanitary", "crossing")
    assert min_parallel == 0.5
    assert min_crossing == 0.1
    assert rule_parallel is not None and rule_parallel.rule_id == "dcw_sanitary_parallel"
    assert rule_crossing is not None and rule_crossing.rule_id == "dcw_sanitary_crossing"


def test_utility_rule_unit_conversion_from_mm_to_m():
    rulepack = RulePack.from_dict(
        {
            "rules": [
                {
                    "id": "dcw_sanitary_mm",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "any"},
                    "constraint": {"min_distance": 500, "unit": "mm", "measure": "clear_distance"},
                }
            ]
        }
    )
    min_distance, rule = rulepack.resolve_min_distance_m("dcw", "sanitary", "parallel")
    assert min_distance == 0.5
    assert rule is not None and rule.rule_id == "dcw_sanitary_mm"


def test_v2_schema_mappings_and_rule_id_are_supported():
    rulepack = RulePack.from_dict(
        {
            "rulepack": {"id": "dk.distance.dcw_vs_sanitary", "version": "1.1.0"},
            "classification": {
                "mode": "first_match_wins",
                "input_fields": ["System", "Group"],
                "mappings": [
                    {"utility": "dcw", "match": {"any_regex": [r"(?i)domestic\s*cold\s*water"]}},
                    {"utility": "sanitary", "match": {"any_regex": [r"(?i)sanitary"]}},
                ],
            },
            "rules": [
                {
                    "rule_id": "DIST_DCW_SAN_P_001",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "parallel"},
                    "constraint": {"min_distance": 0.5, "unit": "m", "measure": "clear_distance"},
                }
            ],
        }
    )
    result = rulepack.classify(_DummyElement("Domestic Cold Water"))
    min_distance, rule = rulepack.resolve_min_distance_m("sanitary", "dcw", "parallel")
    assert result["utilityType"] == "dcw"
    assert min_distance == 0.5
    assert rule is not None and rule.rule_id == "DIST_DCW_SAN_P_001"


def test_utility_rule_supports_apply_to_search_set_and_types():
    rulepack = RulePack.from_dict(
        {
            "rules": [
                {
                    "id": "dcw_sanitary_parallel",
                    "type": "min_distance_between_utilities",
                    "applies_to": {"utility_a": "dcw", "utility_b": "sanitary", "relation": "parallel"},
                    "applyToSet": "Drainage",
                    "applyToTypes": ["IfcPipeSegment", "IfcFlowSegment"],
                    "constraint": {"min_distance": 0.5, "unit": "m"},
                }
            ]
        }
    )
    _distance, rule = rulepack.resolve_min_distance_m("dcw", "sanitary", "parallel")
    assert rule is not None
    assert rule.apply_to_set == "Drainage"
    assert rule.apply_to_types == ["ifcpipesegment", "ifcflowsegment"]
