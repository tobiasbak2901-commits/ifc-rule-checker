from fix_generator_fallback import FallbackTrial, FixGeneratorFallback


def test_unknown_classification_fallback_produces_candidates():
    offsets = FixGeneratorFallback.candidate_offsets_mm(z_move_allowed=False)
    assert offsets

    def evaluator(dx_mm: float, dy_mm: float, dz_mm: float):
        resolved = 1 if abs(dx_mm) == 25.0 and abs(dy_mm) <= 1e-9 and abs(dz_mm) <= 1e-9 else 0
        return {
            "resolved_clashes": resolved,
            "min_clearance_improvement_mm": 30.0 if resolved else 0.0,
            "creates_new_clash": False,
            "violates_constraints": False,
        }

    trials = FixGeneratorFallback.build_trials(
        element_id="GUID-A",
        offsets_mm=offsets,
        evaluator=evaluator,
    )
    ranked = FixGeneratorFallback.rank_trials(trials)
    assert trials
    assert any(trial.resolved_clashes > 0 for trial in ranked)
    assert ranked[0].resolved_clashes > 0


def test_fallback_ranking_is_deterministic():
    trials = [
        FallbackTrial(
            element_id="A",
            dx_mm=25.0,
            dy_mm=0.0,
            dz_mm=0.0,
            move_distance_mm=25.0,
            resolved_clashes=1,
            min_clearance_improvement_mm=40.0,
            creates_new_clash=False,
            violates_constraints=False,
            score=FixGeneratorFallback.score_trial(
                resolved_clashes=1,
                min_clearance_improvement_mm=40.0,
                move_distance_mm=25.0,
                creates_new_clash=False,
                violates_constraints=False,
            ),
        ),
        FallbackTrial(
            element_id="B",
            dx_mm=-25.0,
            dy_mm=0.0,
            dz_mm=0.0,
            move_distance_mm=25.0,
            resolved_clashes=1,
            min_clearance_improvement_mm=40.0,
            creates_new_clash=False,
            violates_constraints=False,
            score=FixGeneratorFallback.score_trial(
                resolved_clashes=1,
                min_clearance_improvement_mm=40.0,
                move_distance_mm=25.0,
                creates_new_clash=False,
                violates_constraints=False,
            ),
        ),
    ]
    rank_one = FixGeneratorFallback.rank_trials(trials)
    rank_two = FixGeneratorFallback.rank_trials(trials)
    assert [t.element_id for t in rank_one] == [t.element_id for t in rank_two]
    assert [t.dx_mm for t in rank_one] == [t.dx_mm for t in rank_two]
