from detection import evaluate_pair, generate_issues_from_search_sets


def test_evaluate_pair_clearance_positive():
    aabb_a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    aabb_b = (2.0, 0.0, 0.0, 3.0, 1.0, 1.0)
    issue = evaluate_pair("a", "b", aabb_a, aabb_b, respect=0.5, tolerance=0.0, rule_id="R", severity="High")
    assert issue.clearance > 0


def test_evaluate_pair_clearance_negative():
    aabb_a = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    aabb_b = (1.1, 0.0, 0.0, 2.0, 1.0, 1.0)
    issue = evaluate_pair("a", "b", aabb_a, aabb_b, respect=0.5, tolerance=0.0, rule_id="R", severity="High")
    assert issue.clearance < 0


def test_generate_issues_from_search_sets_uses_aabb_intersection():
    aabbs = {
        "a": (0.0, 0.0, 0.0, 1.0, 1.0, 1.0),
        "b": (0.5, 0.5, 0.5, 1.2, 1.2, 1.2),
        "c": (2.0, 2.0, 2.0, 3.0, 3.0, 3.0),
    }
    issues = generate_issues_from_search_sets(
        set_a_guids=["a", "c"],
        set_b_guids=["b"],
        aabbs=aabbs,
        set_names_a={"a": ["Pipes"], "c": ["Pipes"]},
        set_names_b={"b": ["Drainage"]},
    )
    assert len(issues) == 1
    issue = issues[0]
    assert {issue.guid_a, issue.guid_b} == {"a", "b"}
    assert issue.bbox_overlap is not None
    assert issue.bbox_overlap[0] > 0
    assert issue.search_set_names_a == ["Pipes"]
    assert issue.search_set_names_b == ["Drainage"]
