from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clash_tests.benchmark import format_clash_benchmark, run_clash_benchmark


def test_clash_benchmark_returns_timings_and_counts():
    report = run_clash_benchmark(scenarios=[("tiny", 40)])
    assert len(report.scenarios) == 1
    scenario = report.scenarios[0]
    assert scenario.name == "tiny"
    assert scenario.counts["elementsA"] > 0
    assert scenario.counts["elementsB"] > 0
    assert "buildProxies" in scenario.timings_ms
    assert "broadphase" in scenario.timings_ms
    assert "narrowphase" in scenario.timings_ms
    assert "grouping" in scenario.timings_ms
    assert "total" in scenario.timings_ms
    assert "total" in scenario.timings_ms_second_run
    assert "proxiesBuilt" in scenario.counts_second_run
    assert float(scenario.speedup_second_run) > 1.0
    assert int(scenario.counts_second_run.get("changedElements") or 0) == 0
    brute_force = int(scenario.counts["elementsA"]) * int(scenario.counts["elementsB"])
    assert int(scenario.counts["candidates"]) < brute_force


def test_clash_benchmark_formatter_includes_required_fields():
    report = run_clash_benchmark(scenarios=[("tiny", 40)])
    text = format_clash_benchmark(report)
    assert "Clash benchmark - simpel log" in text
    assert "Scenarier:" in text
    assert "Samlet tid:" in text
    assert "Tid:" in text
    assert "Tid (2. koersel):" in text
    assert "Speedup (2. koersel):" in text
    assert "FPS antal (estimat):" in text
    assert "Elementer A:" in text
    assert "Elementer B:" in text
    assert "Proxies bygget:" in text
    assert "Aendrede elementer (2. koersel):" in text
    assert "Kandidater:" in text
    assert "Bekraeftede clashes:" in text
    assert "Byg proxies:" in text
    assert "Grovfase:" in text
    assert "Smalfase:" in text
    assert "Gruppering:" in text
