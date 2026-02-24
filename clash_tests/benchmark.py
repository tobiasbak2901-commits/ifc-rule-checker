from __future__ import annotations

from dataclasses import dataclass
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from clash_detection import Bounds
from models import Element

from .engine import ClashRunCache, run_clash_test
from .models import (
    GROUP_ELEMENT_A,
    GROUP_PROXIMITY,
    ClashTest,
    ClashType,
    default_ignore_rules,
)


@dataclass(frozen=True)
class ClashBenchScenarioResult:
    name: str
    requested_elements: int
    timings_ms: Dict[str, float]
    timings_ms_second_run: Dict[str, float]
    counts: Dict[str, int]
    counts_second_run: Dict[str, int]
    speedup_second_run: float
    memory_mb_before: Optional[float]
    memory_mb_after: Optional[float]
    memory_mb_delta: Optional[float]
    fps_impact: Dict[str, float]


@dataclass(frozen=True)
class ClashBenchReport:
    started_at: float
    finished_at: float
    scenarios: List[ClashBenchScenarioResult]


DEFAULT_SCENARIOS: Tuple[Tuple[str, int], ...] = (
    ("small", 1_000),
    ("medium", 10_000),
    ("large", 50_000),
)


def run_clash_benchmark(
    *,
    scenarios: Optional[Sequence[Tuple[str, int]]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> ClashBenchReport:
    started_at = time.time()
    out: List[ClashBenchScenarioResult] = []
    for scenario_name, total_elements in list(scenarios or DEFAULT_SCENARIOS):
        result = _run_single_scenario(str(scenario_name), int(total_elements))
        out.append(result)
        if callable(log):
            log(
                f"[ClashBench] {result.name}: first={result.timings_ms.get('total', 0.0):.2f} ms, "
                f"second={result.timings_ms_second_run.get('total', 0.0):.2f} ms, "
                f"speedup={result.speedup_second_run:.2f}x, "
                f"candidates={result.counts.get('candidates', 0)}, "
                f"confirmed={result.counts.get('confirmedClashes', 0)}"
            )
    finished_at = time.time()
    return ClashBenchReport(started_at=float(started_at), finished_at=float(finished_at), scenarios=out)


def format_clash_benchmark(report: ClashBenchReport) -> str:
    lines: List[str] = []
    total_ms = max(0.0, (float(report.finished_at) - float(report.started_at)) * 1000.0)
    lines.append("Clash benchmark - simpel log")
    lines.append(f"Scenarier: {len(report.scenarios)}")
    lines.append(f"Samlet tid: {_format_duration(total_ms)}")
    for scenario in list(report.scenarios or []):
        total_step_ms = float(scenario.timings_ms.get("total", 0.0) or 0.0)
        total_step_ms_second = float(scenario.timings_ms_second_run.get("total", 0.0) or 0.0)
        fps_if_blocking = float(scenario.fps_impact.get("fpsIfBlocking", 0.0) or 0.0)
        fps_rounded = int(round(fps_if_blocking)) if fps_if_blocking > 0.0 else 0
        elements_a = int(scenario.counts.get("elementsA", 0) or 0)
        elements_b = int(scenario.counts.get("elementsB", 0) or 0)
        proxies_built = int(scenario.counts.get("proxiesBuilt", 0) or 0)
        proxies_built_second = int(scenario.counts_second_run.get("proxiesBuilt", 0) or 0)
        candidates = int(scenario.counts.get("candidates", 0) or 0)
        confirmed = int(scenario.counts.get("confirmedClashes", 0) or 0)
        changed_second = int(scenario.counts_second_run.get("changedElements", 0) or 0)
        lines.append("")
        lines.append(f"Scenarie: {scenario.name} ({int(scenario.requested_elements)} elementer)")
        lines.append(f"Tid: {_format_duration(total_step_ms)}")
        lines.append(f"Tid (1. koersel): {_format_duration(total_step_ms)}")
        lines.append(f"Tid (2. koersel): {_format_duration(total_step_ms_second)}")
        lines.append(f"Speedup (2. koersel): {float(scenario.speedup_second_run):.2f}x")
        lines.append(f"FPS antal (estimat): {fps_rounded}")
        lines.append(f"Elementer A: {elements_a}")
        lines.append(f"Elementer B: {elements_b}")
        lines.append(f"Proxies bygget: {proxies_built}")
        lines.append(f"Proxies bygget (2. koersel): {proxies_built_second}")
        lines.append(f"Aendrede elementer (2. koersel): {changed_second}")
        lines.append(f"Kandidater: {candidates}")
        lines.append(f"Bekraeftede clashes: {confirmed}")
        lines.append(
            "Byg proxies: "
            f"{_format_duration(scenario.timings_ms.get('buildProxies', 0.0))} -> "
            f"{_format_duration(scenario.timings_ms_second_run.get('buildProxies', 0.0))}"
        )
        lines.append(
            "Grovfase: "
            f"{_format_duration(scenario.timings_ms.get('broadphase', 0.0))} -> "
            f"{_format_duration(scenario.timings_ms_second_run.get('broadphase', 0.0))}"
        )
        lines.append(
            "Smalfase: "
            f"{_format_duration(scenario.timings_ms.get('narrowphase', 0.0))} -> "
            f"{_format_duration(scenario.timings_ms_second_run.get('narrowphase', 0.0))}"
        )
        lines.append(
            "Gruppering: "
            f"{_format_duration(scenario.timings_ms.get('grouping', 0.0))} -> "
            f"{_format_duration(scenario.timings_ms_second_run.get('grouping', 0.0))}"
        )
        mem_before = scenario.memory_mb_before
        mem_after = scenario.memory_mb_after
        mem_delta = scenario.memory_mb_delta
        if mem_before is None or mem_after is None or mem_delta is None:
            lines.append("Hukommelse: ikke tilgaengelig")
        else:
            lines.append(
                f"Hukommelse (MB): foer={mem_before:.2f}, efter={mem_after:.2f}, aendring={mem_delta:+.2f}"
            )
        lines.append(f"Frames paavirket: {scenario.fps_impact.get('framesBlocked', 0.0):.2f}")
    return "\n".join(lines)


def _format_duration(value_ms: float) -> str:
    ms = max(0.0, float(value_ms or 0.0))
    if ms >= 60_000.0:
        minutes = int(ms // 60_000.0)
        rest_seconds = (ms - float(minutes) * 60_000.0) / 1000.0
        if rest_seconds >= 1.0:
            return f"{minutes} min {rest_seconds:.1f} sek"
        return f"{minutes} min"
    if ms >= 1_000.0:
        seconds = ms / 1000.0
        if seconds >= 10.0:
            return f"{seconds:.1f} sek"
        return f"{seconds:.2f} sek"
    if ms >= 100.0:
        return f"{ms:.0f} ms"
    return f"{ms:.2f} ms"


def _run_single_scenario(name: str, total_elements: int) -> ClashBenchScenarioResult:
    safe_total = max(2, int(total_elements))
    guids_a, guids_b, bounds_map, elements = _build_synthetic_scene(safe_total)
    set_names_a = {guid: [f"{name}:A"] for guid in guids_a}
    set_names_b = {guid: [f"{name}:B"] for guid in guids_b}
    clash_test = ClashTest(
        id=f"bench:{name}",
        name=f"ClashBench {name}",
        search_set_ids_a=["bench:a"],
        search_set_ids_b=["bench:b"],
        clash_type=ClashType.HARD,
        threshold_mm=0.0,
        ignore_rules=default_ignore_rules(),
        grouping_order=[GROUP_ELEMENT_A, GROUP_PROXIMITY],
        proximity_meters=6.0,
        auto_viewpoint=False,
        auto_screenshot=False,
    )

    profile_first: Dict[str, object] = {}
    profile_second: Dict[str, object] = {}
    run_cache = ClashRunCache()
    mem_before = _memory_mb()
    run_clash_test(
        test=clash_test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        set_names_a=set_names_a,
        set_names_b=set_names_b,
        level_intervals=[],
        model_unit_to_meter=1.0,
        default_model_ref=f"bench:{name}",
        broadphase_padding_m=0.01,
        eps=1.0e-4,
        profile=profile_first,
        cache=run_cache,
    )
    run_clash_test(
        test=clash_test,
        guids_a=guids_a,
        guids_b=guids_b,
        bounds_map=bounds_map,
        elements=elements,
        set_names_a=set_names_a,
        set_names_b=set_names_b,
        level_intervals=[],
        model_unit_to_meter=1.0,
        default_model_ref=f"bench:{name}",
        broadphase_padding_m=0.01,
        eps=1.0e-4,
        profile=profile_second,
        cache=run_cache,
    )
    mem_after = _memory_mb()

    timings_raw = dict(profile_first.get("timingsMs") or {})
    timings_second_raw = dict(profile_second.get("timingsMs") or {})
    counts_raw = dict(profile_first.get("counts") or {})
    counts_second_raw = dict(profile_second.get("counts") or {})
    timings_ms = {
        "buildProxies": float(timings_raw.get("buildProxies") or 0.0),
        "broadphase": float(timings_raw.get("broadphase") or 0.0),
        "narrowphase": float(timings_raw.get("narrowphase") or 0.0),
        "grouping": float(timings_raw.get("grouping") or 0.0),
        "total": float(timings_raw.get("total") or 0.0),
    }
    timings_ms_second = {
        "buildProxies": float(timings_second_raw.get("buildProxies") or 0.0),
        "broadphase": float(timings_second_raw.get("broadphase") or 0.0),
        "narrowphase": float(timings_second_raw.get("narrowphase") or 0.0),
        "grouping": float(timings_second_raw.get("grouping") or 0.0),
        "total": float(timings_second_raw.get("total") or 0.0),
    }
    counts = {
        "elementsA": int(counts_raw.get("elementsA") or len(guids_a)),
        "elementsB": int(counts_raw.get("elementsB") or len(guids_b)),
        "proxiesBuilt": int(counts_raw.get("proxiesBuilt") or 0),
        "changedElements": int(counts_raw.get("changedElements") or 0),
        "candidates": int(counts_raw.get("candidates") or 0),
        "confirmedClashes": int(counts_raw.get("confirmedClashes") or 0),
    }
    counts_second = {
        "elementsA": int(counts_second_raw.get("elementsA") or len(guids_a)),
        "elementsB": int(counts_second_raw.get("elementsB") or len(guids_b)),
        "proxiesBuilt": int(counts_second_raw.get("proxiesBuilt") or 0),
        "changedElements": int(counts_second_raw.get("changedElements") or 0),
        "candidates": int(counts_second_raw.get("candidates") or 0),
        "confirmedClashes": int(counts_second_raw.get("confirmedClashes") or 0),
    }
    mem_delta: Optional[float] = None
    if mem_before is not None and mem_after is not None:
        mem_delta = float(mem_after) - float(mem_before)
    fps_impact = _fps_impact_estimate(timings_ms_second.get("total", 0.0))
    first_total = float(timings_ms.get("total") or 0.0)
    second_total = max(1.0e-9, float(timings_ms_second.get("total") or 0.0))
    speedup = float(first_total / second_total) if first_total > 0.0 else 0.0

    return ClashBenchScenarioResult(
        name=str(name),
        requested_elements=int(safe_total),
        timings_ms=timings_ms,
        timings_ms_second_run=timings_ms_second,
        counts=counts,
        counts_second_run=counts_second,
        speedup_second_run=float(speedup),
        memory_mb_before=mem_before,
        memory_mb_after=mem_after,
        memory_mb_delta=mem_delta,
        fps_impact=fps_impact,
    )


def _build_synthetic_scene(total_elements: int) -> Tuple[List[str], List[str], Dict[str, Bounds], Dict[str, Element]]:
    n_total = max(2, int(total_elements))
    n_a = max(1, n_total // 2)
    n_b = max(1, n_total - n_a)
    max_n = max(n_a, n_b)
    spacing = 2.0
    overlap_every = 20
    size = 0.4

    guids_a: List[str] = []
    guids_b: List[str] = []
    bounds_map: Dict[str, Bounds] = {}
    elements: Dict[str, Element] = {}

    for idx in range(max_n):
        x = float(idx) * spacing
        if idx < n_a:
            guid_a = f"A-{idx:06d}"
            guids_a.append(guid_a)
            bounds_map[guid_a] = _make_bound(guid_a, x=x, y=0.0, z=0.0, size=size)
            elements[guid_a] = Element(
                guid=guid_a,
                type="IfcPipeSegment",
                discipline="MEP",
                geom_ref=guid_a,
                name=f"Bench A {idx}",
                system="BenchA",
                systems=["BenchA"],
                system_group_names=["BenchA"],
            )
        if idx < n_b:
            guid_b = f"B-{idx:06d}"
            guids_b.append(guid_b)
            offset_x = 0.1 if (idx % overlap_every == 0) else 1.0
            bounds_map[guid_b] = _make_bound(guid_b, x=x + offset_x, y=0.0, z=0.0, size=size)
            elements[guid_b] = Element(
                guid=guid_b,
                type="IfcPipeSegment",
                discipline="MEP",
                geom_ref=guid_b,
                name=f"Bench B {idx}",
                system="BenchB",
                systems=["BenchB"],
                system_group_names=["BenchB"],
            )

    return guids_a, guids_b, bounds_map, elements


def _make_bound(element_id: str, *, x: float, y: float, z: float, size: float) -> Bounds:
    minx = float(x)
    miny = float(y)
    minz = float(z)
    maxx = minx + float(size)
    maxy = miny + float(size)
    maxz = minz + float(size)
    return Bounds(
        elementId=str(element_id),
        aabbWorld=(minx, miny, minz, maxx, maxy, maxz),
        aabbLocal=(0.0, 0.0, 0.0, float(size), float(size), float(size)),
        meshVertexCount=8,
        meshCount=1,
        hasRenderableGeometry=True,
    )


def _fps_impact_estimate(pipeline_ms: float) -> Dict[str, float]:
    duration_ms = max(0.0, float(pipeline_ms or 0.0))
    frame_budget_ms = 1000.0 / 60.0
    frames_blocked = duration_ms / frame_budget_ms if frame_budget_ms > 1.0e-9 else 0.0
    fps_if_blocking = 1000.0 / duration_ms if duration_ms > 1.0e-9 else 0.0
    return {
        "frameBudgetMs": float(frame_budget_ms),
        "pipelineMs": float(duration_ms),
        "framesBlocked": float(frames_blocked),
        "fpsIfBlocking": float(fps_if_blocking),
    }


def _memory_mb() -> Optional[float]:
    try:
        import resource  # type: ignore
    except Exception:
        return None
    try:
        rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        return None
    if rss <= 0.0:
        return None
    if sys.platform == "darwin":
        return float(rss / (1024.0 * 1024.0))
    return float(rss / 1024.0)
