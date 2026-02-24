from pathlib import Path


def test_ifc_section_uses_collapsible_pset_subrows_with_counts():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _build_ifc_section_rows(" in source
    assert "def _ifc_subsection_row(" in source
    assert "\"label\": f\"{str(title or 'Property Set')} ({len(detail_rows)})\"" in source
    assert "if normalized.startswith(\"pset:\")" in source
    assert "kind = \"Type Pset\" if normalized.startswith(\"pset:type:\") else \"Pset\"" in source
    assert "ifc_rows = self._build_ifc_section_rows(groups, group_order)" in source


def test_ifc_search_includes_nested_property_labels_and_values():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _inspect_row_matches_needle(" in source
    assert "for detail_label, detail_value, detail_source_group, detail_source_key in list(details or []):" in source
    assert "matches, matched_details = self._inspect_row_matches_needle(" in source
    assert "effective_detail_rows = list(matched_details if needle else cleaned_detail_rows)" in source


def test_ifc_section_uses_lazy_detail_materialization_for_performance():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "lazy_detail_rows = bool(group_key == \"ifc\")" in source
    assert "if lazy_detail_rows:" in source
    assert "rows_layout.insertWidget(insert_at, detail_widget, 0)" in source


def test_legacy_ifc_mini_table_calls_removed_from_inspect_refresh():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._populate_ifc_inspector(None)" not in source
    assert "self._populate_ifc_inspector(elem)" not in source
