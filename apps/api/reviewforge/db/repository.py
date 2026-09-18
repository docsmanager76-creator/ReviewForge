from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProductRecord:
    id: str
    project_id: str
    name: str
    brand: Optional[str]
    model: Optional[str]
    url: Optional[str]
    additional_urls: List[str]


@dataclass
class ProjectRecord:
    id: str
    name: str
    script_path: str
    voiceover_path: str
    master_prompt: str
    created_at: str
    product: ProductRecord


@dataclass
class JobRecord:
    id: str
    project_id: str
    type: str
    status: str
    stage: Optional[str]
    progress: int
    created_at: str
    updated_at: str
    error: Optional[str]
    result: Optional[dict]


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_project(
        self,
        name: str,
        script_path: str,
        voiceover_path: str,
        master_prompt: str,
        product_name: str,
        product_brand: Optional[str],
        product_model: Optional[str],
        product_url: Optional[str],
        additional_urls: List[str],
    ) -> ProjectRecord:
        project_id = new_id()
        product_id = new_id()
        created_at = now_iso()

        self.conn.execute(
            "INSERT INTO project (id, name, script_path, voiceover_path, master_prompt, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, name, script_path, voiceover_path, master_prompt, created_at),
        )
        self.conn.execute(
            "INSERT INTO product (id, project_id, name, brand, model, url, additional_urls) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, project_id, product_name, product_brand, product_model, product_url, json.dumps(additional_urls)),
        )
        self.conn.commit()

        return self.get_project(project_id)  # type: ignore[return-value]

    def update_project_paths(self, project_id: str, script_path: str, voiceover_path: str) -> None:
        """Used by the file-upload Create Project flow: the project row is created first (to
        get its id and thus its directory), then updated with the real paths once the
        uploaded files have been written into that project's input/ folder."""
        self.conn.execute(
            "UPDATE project SET script_path = ?, voiceover_path = ? WHERE id = ?",
            (script_path, voiceover_path, project_id),
        )
        self.conn.commit()

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        row = self.conn.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        product_row = self.conn.execute(
            "SELECT * FROM product WHERE project_id = ?", (project_id,)
        ).fetchone()
        product = ProductRecord(
            id=product_row["id"],
            project_id=project_id,
            name=product_row["name"],
            brand=product_row["brand"],
            model=product_row["model"],
            url=product_row["url"],
            additional_urls=json.loads(product_row["additional_urls"]),
        )
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            script_path=row["script_path"],
            voiceover_path=row["voiceover_path"],
            master_prompt=row["master_prompt"],
            created_at=row["created_at"],
            product=product,
        )

    def list_projects(self) -> List[ProjectRecord]:
        rows = self.conn.execute("SELECT id FROM project ORDER BY created_at DESC").fetchall()
        return [self.get_project(row["id"]) for row in rows]  # type: ignore[misc]

    def create_job(self, project_id: str, job_type: str) -> str:
        job_id = new_id()
        ts = now_iso()
        self.conn.execute(
            "INSERT INTO job (id, project_id, type, status, stage, progress, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', 'starting', 0, ?, ?)",
            (job_id, project_id, job_type, ts, ts),
        )
        self.conn.commit()
        return job_id

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        result: Optional[dict] = None,
    ) -> None:
        fields = {"updated_at": now_iso()}
        if status is not None:
            fields["status"] = status
        if stage is not None:
            fields["stage"] = stage
        if progress is not None:
            fields["progress"] = progress
        if error is not None:
            fields["error"] = error
        if result is not None:
            fields["result"] = json.dumps(result)

        set_clause = ", ".join(f"{col} = ?" for col in fields)
        self.conn.execute(f"UPDATE job SET {set_clause} WHERE id = ?", (*fields.values(), job_id))
        self.conn.commit()

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        row = self.conn.execute("SELECT * FROM job WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            type=row["type"],
            status=row["status"],
            stage=row["stage"],
            progress=row["progress"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            error=row["error"],
            result=json.loads(row["result"]) if row["result"] else None,
        )
