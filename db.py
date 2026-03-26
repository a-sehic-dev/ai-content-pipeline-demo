from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from utils import utc_now_iso


DEFAULT_DB_PATH = Path(os.environ.get("PIPELINE_DB_PATH", "ai_content_pipeline.db")).resolve()
SCHEMA_PATH = Path(os.environ.get("PIPELINE_SCHEMA_PATH", "schema.sql")).resolve()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection, schema_path: Path | None = None) -> None:
    schema = (schema_path or SCHEMA_PATH).read_text(encoding="utf-8")
    conn.executescript(schema)


def as_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def log_event(
    conn: sqlite3.Connection,
    *,
    level: str,
    event_type: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO logs (level, event_type, message, context_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (level, event_type, message, as_json(context) if context else None, utc_now_iso()),
    )


def fetch_one(conn: sqlite3.Connection, query: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    cur = conn.execute(query, params)
    return cur.fetchone()


def fetch_all(conn: sqlite3.Connection, query: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    cur = conn.execute(query, params)
    return list(cur.fetchall())


def execute_many(conn: sqlite3.Connection, query: str, rows: Iterable[Sequence[Any]]) -> int:
    cur = conn.executemany(query, rows)
    return cur.rowcount


@dataclass(frozen=True)
class Campaign:
    id: int
    service_name: str
    content_idea: str
    cta: str | None
    link: str | None
    selected_platforms: list[str]
    created_at: str


def get_latest_campaign(conn: sqlite3.Connection) -> Campaign | None:
    row = fetch_one(
        conn,
        """
        SELECT id, service_name, content_idea, cta, link, selected_platforms_json, created_at
        FROM content_campaigns
        ORDER BY id DESC
        LIMIT 1
        """,
    )
    if not row:
        return None
    platforms = json.loads(row["selected_platforms_json"])
    return Campaign(
        id=int(row["id"]),
        service_name=str(row["service_name"]),
        content_idea=str(row["content_idea"]),
        cta=row["cta"],
        link=row["link"],
        selected_platforms=list(platforms),
        created_at=str(row["created_at"]),
    )

