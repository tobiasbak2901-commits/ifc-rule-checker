from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .models import ClashGroup, ClashResult, ClashResultStatus, ClashTest, ClashType, IgnoreRule, SearchSet, Viewpoint


class ClashTestStore:
    SCHEMA_VERSION = 1

    def __init__(self, project_root: Path):
        self._project_root = Path(project_root)
        self._path = self._project_root / ".ponker" / "clash_tests.db"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS clash_tests (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    clash_type TEXT NOT NULL,
                    threshold_mm REAL NOT NULL,
                    search_set_ids_a TEXT NOT NULL,
                    search_set_ids_b TEXT NOT NULL,
                    grouping_order TEXT NOT NULL,
                    proximity_meters REAL NOT NULL,
                    auto_viewpoint INTEGER NOT NULL,
                    auto_screenshot INTEGER NOT NULL,
                    created_ts REAL NOT NULL,
                    updated_ts REAL NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS search_sets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    query_json TEXT NOT NULL,
                    manual_guids_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    updated_ts REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ignore_rules (
                    test_id TEXT NOT NULL,
                    rule_key TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    params_json TEXT NOT NULL,
                    PRIMARY KEY (test_id, rule_key)
                );

                CREATE TABLE IF NOT EXISTS clash_groups (
                    id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    elementA_key TEXT NOT NULL,
                    proximity_cell TEXT NOT NULL,
                    level_id TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    result_ids_json TEXT NOT NULL,
                    created_ts REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clash_results (
                    id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    elementA_id TEXT NOT NULL,
                    elementB_id TEXT NOT NULL,
                    elementA_guid TEXT,
                    elementB_guid TEXT,
                    rule_triggered TEXT NOT NULL,
                    min_distance_m REAL NOT NULL,
                    penetration_depth_m REAL NOT NULL,
                    method TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    level_id TEXT NOT NULL,
                    proximity_cell TEXT NOT NULL,
                    elementA_key TEXT NOT NULL,
                    clash_key TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    assignee TEXT,
                    tags_json TEXT NOT NULL,
                    group_id TEXT,
                    group_name TEXT,
                    clash_name TEXT,
                    midpoint_x REAL,
                    midpoint_y REAL,
                    midpoint_z REAL,
                    first_seen_ts REAL,
                    last_seen_ts REAL,
                    reopen_count INTEGER NOT NULL DEFAULT 0,
                    diagnostics_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS issue_views (
                    id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    result_id TEXT NOT NULL,
                    camera_json TEXT NOT NULL,
                    screenshot_path TEXT,
                    screenshot_status TEXT NOT NULL,
                    created_ts REAL NOT NULL
                );
                """
            )
            self._ensure_column(conn, "clash_results", "clash_key", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "clash_results", "first_seen_ts", "REAL")
            self._ensure_column(conn, "clash_results", "last_seen_ts", "REAL")
            self._ensure_column(conn, "clash_results", "reopen_count", "INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_clash_results_test_clash_key ON clash_results(test_id, clash_key)"
            )

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
        rows = list(conn.execute(f"PRAGMA table_info({table})"))
        return [str(row["name"]) for row in rows]

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, spec: str) -> None:
        columns = set(self._table_columns(conn, table))
        if str(column) in columns:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")

    def upsert_search_sets(self, search_sets: Sequence[Any]) -> None:
        rows: List[SearchSet] = []
        now = float(time.time())
        for item in list(search_sets or []):
            rows.append(
                SearchSet(
                    id=str(getattr(item, "id", "") or ""),
                    name=str(getattr(item, "name", "") or ""),
                    query=list(getattr(item, "query", []) or []),
                    manual_guids=[str(v) for v in list(getattr(item, "manual_guids", []) or []) if v],
                    enabled=bool(getattr(item, "enabled", True)),
                )
            )
        with self._connect() as conn:
            for row in rows:
                if not row.id:
                    continue
                conn.execute(
                    """
                    INSERT INTO search_sets(id, name, query_json, manual_guids_json, enabled, updated_ts)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        query_json=excluded.query_json,
                        manual_guids_json=excluded.manual_guids_json,
                        enabled=excluded.enabled,
                        updated_ts=excluded.updated_ts
                    """,
                    (
                        row.id,
                        row.name,
                        json.dumps(list(row.query or []), ensure_ascii=True),
                        json.dumps(list(row.manual_guids or []), ensure_ascii=True),
                        int(bool(row.enabled)),
                        now,
                    ),
                )

    def list_tests(self) -> List[ClashTest]:
        with self._connect() as conn:
            rows = list(conn.execute("SELECT * FROM clash_tests ORDER BY name COLLATE NOCASE"))
            return [self._row_to_test(conn, row) for row in rows]

    def get_test(self, test_id: str) -> Optional[ClashTest]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM clash_tests WHERE id = ?", (str(test_id),)).fetchone()
            if row is None:
                return None
            return self._row_to_test(conn, row)

    def get_active_test(self) -> Optional[ClashTest]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM clash_tests WHERE is_active = 1 ORDER BY updated_ts DESC LIMIT 1").fetchone()
            if row is None:
                return None
            return self._row_to_test(conn, row)

    def save_test(self, test: ClashTest, *, set_active: bool = False) -> ClashTest:
        test.updated_ts = float(time.time())
        if not test.created_ts:
            test.created_ts = test.updated_ts

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clash_tests(
                    id, name, clash_type, threshold_mm, search_set_ids_a, search_set_ids_b,
                    grouping_order, proximity_meters, auto_viewpoint, auto_screenshot,
                    created_ts, updated_ts, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    clash_type=excluded.clash_type,
                    threshold_mm=excluded.threshold_mm,
                    search_set_ids_a=excluded.search_set_ids_a,
                    search_set_ids_b=excluded.search_set_ids_b,
                    grouping_order=excluded.grouping_order,
                    proximity_meters=excluded.proximity_meters,
                    auto_viewpoint=excluded.auto_viewpoint,
                    auto_screenshot=excluded.auto_screenshot,
                    updated_ts=excluded.updated_ts,
                    is_active=excluded.is_active
                """,
                (
                    str(test.id),
                    str(test.name),
                    str(test.clash_type.value),
                    float(test.threshold_mm or 0.0),
                    json.dumps(list(test.search_set_ids_a or []), ensure_ascii=True),
                    json.dumps(list(test.search_set_ids_b or []), ensure_ascii=True),
                    json.dumps(list(test.grouping_order or []), ensure_ascii=True),
                    float(test.proximity_meters or 6.0),
                    int(bool(test.auto_viewpoint)),
                    int(bool(test.auto_screenshot)),
                    float(test.created_ts),
                    float(test.updated_ts),
                    int(bool(set_active)),
                ),
            )

            conn.execute("DELETE FROM ignore_rules WHERE test_id = ?", (str(test.id),))
            for rule in list(test.ignore_rules or []):
                conn.execute(
                    "INSERT INTO ignore_rules(test_id, rule_key, enabled, params_json) VALUES(?, ?, ?, ?)",
                    (
                        str(test.id),
                        str(rule.key),
                        int(bool(rule.enabled)),
                        json.dumps(dict(rule.params or {}), ensure_ascii=True),
                    ),
                )

            if set_active:
                conn.execute("UPDATE clash_tests SET is_active = 0 WHERE id <> ?", (str(test.id),))

        return test

    def set_active_test(self, test_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE clash_tests SET is_active = CASE WHEN id = ? THEN 1 ELSE 0 END", (str(test_id),))

    def ensure_default_test(self, *, search_set_ids: Sequence[str], level_available: bool) -> ClashTest:
        active = self.get_active_test()
        if active is not None:
            return active

        from .models import (
            GROUP_ELEMENT_A,
            GROUP_LEVEL,
            GROUP_PROXIMITY,
            IGNORE_IFCTYPE_IN,
            IGNORE_NAME_PATTERN,
            IGNORE_SAME_ELEMENT,
            IGNORE_SAME_FILE,
            IGNORE_SAME_SYSTEM,
        )

        grouping = [GROUP_ELEMENT_A, GROUP_PROXIMITY]
        if level_available:
            grouping.append(GROUP_LEVEL)
        test = ClashTest(
            id="default",
            name="Default Clash Test",
            search_set_ids_a=[str(v) for v in list(search_set_ids or []) if v],
            search_set_ids_b=[str(v) for v in list(search_set_ids or []) if v],
            clash_type=ClashType.HARD,
            threshold_mm=0.0,
            ignore_rules=[
                IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True),
                IgnoreRule(key=IGNORE_SAME_SYSTEM, enabled=False),
                IgnoreRule(key=IGNORE_SAME_FILE, enabled=False),
                IgnoreRule(key=IGNORE_NAME_PATTERN, enabled=False, params={"patterns": []}),
                IgnoreRule(key=IGNORE_IFCTYPE_IN, enabled=False, params={"types": []}),
            ],
            grouping_order=grouping,
            proximity_meters=6.0,
            auto_viewpoint=True,
            auto_screenshot=False,
        )
        return self.save_test(test, set_active=True)

    def replace_results_for_test(
        self,
        *,
        test_id: str,
        results: Sequence[ClashResult],
        groups: Sequence[ClashGroup],
        viewpoints: Sequence[Viewpoint],
    ) -> Dict[str, Dict[str, Any]]:
        tid = str(test_id)
        persisted: Dict[str, Dict[str, Any]] = {}
        result_id_map: Dict[str, str] = {}
        with self._connect() as conn:
            conn.execute("DELETE FROM clash_groups WHERE test_id = ?", (tid,))
            conn.execute("DELETE FROM issue_views WHERE test_id = ?", (tid,))
            existing_rows = list(
                conn.execute(
                    """
                    SELECT
                        id,
                        clash_key,
                        status,
                        assignee,
                        tags_json,
                        first_seen_ts,
                        last_seen_ts,
                        reopen_count,
                        diagnostics_json
                    FROM clash_results
                    WHERE test_id = ?
                    """,
                    (tid,),
                )
            )
            existing_by_key: Dict[str, sqlite3.Row] = {}
            for row in existing_rows:
                row_id = str(row["id"] or "").strip()
                clash_key = str(row["clash_key"] or "").strip()
                if clash_key and clash_key not in existing_by_key:
                    existing_by_key[clash_key] = row
                if row_id and row_id not in existing_by_key:
                    existing_by_key[row_id] = row

            for group in list(groups or []):
                conn.execute(
                    """
                    INSERT INTO clash_groups(
                        id, test_id, name, elementA_key, proximity_cell, level_id,
                        result_count, result_ids_json, created_ts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(group.id),
                        tid,
                        str(group.name),
                        str(group.elementA_key),
                        str(group.proximity_cell),
                        str(group.level_id),
                        int(len(group.result_ids)),
                        json.dumps(list(group.result_ids or []), ensure_ascii=True),
                        float(group.created_ts),
                    ),
                )

            for result in list(results or []):
                original_result_id = str(result.id or "").strip()
                midpoint = tuple(result.clash_midpoint or ())
                clash_key = str(result.clash_key or result.id or "").strip()
                if not clash_key:
                    clash_key = str(result.id or f"{result.elementA_id}|{result.elementB_id}|{result.timestamp}")
                existing = existing_by_key.get(clash_key)
                status_raw = str(getattr(result.status, "value", result.status) or ClashResultStatus.NEW.value).strip().lower()
                now_ts = float(result.timestamp or time.time())
                first_seen = now_ts
                last_seen = now_ts
                reopen_count = int(result.reopen_count or 0)
                reopened = False
                assignee = str(result.assignee) if result.assignee else None
                tags = list(result.tags or [])
                row_id = str(result.id or clash_key)
                if existing is not None:
                    existing_status = str(existing["status"] or "").strip().lower()
                    first_seen = float(existing["first_seen_ts"] or now_ts)
                    last_seen = now_ts
                    reopen_count = int(existing["reopen_count"] or 0)
                    if existing_status in {"closed", "resolved"}:
                        reopened = True
                        reopen_count += 1
                        status_raw = ClashResultStatus.NEW.value
                    else:
                        status_raw = existing_status or status_raw
                    row_id = str(existing["id"] or row_id or clash_key)
                    existing_assignee = str(existing["assignee"] or "").strip()
                    if existing_assignee:
                        assignee = existing_assignee
                    tags = self._json_list(existing["tags_json"]) or list(tags)
                diagnostics = dict(result.diagnostics or {})
                existing_diag = self._json_dict(existing["diagnostics_json"]) if existing is not None else {}
                existing_comments = list(existing_diag.get("comments") or [])
                if existing_comments and not list(diagnostics.get("comments") or []):
                    diagnostics["comments"] = existing_comments
                lifecycle = dict(diagnostics.get("lifecycle") or {})
                lifecycle.update(
                    {
                        "clashKey": str(clash_key),
                        "firstSeenAt": float(first_seen),
                        "lastSeenAt": float(last_seen),
                        "reopened": bool(reopened),
                        "reopenCount": int(reopen_count),
                    }
                )
                diagnostics["lifecycle"] = lifecycle
                diagnostics_json = json.dumps(diagnostics, ensure_ascii=True)
                if existing is not None:
                    conn.execute(
                        """
                        UPDATE clash_results
                        SET
                            elementA_id = ?,
                            elementB_id = ?,
                            elementA_guid = ?,
                            elementB_guid = ?,
                            rule_triggered = ?,
                            min_distance_m = ?,
                            penetration_depth_m = ?,
                            method = ?,
                            timestamp = ?,
                            level_id = ?,
                            proximity_cell = ?,
                            elementA_key = ?,
                            clash_key = ?,
                            status = ?,
                            assignee = ?,
                            tags_json = ?,
                            group_id = ?,
                            group_name = ?,
                            clash_name = ?,
                            midpoint_x = ?,
                            midpoint_y = ?,
                            midpoint_z = ?,
                            first_seen_ts = ?,
                            last_seen_ts = ?,
                            reopen_count = ?,
                            diagnostics_json = ?
                        WHERE id = ?
                        """,
                        (
                            str(result.elementA_id),
                            str(result.elementB_id),
                            str(result.elementA_guid) if result.elementA_guid else None,
                            str(result.elementB_guid) if result.elementB_guid else None,
                            str(result.rule_triggered),
                            float(result.min_distance_m),
                            float(result.penetration_depth_m),
                            str(result.method),
                            float(now_ts),
                            str(result.level_id),
                            str(result.proximity_cell),
                            str(result.elementA_key),
                            str(clash_key),
                            str(status_raw),
                            assignee,
                            json.dumps(list(tags or []), ensure_ascii=True),
                            str(result.group_id) if result.group_id else None,
                            str(result.group_name) if result.group_name else None,
                            str(result.clash_name) if result.clash_name else None,
                            float(midpoint[0]) if len(midpoint) == 3 else None,
                            float(midpoint[1]) if len(midpoint) == 3 else None,
                            float(midpoint[2]) if len(midpoint) == 3 else None,
                            float(first_seen),
                            float(last_seen),
                            int(reopen_count),
                            diagnostics_json,
                            str(row_id),
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO clash_results(
                            id, test_id, elementA_id, elementB_id, elementA_guid, elementB_guid,
                            rule_triggered, min_distance_m, penetration_depth_m, method, timestamp,
                            level_id, proximity_cell, elementA_key, clash_key, status, assignee, tags_json,
                            group_id, group_name, clash_name, midpoint_x, midpoint_y, midpoint_z,
                            first_seen_ts, last_seen_ts, reopen_count, diagnostics_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(row_id),
                            tid,
                            str(result.elementA_id),
                            str(result.elementB_id),
                            str(result.elementA_guid) if result.elementA_guid else None,
                            str(result.elementB_guid) if result.elementB_guid else None,
                            str(result.rule_triggered),
                            float(result.min_distance_m),
                            float(result.penetration_depth_m),
                            str(result.method),
                            float(now_ts),
                            str(result.level_id),
                            str(result.proximity_cell),
                            str(result.elementA_key),
                            str(clash_key),
                            str(status_raw),
                            assignee,
                            json.dumps(list(tags or []), ensure_ascii=True),
                            str(result.group_id) if result.group_id else None,
                            str(result.group_name) if result.group_name else None,
                            str(result.clash_name) if result.clash_name else None,
                            float(midpoint[0]) if len(midpoint) == 3 else None,
                            float(midpoint[1]) if len(midpoint) == 3 else None,
                            float(midpoint[2]) if len(midpoint) == 3 else None,
                            float(first_seen),
                            float(last_seen),
                            int(reopen_count),
                            diagnostics_json,
                        ),
                    )
                result.id = str(row_id)
                result.clash_key = str(clash_key)
                result.first_seen_at = float(first_seen)
                result.last_seen_at = float(last_seen)
                result.reopen_count = int(reopen_count)
                result.reopened = bool(reopened)
                result.assignee = assignee
                result.tags = list(tags or [])
                try:
                    result.status = ClashResultStatus(str(status_raw))
                except Exception:
                    result.status = ClashResultStatus.NEW
                result.diagnostics = diagnostics
                if original_result_id:
                    result_id_map[original_result_id] = str(row_id)
                result_id_map[str(clash_key)] = str(row_id)
                persisted[clash_key] = {
                    "id": str(row_id),
                    "clashKey": str(clash_key),
                    "kind": "clash",
                    "status": str(status_raw),
                    "firstSeenAt": float(first_seen),
                    "lastSeenAt": float(last_seen),
                    "updatedAt": float(last_seen),
                    "reopened": bool(reopened),
                    "reopenCount": int(reopen_count),
                    "comments": list(diagnostics.get("comments") or []),
                }

            for view in list(viewpoints or []):
                mapped_result_id = str(result_id_map.get(str(view.result_id or ""), str(view.result_id or "")))
                view.result_id = mapped_result_id
                camera = {
                    "position": list(view.camera_position),
                    "direction": list(view.camera_direction),
                    "up": list(view.camera_up),
                    "type": view.camera_type,
                    "scale": view.camera_scale,
                    "look_at": list(view.look_at) if view.look_at else None,
                }
                conn.execute(
                    """
                    INSERT INTO issue_views(
                        id, test_id, result_id, camera_json, screenshot_path, screenshot_status, created_ts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(view.id),
                        tid,
                        mapped_result_id,
                        json.dumps(camera, ensure_ascii=True),
                        str(view.screenshot_path) if view.screenshot_path else None,
                        str(view.screenshot_status),
                        float(view.created_ts),
                    ),
                )
        return persisted

    def update_result_status(
        self,
        *,
        test_id: str,
        clash_key: str,
        status: str,
        updated_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        tid = str(test_id or "").strip()
        key = str(clash_key or "").strip()
        status_norm = str(status or "").strip().lower()
        if not tid or not key or not status_norm:
            return {}
        now = float(updated_ts if updated_ts is not None else time.time())
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, diagnostics_json, first_seen_ts, reopen_count
                FROM clash_results
                WHERE test_id = ? AND clash_key = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (tid, key),
            ).fetchone()
            if row is None:
                return {}
            row_id = str(row["id"] or "").strip()
            first_seen = float(row["first_seen_ts"] or now)
            reopen_count = int(row["reopen_count"] or 0)
            diagnostics = self._json_dict(row["diagnostics_json"])
            result_diag = dict(diagnostics.get("result") or {})
            result_diag.update(
                {
                    "clashKey": key,
                    "status": status_norm,
                    "firstSeenAt": float(first_seen),
                    "lastSeenAt": float(now),
                    "updatedAt": float(now),
                    "reopened": False,
                    "reopenCount": int(reopen_count),
                }
            )
            diagnostics["result"] = result_diag
            lifecycle = dict(diagnostics.get("lifecycle") or {})
            lifecycle.update(
                {
                    "clashKey": key,
                    "firstSeenAt": float(first_seen),
                    "lastSeenAt": float(now),
                    "updatedAt": float(now),
                    "reopened": False,
                    "reopenCount": int(reopen_count),
                }
            )
            diagnostics["lifecycle"] = lifecycle
            conn.execute(
                """
                UPDATE clash_results
                SET status = ?, last_seen_ts = ?, diagnostics_json = ?
                WHERE id = ?
                """,
                (
                    status_norm,
                    float(now),
                    json.dumps(diagnostics, ensure_ascii=True),
                    row_id,
                ),
            )
            return {
                "id": row_id,
                "clashKey": key,
                "kind": "clash",
                "status": status_norm,
                "firstSeenAt": float(first_seen),
                "lastSeenAt": float(now),
                "updatedAt": float(now),
                "reopened": False,
                "reopenCount": int(reopen_count),
                "comments": list(diagnostics.get("comments") or []),
            }

    def append_result_comment(
        self,
        *,
        test_id: str,
        clash_key: str,
        comment: str,
        author: str = "",
        updated_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        tid = str(test_id or "").strip()
        key = str(clash_key or "").strip()
        text = str(comment or "").strip()
        if not tid or not key or not text:
            return {}
        who = str(author or "").strip()
        now = float(updated_ts if updated_ts is not None else time.time())
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, diagnostics_json, first_seen_ts, status, reopen_count
                FROM clash_results
                WHERE test_id = ? AND clash_key = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (tid, key),
            ).fetchone()
            if row is None:
                return {}
            row_id = str(row["id"] or "").strip()
            first_seen = float(row["first_seen_ts"] or now)
            status_norm = str(row["status"] or ClashResultStatus.NEW.value).strip().lower()
            reopen_count = int(row["reopen_count"] or 0)
            diagnostics = self._json_dict(row["diagnostics_json"])
            comments = list(diagnostics.get("comments") or [])
            comments.append(
                {
                    "text": text,
                    "author": who,
                    "createdAt": float(now),
                }
            )
            diagnostics["comments"] = comments[-200:]
            result_diag = dict(diagnostics.get("result") or {})
            result_diag.update(
                {
                    "clashKey": key,
                    "status": status_norm,
                    "firstSeenAt": float(first_seen),
                    "lastSeenAt": float(now),
                    "updatedAt": float(now),
                    "reopened": False,
                    "reopenCount": int(reopen_count),
                }
            )
            diagnostics["result"] = result_diag
            lifecycle = dict(diagnostics.get("lifecycle") or {})
            lifecycle.update(
                {
                    "clashKey": key,
                    "firstSeenAt": float(first_seen),
                    "lastSeenAt": float(now),
                    "updatedAt": float(now),
                    "reopened": False,
                    "reopenCount": int(reopen_count),
                }
            )
            diagnostics["lifecycle"] = lifecycle
            conn.execute(
                """
                UPDATE clash_results
                SET last_seen_ts = ?, diagnostics_json = ?
                WHERE id = ?
                """,
                (
                    float(now),
                    json.dumps(diagnostics, ensure_ascii=True),
                    row_id,
                ),
            )
            return {
                "id": row_id,
                "clashKey": key,
                "kind": "clash",
                "status": status_norm,
                "firstSeenAt": float(first_seen),
                "lastSeenAt": float(now),
                "updatedAt": float(now),
                "reopened": False,
                "reopenCount": int(reopen_count),
                "comments": list(diagnostics.get("comments") or []),
            }

    def _row_to_test(self, conn: sqlite3.Connection, row: sqlite3.Row) -> ClashTest:
        rules_rows = list(
            conn.execute(
                "SELECT rule_key, enabled, params_json FROM ignore_rules WHERE test_id = ? ORDER BY rule_key",
                (str(row["id"]),),
            )
        )
        rules = [
            IgnoreRule(
                key=str(r["rule_key"]),
                enabled=bool(r["enabled"]),
                params=self._json_dict(r["params_json"]),
            )
            for r in rules_rows
        ]
        clash_type_raw = str(row["clash_type"] or ClashType.HARD.value)
        try:
            clash_type = ClashType(clash_type_raw)
        except Exception:
            clash_type = ClashType.HARD
        return ClashTest(
            id=str(row["id"]),
            name=str(row["name"]),
            search_set_ids_a=self._json_list(row["search_set_ids_a"]),
            search_set_ids_b=self._json_list(row["search_set_ids_b"]),
            clash_type=clash_type,
            threshold_mm=float(row["threshold_mm"] or 0.0),
            ignore_rules=rules,
            grouping_order=self._json_list(row["grouping_order"]),
            proximity_meters=float(row["proximity_meters"] or 6.0),
            auto_viewpoint=bool(row["auto_viewpoint"]),
            auto_screenshot=bool(row["auto_screenshot"]),
            created_ts=float(row["created_ts"] or time.time()),
            updated_ts=float(row["updated_ts"] or time.time()),
        )

    @staticmethod
    def _json_list(raw: Any) -> List[str]:
        try:
            data = json.loads(str(raw or "[]"))
            if not isinstance(data, list):
                return []
            return [str(v) for v in data if str(v).strip()]
        except Exception:
            return []

    @staticmethod
    def _json_dict(raw: Any) -> Dict[str, Any]:
        try:
            data = json.loads(str(raw or "{}"))
            return dict(data) if isinstance(data, dict) else {}
        except Exception:
            return {}
