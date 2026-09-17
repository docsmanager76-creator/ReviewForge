"""SQLite connection + schema management. A single local file (app.db) holds only metadata
and state — project records, product metadata, job history. Media always lives on disk as
files, referenced by path, never as blobs in the database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    script_path TEXT NOT NULL,
    voiceover_path TEXT NOT NULL,
    master_prompt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id),
    name TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    url TEXT,
    additional_urls TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS job (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id),
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate_job_table(conn)


def _migrate_job_table(conn: sqlite3.Connection) -> None:
    """Phase 1 adds progress-reporting columns to `job`. CREATE TABLE IF NOT EXISTS above
    leaves an existing app.db untouched, so add any missing columns here rather than requiring
    users to delete their database."""
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(job)")}
    migrations = {
        "stage": "ALTER TABLE job ADD COLUMN stage TEXT",
        "progress": "ALTER TABLE job ADD COLUMN progress INTEGER NOT NULL DEFAULT 0",
        "result": "ALTER TABLE job ADD COLUMN result TEXT",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            conn.execute(statement)
    conn.commit()
