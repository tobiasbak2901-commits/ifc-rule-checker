from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Tuple


@dataclass(frozen=True)
class WorkspaceConfig:
    key: str
    label: str
    panels: Mapping[str, bool]
    focus_panel: str = ""
    object_tree_view: str = ""
    object_tree_tab: str = ""
    clash_step: str = ""


class WorkspaceManager:
    def __init__(self) -> None:
        self._aliases: Dict[str, str] = {
            "project": "Project",
            "model": "Model",
            "inspect": "Model",
            "analyze": "Analyze",
            "issues": "Issues",
            "decisions": "Issues",
        }
        self._ordered_keys: Tuple[str, ...] = ("Project", "Model", "Analyze", "Issues")
        self._configs: Dict[str, WorkspaceConfig] = {
            "Project": WorkspaceConfig(
                key="Project",
                label="Project",
                panels={
                    "objectTree": False,
                    "searchSets": True,
                    "findObjects": True,
                    "clash": False,
                    "issues": False,
                    "properties": False,
                    "ai": False,
                },
                focus_panel="searchSets",
            ),
            "Model": WorkspaceConfig(
                key="Model",
                label="Model",
                panels={
                    "objectTree": True,
                    "searchSets": False,
                    "findObjects": False,
                    "clash": False,
                    "issues": False,
                    "properties": True,
                    "ai": False,
                },
                focus_panel="objectTree",
                object_tree_view="by_file",
                object_tree_tab="tree",
            ),
            "Analyze": WorkspaceConfig(
                key="Analyze",
                label="Analyze",
                panels={
                    "objectTree": True,
                    "searchSets": False,
                    "findObjects": False,
                    "clash": True,
                    "issues": False,
                    "properties": False,
                    "ai": False,
                },
                focus_panel="clash",
                object_tree_view="ai",
                object_tree_tab="tree",
                clash_step="setup",
            ),
            "Issues": WorkspaceConfig(
                key="Issues",
                label="Issues",
                panels={
                    "objectTree": False,
                    "searchSets": False,
                    "findObjects": False,
                    "clash": True,
                    "issues": True,
                    "properties": False,
                    "ai": False,
                },
                focus_panel="issues",
                clash_step="issues",
            ),
        }

    def normalize(self, workspace: str) -> str:
        raw = str(workspace or "").strip().lower()
        if not raw:
            return "Analyze"
        return self._aliases.get(raw, "Analyze")

    def config_for(self, workspace: str) -> WorkspaceConfig:
        return self._configs[self.normalize(workspace)]

    def ordered_tabs(self) -> Tuple[Tuple[str, str], ...]:
        return tuple((key, self._configs[key].label) for key in self._ordered_keys)
