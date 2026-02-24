from resolution.high_impact_fix import (
    Clash,
    HighImpactFixConfig,
    TrialResult,
    buildElementClashMap,
    evaluateTrialAgainstClashes,
    findBestSingleMoveFixes,
    generateTranslationTrials,
    getHotElements,
    rankFixes,
)


def test_grouping_returns_hot_element_by_degree():
    clashes = [
        Clash(id="c1", aId="A", bId="B", type="hard"),
        Clash(id="c2", aId="A", bId="C", type="hard"),
        Clash(id="c3", aId="B", bId="C", type="hard"),
        Clash(id="c4", aId="D", bId="E", type="hard"),
    ]
    clash_map = buildElementClashMap(clashes)
    assert sorted(clash_map["A"]) == ["c1", "c2"]
    hot = getHotElements(clashes, topN=2)
    assert hot[0].elementId == "A"
    assert hot[0].clashCount == 2
    assert list(hot[0].opponentIds) == ["B", "C"]


def test_translation_trial_resolves_point_based_clashes():
    clashes = [
        Clash(id="c1", aId="A", bId="B", type="hard", pA=(0.0, 0.0, 0.0), pB=(0.03, 0.0, 0.0)),
        Clash(id="c2", aId="A", bId="C", type="hard", pA=(0.0, 0.0, 0.0), pB=(0.04, 0.0, 0.0)),
    ]
    clashes_by_element = {"A": clashes}
    aabbs = {
        "A": (0.0, 0.0, 0.0, 0.1, 0.1, 0.1),
        "B": (0.2, 0.0, 0.0, 0.3, 0.1, 0.1),
        "C": (0.4, 0.0, 0.0, 0.5, 0.1, 0.1),
    }
    cfg = HighImpactFixConfig(
        step_sizes_mm=(25.0, 50.0),
        max_move_mm=50.0,
        z_move_allowed=False,
        model_unit_to_meter=1.0,
    )
    trial = evaluateTrialAgainstClashes(
        moveElementId="A",
        vectorMm=(50.0, 0.0, 0.0),
        clashesByElement=clashes_by_element,
        elementAabbs=aabbs,
        config=cfg,
    )
    assert sorted(trial.resolvedClashIds) == ["c1", "c2"]
    assert trial.newClashCount == 0


def test_ranking_prefers_more_resolved_fewer_new_and_smaller_move():
    trials = [
        TrialResult(
            elementId="A",
            vectorMm=(100.0, 0.0, 0.0),
            moveDistanceMm=100.0,
            resolvedClashIds=("c1", "c2", "c3"),
            impactedClashIds=("c1", "c2", "c3"),
            unresolvedClashIds=tuple(),
            newClashCount=0,
            newClashPairIds=tuple(),
            perClashReason={},
            worstClearanceAfterMm=5.0,
            avgClearanceAfterMm=7.0,
            score=280.0,
        ),
        TrialResult(
            elementId="B",
            vectorMm=(50.0, 0.0, 0.0),
            moveDistanceMm=50.0,
            resolvedClashIds=("c1", "c2", "c3"),
            impactedClashIds=("c1", "c2", "c3"),
            unresolvedClashIds=tuple(),
            newClashCount=1,
            newClashPairIds=("B|X",),
            perClashReason={},
            worstClearanceAfterMm=5.0,
            avgClearanceAfterMm=7.0,
            score=280.0,
        ),
        TrialResult(
            elementId="C",
            vectorMm=(25.0, 0.0, 0.0),
            moveDistanceMm=25.0,
            resolvedClashIds=("c1", "c2"),
            impactedClashIds=("c1", "c2", "c3"),
            unresolvedClashIds=("c3",),
            newClashCount=0,
            newClashPairIds=tuple(),
            perClashReason={},
            worstClearanceAfterMm=5.0,
            avgClearanceAfterMm=7.0,
            score=200.0,
        ),
    ]
    ranked = rankFixes(trials, topK=3, zMovePenalty=30.0)
    assert ranked[0].moveElementId == "A"
    assert ranked[1].moveElementId == "B"
    assert ranked[2].moveElementId == "C"


def test_pipeline_is_deterministic():
    clashes = [
        Clash(id="c1", aId="A", bId="B", type="hard", pA=(0.0, 0.0, 0.0), pB=(0.02, 0.0, 0.0)),
        Clash(id="c2", aId="A", bId="C", type="hard", pA=(0.0, 0.0, 0.0), pB=(0.03, 0.0, 0.0)),
    ]
    aabbs = {
        "A": (0.0, 0.0, 0.0, 0.1, 0.1, 0.1),
        "B": (0.2, 0.0, 0.0, 0.3, 0.1, 0.1),
        "C": (0.4, 0.0, 0.0, 0.5, 0.1, 0.1),
    }
    cfg = HighImpactFixConfig(
        top_hot_elements=2,
        top_k=3,
        step_sizes_mm=(25.0, 50.0),
        max_move_mm=50.0,
        z_move_allowed=False,
        model_unit_to_meter=1.0,
    )
    first = findBestSingleMoveFixes(clashes=clashes, elementAabbs=aabbs, config=cfg)
    second = findBestSingleMoveFixes(clashes=clashes, elementAabbs=aabbs, config=cfg)
    assert [fix.id for fix in first.fixes] == [fix.id for fix in second.fixes]
    assert first.trialsTested == second.trialsTested
    assert generateTranslationTrials("A", cfg.step_sizes_mm, cfg.max_move_mm, cfg.z_move_allowed) == [
        (25.0, 0.0, 0.0),
        (50.0, 0.0, 0.0),
        (-25.0, 0.0, 0.0),
        (-50.0, 0.0, 0.0),
        (0.0, 25.0, 0.0),
        (0.0, 50.0, 0.0),
        (0.0, -25.0, 0.0),
        (0.0, -50.0, 0.0),
    ]
