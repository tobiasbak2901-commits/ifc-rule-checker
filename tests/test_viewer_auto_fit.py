from viewer.auto_fit import compute_auto_fit_plan


def test_auto_fit_centered_model():
    plan = compute_auto_fit_plan(
        mesh_bounds_world=[(-5.0, 5.0, -2.0, 2.0, -1.0, 3.0)],
        fallback_bounds_world=[],
    )
    assert plan.valid is True
    assert plan.georeferenced is False
    assert plan.scene_offset is None
    assert plan.bbox_center == (0.0, 0.0, 1.0)
    assert plan.camera_target == (0.0, 0.0, 1.0)
    assert plan.camera_near is not None and plan.camera_near >= 0.01
    assert plan.camera_far is not None and plan.camera_far >= 1000.0


def test_auto_fit_georeferenced_model_rebases_to_origin():
    plan = compute_auto_fit_plan(
        mesh_bounds_world=[(999_500.0, 1_000_500.0, 1_999_500.0, 2_000_500.0, 50.0, 150.0)],
        fallback_bounds_world=[],
    )
    assert plan.valid is True
    assert plan.georeferenced is True
    assert plan.scene_offset == (1_000_000.0, 2_000_000.0, 100.0)
    assert plan.camera_target == (0.0, 0.0, 0.0)


def test_auto_fit_no_mesh_uses_fallback_bounds():
    plan = compute_auto_fit_plan(
        mesh_bounds_world=[],
        fallback_bounds_world=[(0.0, 10.0, 0.0, 5.0, -2.0, 2.0)],
    )
    assert plan.valid is True
    assert plan.used_fallback_bounds is True
    assert plan.bbox_world == (0.0, 10.0, 0.0, 5.0, -2.0, 2.0)


def test_auto_fit_empty_bounds_is_invalid():
    plan = compute_auto_fit_plan(mesh_bounds_world=[], fallback_bounds_world=[])
    assert plan.valid is False
    assert "No renderable geometry" in plan.message
