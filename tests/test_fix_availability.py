from fix_availability import computeFixAvailability


def _base_context():
    return {
        "classification": {
            "A": {"ifcType": "IfcPipeSegment", "systemGroup": "Drainage", "name": "A", "class": "Unknown", "confidence": 0.0},
            "B": {"ifcType": "IfcPipeSegment", "systemGroup": "Drainage", "name": "B", "class": "Unknown", "confidence": 0.0},
        },
        "constraints": {
            "A": {"movability": "Locked", "maxMoveM": 0.0, "zAllowed": False, "protected": False},
            "B": {"movability": "Locked", "maxMoveM": 0.0, "zAllowed": False, "protected": False},
        },
        "rulepack": {"path": "rulepack", "id": "core-v1", "version": "1.0"},
        "ruleTrace": {
            "A": {"signalsMatched": 0, "topSignals": [], "failed": []},
            "B": {"signalsMatched": 0, "topSignals": [], "failed": []},
        },
        "clashContext": {"minDistanceM": 0.5, "method": "AABB", "pA": [0.0, 0.0, 0.0], "pB": [1.0, 0.0, 0.0]},
        "searchSets": {"A": {"name": "Set A", "count": 5}, "B": {"name": "Set B", "count": 6}},
        "ruleApplicability": {"anyApplicable": False, "hasGenericFallback": False},
    }


def _codes(report):
    return {entry["code"] for entry in report.get("reasons") or []}


def test_unknown_unknown_issue_reports_classification_unknown_reasons():
    context = _base_context()
    report = computeFixAvailability(issue=object(), context=context)
    assert report["status"] == "NOT_AVAILABLE"
    codes = _codes(report)
    assert "CLASSIFICATION_UNKNOWN_A" in codes
    assert "CLASSIFICATION_UNKNOWN_B" in codes
    assert "NO_APPLICABLE_RULES" in codes


def test_known_classes_but_zero_max_move_reports_max_move_zero():
    context = _base_context()
    context["classification"]["A"]["class"] = "Drainage"
    context["classification"]["A"]["confidence"] = 0.9
    context["classification"]["B"]["class"] = "Drainage"
    context["classification"]["B"]["confidence"] = 0.8
    context["ruleApplicability"] = {"anyApplicable": True, "hasGenericFallback": True}
    report = computeFixAvailability(issue=object(), context=context)
    assert report["status"] == "NOT_AVAILABLE"
    assert "MAX_MOVE_ZERO" in _codes(report)


def test_known_classes_with_applicable_rule_reports_available():
    context = _base_context()
    context["classification"]["A"]["class"] = "Drainage"
    context["classification"]["A"]["confidence"] = 0.9
    context["classification"]["B"]["class"] = "Drainage"
    context["classification"]["B"]["confidence"] = 0.8
    context["constraints"]["A"]["movability"] = "Free"
    context["constraints"]["A"]["maxMoveM"] = 0.8
    context["constraints"]["A"]["protected"] = False
    context["constraints"]["B"]["movability"] = "Protected"
    context["constraints"]["B"]["maxMoveM"] = 0.8
    context["constraints"]["B"]["protected"] = True
    context["ruleApplicability"] = {"anyApplicable": True, "hasGenericFallback": False}
    report = computeFixAvailability(issue=object(), context=context)
    assert report["status"] == "AVAILABLE"
    assert report["reasons"] == []
