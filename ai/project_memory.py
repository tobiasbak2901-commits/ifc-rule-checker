from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


MEMORY_DIR = ".ponker"
MEMORY_FILE = "memory.json"


def _memory_path(project_root: Path) -> Path:
    return project_root / MEMORY_DIR / MEMORY_FILE


def load_memory(project_root: Path) -> Dict[str, Any]:
    path = _memory_path(project_root)
    if not path.exists():
        return {"project_id": "", "notes": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"project_id": "", "notes": []}
    if not isinstance(raw, dict):
        return {"project_id": "", "notes": []}
    notes = raw.get("notes")
    if not isinstance(notes, list):
        notes = []
    return {"project_id": str(raw.get("project_id") or ""), "notes": list(notes)}


def save_note(
    project_root: Path,
    *,
    project_id: str,
    scope: str,
    text: str,
    tags: Optional[List[str]] = None,
    source_issue_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = load_memory(project_root)
    existing_project_id = str(payload.get("project_id") or "").strip()
    effective_project_id = str(project_id or existing_project_id or "ponker-project").strip()
    notes = list(payload.get("notes") or [])
    note = {
        "id": f"note-{uuid.uuid4().hex[:10]}",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": str(scope or "project").strip() or "project",
        "text": str(text or "").strip(),
        "tags": [str(tag).strip() for tag in list(tags or []) if str(tag).strip()],
        "source_issue_id": str(source_issue_id).strip() if source_issue_id else None,
    }
    notes.append(note)
    out = {"project_id": effective_project_id, "notes": notes}
    path = _memory_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    return note


def relevant_notes(project_root: Path, tags: List[str], limit: int = 3) -> List[Dict[str, Any]]:
    payload = load_memory(project_root)
    notes = [item for item in list(payload.get("notes") or []) if isinstance(item, dict)]
    wanted = {str(tag).strip().lower() for tag in tags if str(tag).strip()}

    def _sort_key(note: Dict[str, Any]) -> str:
        return str(note.get("created_at") or "")

    notes.sort(key=_sort_key, reverse=True)
    if not wanted:
        return notes[:limit]

    picked: List[Dict[str, Any]] = []
    fallback: List[Dict[str, Any]] = []
    for note in notes:
        note_tags = {
            str(tag).strip().lower()
            for tag in list(note.get("tags") or [])
            if str(tag).strip()
        }
        if note_tags & wanted:
            picked.append(note)
        else:
            fallback.append(note)
    if len(picked) < limit:
        picked.extend(fallback[: max(0, limit - len(picked))])
    return picked[:limit]
