from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class ToolbarItemDef:
    id: str
    group: str
    icon: str
    tooltip_title: str
    tooltip_desc: str
    shortcut: str = ""
    is_ai: bool = False
    checkable: bool = False
    checked: bool = False
    action: str = ""


TOOLBAR_GROUP_ORDER: Tuple[str, ...] = (
    "nav",
    "view",
    "select",
    "analyze",
    "issues_ai",
)


# Add future tools by appending here and mapping action handlers in MainWindow._toolbar_action_map.
TOOLBAR_ITEMS: List[ToolbarItemDef] = [
    ToolbarItemDef(
        id="orbit",
        group="nav",
        icon="orbit",
        tooltip_title="Orbit",
        tooltip_desc="Rotate camera around target.",
        shortcut="RMB",
        checkable=True,
        checked=True,
        action="orbit",
    ),
    ToolbarItemDef(
        id="pan",
        group="nav",
        icon="pan",
        tooltip_title="Pan",
        tooltip_desc="Pan camera parallel to view plane.",
        shortcut="Shift+RMB",
        checkable=True,
        action="pan",
    ),
    ToolbarItemDef(
        id="zoom",
        group="nav",
        icon="zoom",
        tooltip_title="Zoom",
        tooltip_desc="Zoom in and out with mouse wheel.",
        shortcut="Wheel",
        checkable=True,
        action="zoom",
    ),
    ToolbarItemDef(
        id="focus",
        group="nav",
        icon="focus",
        tooltip_title="Fit View",
        tooltip_desc="Frame current selection or issue.",
        shortcut="F",
        action="focus",
    ),
    ToolbarItemDef(
        id="transparency",
        group="view",
        icon="transparency",
        tooltip_title="Grid/Transparency",
        tooltip_desc="Toggle transparent overview mode.",
        shortcut="T",
        checkable=True,
        action="transparency",
    ),
    ToolbarItemDef(
        id="isolate",
        group="view",
        icon="isolate",
        tooltip_title="Isolate",
        tooltip_desc="Hide everything except current selection.",
        shortcut="I",
        action="isolate",
    ),
    ToolbarItemDef(
        id="show_all",
        group="view",
        icon="show_all",
        tooltip_title="Show All",
        tooltip_desc="Restore visibility for all elements.",
        shortcut="Shift+I",
        action="show_all",
    ),
    ToolbarItemDef(
        id="measure_select",
        group="select",
        icon="measure_select",
        tooltip_title="Select",
        tooltip_desc="Default selection mode.",
        shortcut="Esc",
        checkable=True,
        checked=True,
        action="measure_select",
    ),
    ToolbarItemDef(
        id="measure_distance",
        group="analyze",
        icon="measure_distance",
        tooltip_title="Measure",
        tooltip_desc="Click two points to measure distance.",
        shortcut="M",
        checkable=True,
        action="measure_distance",
    ),
    ToolbarItemDef(
        id="measure_min",
        group="analyze",
        icon="measure_min",
        tooltip_title="Min Distance",
        tooltip_desc="Measure minimum distance for selected elements.",
        shortcut="Shift+M",
        action="measure_min",
    ),
    ToolbarItemDef(
        id="measure_clearance",
        group="analyze",
        icon="measure_clearance",
        tooltip_title="Clearance",
        tooltip_desc="Measure minimum clearance between two elements.",
        shortcut="Shift+M",
        checkable=True,
        action="measure_clearance",
    ),
    ToolbarItemDef(
        id="section_box",
        group="analyze",
        icon="section_box",
        tooltip_title="Section Box",
        tooltip_desc="Toggle section clipping workspace.",
        shortcut="B",
        checkable=True,
        action="section_box",
    ),
    ToolbarItemDef(
        id="section_fit_selection",
        group="analyze",
        icon="section_fit_selection",
        tooltip_title="Fit Section: Selection",
        tooltip_desc="Fit section box around current selection.",
        action="section_fit_selection",
    ),
    ToolbarItemDef(
        id="section_fit_issue",
        group="analyze",
        icon="section_fit_issue",
        tooltip_title="Fit Section: Issue",
        tooltip_desc="Fit section box around active issue.",
        action="section_fit_issue",
    ),
    ToolbarItemDef(
        id="section_reset",
        group="analyze",
        icon="section_reset",
        tooltip_title="Reset Section",
        tooltip_desc="Reset section box to full scene.",
        action="section_reset",
    ),
    ToolbarItemDef(
        id="detect_clashes",
        group="issues_ai",
        icon="detect_clashes",
        tooltip_title="Issues",
        tooltip_desc="Run clash detection for active search scope.",
        shortcut="Ctrl+D",
        action="detect_clashes",
    ),
    ToolbarItemDef(
        id="generate_issues",
        group="issues_ai",
        icon="generate_issues",
        tooltip_title="Generate Issues",
        tooltip_desc="Create issue list from detected clashes.",
        shortcut="Ctrl+G",
        is_ai=True,
        action="generate_issues",
    ),
    ToolbarItemDef(
        id="preview_fix",
        group="issues_ai",
        icon="preview_fix",
        tooltip_title="Preview Fix",
        tooltip_desc="Show virtual before/after fix overlay.",
        is_ai=True,
        action="preview_fix",
    ),
    ToolbarItemDef(
        id="generate_fixes",
        group="issues_ai",
        icon="generate_fixes",
        tooltip_title="Generate Fixes",
        tooltip_desc="Generate AI fix candidates for selected issue.",
        is_ai=True,
        action="generate_fixes",
    ),
    ToolbarItemDef(
        id="help",
        group="issues_ai",
        icon="help",
        tooltip_title="Tool Help",
        tooltip_desc="Open tool cheat sheet.",
        shortcut="?",
        action="help",
    ),
]
