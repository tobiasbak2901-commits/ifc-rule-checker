from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Set

from PySide6 import QtCore


class CurrentSelectionStore(QtCore.QObject):
    """Shared selection state between Object Tree, Find Objects, and host UI."""

    changed = QtCore.Signal(object)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.selectedIds: Set[str] = set()
        self.selectedMeta: Dict[str, Dict[str, str]] = {}
        self._ordered_ids: List[str] = []
        self.selectedObjectTreeNodeIds: Set[str] = set()
        self.selectedObjectTreeNodeMeta: Dict[str, Dict[str, str]] = {}
        self._ordered_tree_node_ids: List[str] = []
        self.selected3dElementIds: Set[str] = set()
        self._ordered_3d_element_ids: List[str] = []

    @staticmethod
    def _normalize_ids(ids: Sequence[str]) -> List[str]:
        normalized: List[str] = []
        for value in list(ids or []):
            key = str(value or "").strip()
            if not key or key in normalized:
                continue
            normalized.append(key)
        return normalized

    @staticmethod
    def _normalize_meta_entry(entry: object) -> Dict[str, str]:
        if not isinstance(entry, Mapping):
            return {}
        out: Dict[str, str] = {}
        for source_key, target_key in (
            ("name", "name"),
            ("type", "type"),
            ("modelKey", "modelKey"),
            ("file", "file"),
        ):
            text = str(entry.get(source_key) or "").strip()
            if text:
                out[target_key] = text
        return out

    def _emit_changed(self) -> None:
        self.changed.emit(
            {
                "selectedIds": set(self.selectedIds),
                "selectedMeta": dict(self.selectedMeta),
                "selectedObjectTreeNodeIds": set(self.selectedObjectTreeNodeIds),
                "selectedObjectTreeNodeMeta": dict(self.selectedObjectTreeNodeMeta),
                "selected3dElementIds": set(self.selected3dElementIds),
            }
        )

    def setSelection(
        self,
        ids: Sequence[str],
        selected_meta: Optional[Mapping[str, Mapping[str, object]]] = None,
    ) -> bool:
        ordered = self._normalize_ids(ids)
        normalized_set = set(ordered)
        next_meta: Dict[str, Dict[str, str]] = {}
        if isinstance(selected_meta, Mapping):
            for key in ordered:
                entry = self._normalize_meta_entry(selected_meta.get(key))
                if entry:
                    next_meta[key] = entry
        else:
            for key in ordered:
                existing = dict(self.selectedMeta.get(key) or {})
                if existing:
                    next_meta[key] = existing

        changed = (
            ordered != self._ordered_ids
            or normalized_set != self.selectedIds
            or next_meta != self.selectedMeta
        )
        self._ordered_ids = list(ordered)
        self.selectedIds = normalized_set
        self.selectedMeta = next_meta
        if changed:
            self._emit_changed()
        return changed

    def toggle(
        self,
        element_id: str,
        *,
        meta: Optional[Mapping[str, object]] = None,
    ) -> bool:
        key = str(element_id or "").strip()
        if not key:
            return False
        next_order = list(self._ordered_ids)
        next_meta = dict(self.selectedMeta or {})
        if key in self.selectedIds:
            next_order = [current for current in next_order if current != key]
            next_meta.pop(key, None)
            return self.setSelection(next_order, selected_meta=next_meta)
        next_order.append(key)
        if meta is not None:
            entry = self._normalize_meta_entry(meta)
            if entry:
                next_meta[key] = entry
        return self.setSelection(next_order, selected_meta=next_meta)

    def clear(self) -> bool:
        return self.setSelection([])

    def getSelectionArray(self) -> List[str]:
        return list(self._ordered_ids)

    def setObjectTreeSelection(self, nodes: Sequence[Mapping[str, object]]) -> bool:
        ordered_ids: List[str] = []
        next_meta: Dict[str, Dict[str, str]] = {}
        for row in list(nodes or []):
            if not isinstance(row, Mapping):
                continue
            node_id = str(row.get("id") or row.get("nodeId") or "").strip()
            if not node_id or node_id in ordered_ids:
                continue
            ordered_ids.append(node_id)
            node_type = str(row.get("type") or row.get("kind") or "").strip().lower()
            if node_type not in {"file", "system", "group", "element"}:
                node_type = "group"
            label = str(row.get("label") or "").strip()
            entry: Dict[str, str] = {"type": node_type}
            if label:
                entry["label"] = label
            next_meta[node_id] = entry
        normalized_set = set(ordered_ids)
        changed = (
            ordered_ids != self._ordered_tree_node_ids
            or normalized_set != self.selectedObjectTreeNodeIds
            or next_meta != self.selectedObjectTreeNodeMeta
        )
        self._ordered_tree_node_ids = list(ordered_ids)
        self.selectedObjectTreeNodeIds = normalized_set
        self.selectedObjectTreeNodeMeta = next_meta
        if changed:
            self._emit_changed()
        return changed

    def getObjectTreeSelectionArray(self) -> List[str]:
        return list(self._ordered_tree_node_ids)

    def set3dSelection(self, ids: Sequence[str]) -> bool:
        ordered = self._normalize_ids(ids)
        normalized_set = set(ordered)
        changed = ordered != self._ordered_3d_element_ids or normalized_set != self.selected3dElementIds
        self._ordered_3d_element_ids = list(ordered)
        self.selected3dElementIds = normalized_set
        if changed:
            self._emit_changed()
        return changed

    def get3dSelectionArray(self) -> List[str]:
        return list(self._ordered_3d_element_ids)
