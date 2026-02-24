from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from models import Element


@dataclass
class ObjectIndexItem:
    elementId: str
    globalId: str
    name: str
    type: str
    ifcType: str
    systemGroup: str
    sourceFileId: str
    sourceFileName: str
    flattenedProperties: Dict[str, str] = field(default_factory=dict)
    searchableText: str = ""


class ObjectIndex:
    """Flat searchable index for Find Objects."""

    def __init__(self) -> None:
        self.items: List[ObjectIndexItem] = []
        self._by_element_id: Dict[str, ObjectIndexItem] = {}
        self._by_global_id: Dict[str, ObjectIndexItem] = {}

    @property
    def count(self) -> int:
        return len(self.items)

    def clear(self) -> None:
        self.items = []
        self._by_element_id = {}
        self._by_global_id = {}

    def rebuild(
        self,
        elements: Mapping[str, Element],
        *,
        source_path: str = "",
        model_key: str = "",
    ) -> None:
        next_items: List[ObjectIndexItem] = []
        next_map: Dict[str, ObjectIndexItem] = {}
        by_global: Dict[str, ObjectIndexItem] = {}
        fallback_source_name = Path(str(source_path or "")).name if str(source_path or "").strip() else "Model file"
        fallback_source_id = str(model_key or "").strip() or fallback_source_name

        for guid, elem in dict(elements or {}).items():
            if elem is None:
                continue
            meta = dict(getattr(elem, "ifc_meta", {}) or {})
            global_id = str(getattr(elem, "guid", "") or str(guid or "")).strip()
            element_id = str(meta.get("elementKey") or global_id or guid or "").strip()
            if not element_id:
                continue

            source_file_name = self._source_file_name(meta, fallback_source_name)
            source_file_id = self._source_file_id(meta, fallback_source_id, source_file_name)
            flattened = self._flatten_properties(elem, meta)
            item = ObjectIndexItem(
                elementId=element_id,
                globalId=global_id,
                name=str(getattr(elem, "name", "") or "").strip(),
                type=str(getattr(elem, "type", "") or "").strip(),
                ifcType=str(getattr(elem, "type", "") or "").strip(),
                systemGroup=self._system_group(elem, meta),
                sourceFileId=source_file_id,
                sourceFileName=source_file_name,
                flattenedProperties=flattened,
            )
            item.searchableText = self._build_searchable_text(item, flattened)
            next_items.append(item)
            next_map[element_id] = item
            if global_id:
                by_global[global_id] = item

        self.items = next_items
        self._by_element_id = next_map
        self._by_global_id = by_global

    def item_for_element_id(self, element_id: str) -> Optional[ObjectIndexItem]:
        key = str(element_id or "").strip()
        if not key:
            return None
        return self._by_element_id.get(key)

    def item_for_global_id(self, global_id: str) -> Optional[ObjectIndexItem]:
        key = str(global_id or "").strip()
        if not key:
            return None
        return self._by_global_id.get(key)

    @staticmethod
    def _source_file_name(meta: Dict[str, object], fallback_name: str) -> str:
        for key in (
            "sourceFileName",
            "source_file_name",
            "sourceFile",
            "source_file",
            "modelFile",
            "model_file",
            "ifc_file",
            "ifcFile",
            "file",
        ):
            raw = str(meta.get(key) or "").strip()
            if raw:
                return Path(raw).name or raw
        return str(fallback_name or "Model file")

    @staticmethod
    def _source_file_id(meta: Dict[str, object], fallback_id: str, source_file_name: str) -> str:
        for key in (
            "sourceFileId",
            "source_file_id",
            "modelId",
            "model_id",
            "modelKey",
            "model_key",
            "sourceFile",
            "source_file",
            "modelFile",
            "model_file",
            "ifc_file",
            "ifcFile",
        ):
            raw = str(meta.get(key) or "").strip()
            if raw:
                return raw
        return str(fallback_id or source_file_name or "model")

    @staticmethod
    def _system_group(elem: Element, meta: Dict[str, object]) -> str:
        for key in ("system_groups", "systems"):
            values = meta.get(key)
            if isinstance(values, list):
                for value in values:
                    text = str(value or "").strip()
                    if text:
                        return text
        for value in list(getattr(elem, "systems", []) or []):
            text = str(value or "").strip()
            if text:
                return text
        for value in list(getattr(elem, "system_group_names", []) or []):
            text = str(value or "").strip()
            if text:
                return text
        return str(getattr(elem, "system", "") or "").strip()

    @staticmethod
    def _flatten_properties(elem: Element, meta: Dict[str, object]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        pools = [
            ("pset", getattr(elem, "psets", None)),
            ("qto", getattr(elem, "qtos", None)),
            ("type_pset", getattr(elem, "type_psets", None)),
            ("type_qto", getattr(elem, "type_qtos", None)),
            ("meta_pset", meta.get("psets")),
            ("meta_qto", meta.get("qtos")),
            ("meta_type_pset", meta.get("type_psets")),
            ("meta_type_qto", meta.get("type_qtos")),
        ]
        for prefix, pool in pools:
            if not isinstance(pool, dict):
                continue
            for set_name, props in pool.items():
                set_label = str(set_name or "").strip() or "set"
                if not isinstance(props, dict):
                    continue
                for prop_name, value in props.items():
                    key = f"{prefix}.{set_label}.{str(prop_name or '').strip()}"
                    if not key.strip().endswith("."):
                        out[key] = ObjectIndex._stringify(value)
        return out

    @staticmethod
    def _stringify(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _build_searchable_text(item: ObjectIndexItem, flattened: Dict[str, str]) -> str:
        parts: List[str] = [
            str(item.elementId or ""),
            str(item.globalId or ""),
            str(item.name or ""),
            str(item.type or ""),
            str(item.ifcType or ""),
            str(item.systemGroup or ""),
            str(item.sourceFileId or ""),
            str(item.sourceFileName or ""),
        ]
        for key, value in dict(flattened or {}).items():
            parts.append(str(key or ""))
            parts.append(str(value or ""))
        return " ".join(part for part in parts if str(part).strip()).lower()
