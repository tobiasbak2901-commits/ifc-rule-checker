from pathlib import Path

from ai.context_builder import build_context


class _RulePackStub:
    generated_rules = []
    utility_rules = []


def test_context_builder_only_keeps_standard_refs_from_registry(tmp_path: Path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir(parents=True, exist_ok=True)
    registry_path = standards_dir / "registry.yaml"
    registry_path.write_text(
        """
sources:
  - id: DS475#5.3
    title: DS 475 section 5.3
    doc_file: standards/ds475_excerpt.md
    excerpt: Sample excerpt
""".strip()
        + "\n",
        encoding="utf-8",
    )

    app_state = {
        "project_root": str(tmp_path),
        "project_id": "demo-project",
        "standards_registry_path": str(registry_path),
        "active_mode": "Analyze",
        "camera": {},
        "selection": [],
        "classification_summary": [],
        "rules_fired": [
            {
                "rule_id": "SEARCH_SET_CLASH",
                "status": "fired",
                "reason": "Rule fired",
                "trace_steps": ["step1"],
                "standard_refs": ["DS475#5.3", "FAKE#404"],
            }
        ],
        "rulepack": _RulePackStub(),
        "fix_availability": {"status": "AVAILABLE", "reasons": []},
    }

    context = build_context(app_state)

    assert [ref.id for ref in context.standard_refs] == ["DS475#5.3"]
    assert context.rules_fired[0].standard_refs == ["DS475#5.3"]
