"""SQLite persistence layer for Cardinal."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cardinal.errors import DatabaseError

__all__ = [
    "RepoRecord",
    "connect",
    "list_repo_records",
    "record_repo_fetch",
]

_CREATE_REPOS_TABLE = """
CREATE TABLE IF NOT EXISTS repos (
    owner_repo   TEXT PRIMARY KEY,
    local_path   TEXT NOT NULL,
    head_sha     TEXT NOT NULL,
    last_fetched TEXT NOT NULL
)
"""

_UPSERT_REPO = """
INSERT INTO repos (owner_repo, local_path, head_sha, last_fetched)
VALUES (?, ?, ?, ?)
ON CONFLICT(owner_repo) DO UPDATE SET
    local_path   = excluded.local_path,
    head_sha     = excluded.head_sha,
    last_fetched = excluded.last_fetched
"""


@dataclass(frozen=True)
class RepoRecord:
    owner_repo: str
    local_path: Path
    head_sha: str
    last_fetched: datetime


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, ensuring the parent directory and schema exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        msg = f"Failed to open database at {db_path}: {exc}"
        raise DatabaseError(msg) from exc

    try:
        conn.row_factory = sqlite3.Row
        conn.execute(_CREATE_REPOS_TABLE)
        conn.commit()
        yield conn
    except sqlite3.Error as exc:
        msg = f"Database error on {db_path}: {exc}"
        raise DatabaseError(msg) from exc
    finally:
        conn.close()


def record_repo_fetch(db_path: Path, record: RepoRecord) -> None:
    """Insert or update a repos row for the given record."""
    with connect(db_path) as conn:
        try:
            conn.execute(
                _UPSERT_REPO,
                (
                    record.owner_repo,
                    str(record.local_path),
                    record.head_sha,
                    record.last_fetched.isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.Error as exc:
            msg = f"Failed to record repo fetch for {record.owner_repo}: {exc}"
            raise DatabaseError(msg) from exc


def list_repo_records(db_path: Path) -> list[RepoRecord]:
    """Return all repo records, most recently fetched first."""
    with connect(db_path) as conn:
        try:
            rows = conn.execute(
                "SELECT owner_repo, local_path, head_sha, last_fetched "
                "FROM repos ORDER BY last_fetched DESC"
            ).fetchall()
        except sqlite3.Error as exc:
            msg = f"Failed to list repo records: {exc}"
            raise DatabaseError(msg) from exc

    return [_row_to_record(row) for row in rows]


def _row_to_record(row: sqlite3.Row) -> RepoRecord:
    last_fetched = datetime.fromisoformat(row["last_fetched"])
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=UTC)
    return RepoRecord(
        owner_repo=row["owner_repo"],
        local_path=Path(row["local_path"]),
        head_sha=row["head_sha"],
        last_fetched=last_fetched,
    )
