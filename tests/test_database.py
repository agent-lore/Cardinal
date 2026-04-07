"""Unit tests for the database module."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from cardinal.database import RepoRecord, connect, list_repo_records, record_repo_fetch
from cardinal.errors import DatabaseError


def _make_record(
    owner_repo: str = "owner/repo",
    sha: str = "abc123",
    when: datetime | None = None,
    path: Path | None = None,
) -> RepoRecord:
    return RepoRecord(
        owner_repo=owner_repo,
        local_path=path or Path("/tmp/cardinal/owner/repo"),
        head_sha=sha,
        last_fetched=when or datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_connect_creates_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='repos'"
        ).fetchone()
    assert row is not None


def test_connect_creates_parent_dir(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "cardinal.db"
    with connect(db_path):
        pass
    assert db_path.is_file()


def test_record_repo_fetch_inserts_new_row(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    record = _make_record()

    record_repo_fetch(db_path, record)

    rows = list_repo_records(db_path)
    assert len(rows) == 1
    assert rows[0] == record


def test_record_repo_fetch_upserts_existing(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    first = _make_record(sha="aaaa", when=datetime(2025, 1, 1, tzinfo=UTC))
    record_repo_fetch(db_path, first)

    second = _make_record(sha="bbbb", when=datetime(2025, 6, 1, tzinfo=UTC))
    record_repo_fetch(db_path, second)

    rows = list_repo_records(db_path)
    assert len(rows) == 1
    assert rows[0].head_sha == "bbbb"
    assert rows[0].last_fetched == datetime(2025, 6, 1, tzinfo=UTC)


def test_list_repo_records_ordered_by_last_fetched(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    older = _make_record(owner_repo="o/one", when=datetime(2025, 1, 1, tzinfo=UTC))
    newer = _make_record(
        owner_repo="o/two", when=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=5)
    )

    record_repo_fetch(db_path, older)
    record_repo_fetch(db_path, newer)

    rows = list_repo_records(db_path)
    assert [r.owner_repo for r in rows] == ["o/two", "o/one"]


def test_database_error_wraps_sqlite_error(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    with (
        patch(
            "cardinal.database.sqlite3.connect",
            side_effect=sqlite3.OperationalError("disk is full"),
        ),
        pytest.raises(DatabaseError, match="disk is full"),
    ):
        record_repo_fetch(db_path, _make_record())
