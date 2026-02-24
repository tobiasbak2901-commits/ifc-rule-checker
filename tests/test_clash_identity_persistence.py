from pathlib import Path

from clash_detection import Bounds
from clash_tests.engine import run_clash_test
from clash_tests.models import ClashResult, ClashResultStatus, ClashTest, ClashType
from clash_tests.store import ClashTestStore
from models import Element


def _element(guid: str) -> Element:
    return Element(guid=guid, type="IfcPipeSegment", discipline="Plumbing", geom_ref=guid)


def _bounds(guid: str, aabb):
    return Bounds(
        elementId=guid,
        aabbWorld=tuple(aabb),
        hasRenderableGeometry=True,
        meshVertexCount=24,
        meshCount=1,
    )


def _result(*, clash_key: str, timestamp: float) -> ClashResult:
    return ClashResult(
        id=clash_key,
        clash_key=clash_key,
        test_id="t-persist",
        elementA_id="A",
        elementB_id="B",
        elementA_guid="A",
        elementB_guid="B",
        rule_triggered="hard:t-persist",
        min_distance_m=0.0,
        penetration_depth_m=0.05,
        method="aabb",
        timestamp=float(timestamp),
        level_id="UnknownLevel",
        proximity_cell="0,0,0",
        elementA_key="A",
        status=ClashResultStatus.NEW,
    )


def test_clash_key_is_stable_when_model_filename_changes():
    test = ClashTest(id="t-stable-key", name="Stable key", clash_type=ClashType.HARD)
    bounds = {
        "A": _bounds("A", (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),
        "B": _bounds("B", (0.7, 0.0, 0.0, 1.7, 1.0, 1.0)),
    }
    elements = {"A": _element("A"), "B": _element("B")}

    out_original = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
        default_model_ref="/tmp/model_original.ifc",
    )
    out_renamed = run_clash_test(
        test=test,
        guids_a={"A"},
        guids_b={"B"},
        bounds_map=bounds,
        elements=elements,
        model_unit_to_meter=1.0,
        default_model_ref="/tmp/model_renamed.ifc",
    )

    assert len(out_original.issues) == 1
    assert len(out_renamed.issues) == 1
    assert out_original.issues[0].issue_id == out_renamed.issues[0].issue_id
    assert out_original.results[0].clash_key == out_renamed.results[0].clash_key


def test_store_reopens_closed_clash_and_updates_last_seen(tmp_path: Path):
    store = ClashTestStore(tmp_path)
    clash_key = "clash:abc123"

    first = _result(clash_key=clash_key, timestamp=100.0)
    persisted_first = store.replace_results_for_test(
        test_id="t-persist",
        results=[first],
        groups=[],
        viewpoints=[],
    )
    assert persisted_first[clash_key]["reopened"] is False
    assert int(persisted_first[clash_key]["reopenCount"]) == 0

    closed_meta = store.update_result_status(
        test_id="t-persist",
        clash_key=clash_key,
        status="closed",
        updated_ts=200.0,
    )
    assert closed_meta["status"] == "closed"
    assert float(closed_meta["updatedAt"]) == 200.0

    second = _result(clash_key=clash_key, timestamp=250.0)
    persisted_second = store.replace_results_for_test(
        test_id="t-persist",
        results=[second],
        groups=[],
        viewpoints=[],
    )

    meta = persisted_second[clash_key]
    assert meta["reopened"] is True
    assert int(meta["reopenCount"]) == 1
    assert float(meta["firstSeenAt"]) == 100.0
    assert float(meta["lastSeenAt"]) == 250.0
    assert second.reopened is True
    assert int(second.reopen_count) == 1
    assert second.status == ClashResultStatus.NEW


def test_store_appends_issue_comment(tmp_path: Path):
    store = ClashTestStore(tmp_path)
    clash_key = "clash:comment-1"
    first = _result(clash_key=clash_key, timestamp=10.0)
    store.replace_results_for_test(
        test_id="t-comments",
        results=[first],
        groups=[],
        viewpoints=[],
    )

    meta = store.append_result_comment(
        test_id="t-comments",
        clash_key=clash_key,
        comment="Need design review",
        author="qa",
        updated_ts=12.0,
    )
    assert meta["status"] == "new"
    assert float(meta["updatedAt"]) == 12.0
    comments = list(meta.get("comments") or [])
    assert len(comments) == 1
    assert comments[0]["text"] == "Need design review"
