from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clash_detection import Bounds
from clash_tests.engine import ClashRunCache, run_clash_test
from clash_tests.models import ClashTest, ClashType, default_ignore_rules
from models import Element


def _build_scene(total: int = 200):
    guids_a = []
    guids_b = []
    bounds_map = {}
    elements = {}
    spacing = 2.0
    size = 0.5
    for idx in range(int(total)):
        x = float(idx) * spacing
        guid_a = f"A-{idx:06d}"
        guid_b = f"B-{idx:06d}"
        guids_a.append(guid_a)
        guids_b.append(guid_b)
        bounds_map[guid_a] = Bounds(
            elementId=guid_a,
            aabbWorld=(x, 0.0, 0.0, x + size, size, size),
            hasRenderableGeometry=True,
            meshVertexCount=8,
            meshCount=1,
        )
        bounds_map[guid_b] = Bounds(
            elementId=guid_b,
            aabbWorld=(x + 0.2, 0.0, 0.0, x + 0.2 + size, size, size),
            hasRenderableGeometry=True,
            meshVertexCount=8,
            meshCount=1,
        )
        elements[guid_a] = Element(guid=guid_a, type="IfcPipeSegment", discipline="MEP", geom_ref=guid_a)
        elements[guid_b] = Element(guid=guid_b, type="IfcPipeSegment", discipline="MEP", geom_ref=guid_b)
    return guids_a, guids_b, bounds_map, elements


def _test_config() -> ClashTest:
    return ClashTest(
        id="cache:test",
        name="Cache test",
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=default_ignore_rules(),
    )


def test_incremental_cache_reuses_pipeline_work_on_second_run():
    guids_a, guids_b, bounds_map, elements = _build_scene(200)
    cache = ClashRunCache()
    test = _test_config()
    profile_first = {}
    profile_second = {}

    run_clash_test(
        test=test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        default_model_ref="bench:model",
        profile=profile_first,
        cache=cache,
    )
    run_clash_test(
        test=test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        default_model_ref="bench:model",
        profile=profile_second,
        cache=cache,
    )

    counts_first = dict(profile_first.get("counts") or {})
    counts_second = dict(profile_second.get("counts") or {})
    cache_second = dict(profile_second.get("cache") or {})

    assert int(counts_first.get("proxiesBuilt") or 0) > 0
    assert int(counts_second.get("proxiesBuilt") or 0) == 0
    assert int(counts_second.get("changedElements") or 0) == 0
    assert int(counts_second.get("proxyCacheHits") or 0) > 0
    assert int(counts_second.get("candidateCacheHit") or 0) == 1
    assert int(cache_second.get("narrowphaseCacheHits") or 0) > 0
    first_total = float((profile_first.get("timingsMs") or {}).get("total") or 0.0)
    second_total = float((profile_second.get("timingsMs") or {}).get("total") or 0.0)
    assert second_total > 0.0
    assert first_total > second_total


def test_incremental_cache_detects_changed_elements():
    guids_a, guids_b, bounds_map, elements = _build_scene(120)
    cache = ClashRunCache()
    test = _test_config()
    profile_first = {}
    profile_second = {}

    run_clash_test(
        test=test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        default_model_ref="bench:model",
        profile=profile_first,
        cache=cache,
    )
    changed = guids_b[0]
    bounds_map[changed] = Bounds(
        elementId=changed,
        aabbWorld=(999.0, 0.0, 0.0, 999.5, 0.5, 0.5),
        hasRenderableGeometry=True,
        meshVertexCount=8,
        meshCount=1,
    )
    run_clash_test(
        test=test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        default_model_ref="bench:model",
        profile=profile_second,
        cache=cache,
    )
    counts_second = dict(profile_second.get("counts") or {})
    assert int(counts_second.get("changedElements") or 0) >= 1
    assert int(counts_second.get("proxiesBuilt") or 0) >= 1
