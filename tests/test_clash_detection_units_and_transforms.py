from clash_detection import (
    broadphase_pairs,
    build_world_bounds,
    detect_clashes,
    load_debug_dataset_two_cylinders,
    narrowphase_distance,
)


def test_world_bounds_apply_units_scale_and_transform():
    scene = {
        "units_scale": 0.001,  # IFC in mm -> meters
        "elements": [
            {
                "id": "A",
                "aabbLocal": (0.0, 0.0, 0.0, 1000.0, 100.0, 100.0),
                "worldMatrix": (
                    1.0,
                    0.0,
                    0.0,
                    2000.0,  # +2000 mm on x
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                ),
                "meshVertexCount": 36,
                "meshCount": 1,
                "hasRenderableGeometry": True,
            }
        ],
    }
    bounds = build_world_bounds(scene)
    a = bounds["A"].aabbWorld
    assert abs(a[0] - 2.0) < 1e-9
    assert abs(a[3] - 3.0) < 1e-9
    assert abs(a[4] - 0.1) < 1e-9


def test_far_apart_pipes_are_not_clashing():
    scene = load_debug_dataset_two_cylinders(separation_m=2.0)
    bounds = build_world_bounds(scene)

    pairs = list(broadphase_pairs(bounds, padding=0.01))
    assert pairs == []

    issues = detect_clashes(
        ["pipe_A"],
        ["pipe_B"],
        {
            "bounds": bounds,
            "clearance_for_pair": lambda _a, _b: 0.1,
            "broadphase_padding": 0.01,
        },
    )
    assert issues == []


def test_intersection_creates_clash():
    scene = load_debug_dataset_two_cylinders(separation_m=0.0)
    bounds = build_world_bounds(scene)
    a = bounds["pipe_A"]
    b = bounds["pipe_B"]
    dist = narrowphase_distance(a, b)
    assert dist.method == "centerline-cylinder"
    assert dist.minDistance < 0.0

    issues = detect_clashes(
        ["pipe_A"],
        ["pipe_B"],
        {
            "bounds": bounds,
            "clearance_for_pair": lambda _a, _b: 0.0,
            "broadphase_padding": 0.01,
        },
    )
    assert len(issues) == 1
    assert issues[0].min_distance_world is not None
    assert issues[0].min_distance_world <= 0.0


def test_same_scope_detects_pairs_when_a_equals_b():
    scene = load_debug_dataset_two_cylinders(separation_m=0.0)
    bounds = build_world_bounds(scene)

    issues = detect_clashes(
        ["pipe_A", "pipe_B"],
        ["pipe_A", "pipe_B"],
        {
            "bounds": bounds,
            "clearance_for_pair": lambda _a, _b: 0.0,
            "broadphase_padding": 0.01,
        },
    )
    assert len(issues) == 1
    pair = {issues[0].guid_a, issues[0].guid_b}
    assert pair == {"pipe_A", "pipe_B"}


def test_clearance_rule_respected_for_gap():
    scene = load_debug_dataset_two_cylinders(separation_m=0.2)
    bounds = build_world_bounds(scene)

    no_clash = detect_clashes(
        ["pipe_A"],
        ["pipe_B"],
        {
            "bounds": bounds,
            "clearance_for_pair": lambda _a, _b: 0.1,
            "broadphase_padding": 0.2,
        },
    )
    assert no_clash == []

    clash = detect_clashes(
        ["pipe_A"],
        ["pipe_B"],
        {
            "bounds": bounds,
            "clearance_for_pair": lambda _a, _b: 0.15,
            "broadphase_padding": 0.2,
        },
    )
    assert len(clash) == 1
    assert clash[0].min_distance_world is not None
    assert clash[0].min_distance_world > 0.0
    assert clash[0].clearance < 0.0
