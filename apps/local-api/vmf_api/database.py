from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS search_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  input_type TEXT NOT NULL,
  original_query TEXT NOT NULL,
  expanded_queries_json TEXT NOT NULL,
  selected_platforms_json TEXT NOT NULL,
  filters_json TEXT NOT NULL,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT,
  error_summary TEXT
);
CREATE TABLE IF NOT EXISTS search_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES search_tasks(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  platform_content_id TEXT,
  content_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  author_name TEXT,
  author_url TEXT,
  source_url TEXT NOT NULL,
  cover_url TEXT,
  local_thumbnail_path TEXT,
  published_at TEXT,
  duration_ms INTEGER,
  public_metrics_json TEXT NOT NULL DEFAULT '{}',
  matched_query TEXT,
  collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  availability_status TEXT NOT NULL DEFAULT 'public',
  rights_status TEXT NOT NULL DEFAULT 'unknown',
  raw_metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS project_materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  result_id INTEGER NOT NULL REFERENCES search_results(id) ON DELETE CASCADE,
  selected_timestamp_ms INTEGER,
  tags_json TEXT NOT NULL DEFAULT '[]',
  note TEXT NOT NULL DEFAULT '',
  review_status TEXT NOT NULL DEFAULT 'pending',
  rights_status TEXT NOT NULL DEFAULT 'unknown',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        with self._lock:
            self.connection.executescript(SCHEMA)
            self.connection.commit()
    def close(self) -> None:
        with self._lock:
            self.connection.close()
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self.connection.execute(sql, tuple(params))
            self.connection.commit()
            return cursor
    def query_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None
    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self.connection.execute(sql, tuple(params)).fetchall()]

def loads_json_fields(record: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    copied = dict(record)
    for field in fields:
        value = copied.get(field)
        if isinstance(value, str):
            copied[field] = json.loads(value)
    return copied
