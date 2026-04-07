"""Unit tests for the repo_cloner module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cardinal.database import list_repo_records
from cardinal.repo_cloner import (
    RepoCloneError,
    clone_or_update,
    local_path_for,
)


def _fake_git(stdout_for_rev_parse: str = "deadbeefcafebabe"):
    """Return a side_effect for subprocess.run that handles rev-parse specially."""

    def run(cmd, **kwargs):
        if cmd[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=stdout_for_rev_parse + "\n", stderr=""
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    return run


# --- local_path_for ---


def test_local_path_for_builds_org_repo_layout(tmp_path: Path) -> None:
    result = local_path_for("agent-lore/Cardinal", base_dir=tmp_path)
    assert result == tmp_path / "agent-lore" / "Cardinal"


def test_local_path_for_rejects_bad_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="owner/repo"):
        local_path_for("not-a-valid-spec", base_dir=tmp_path)


# --- clone_or_update: fresh clone ---


def test_clone_or_update_clones_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    with patch("cardinal.repo_cloner.subprocess.run", side_effect=_fake_git()) as run:
        result = clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=db_path,
        )

    assert result.action == "cloned"
    assert result.path == tmp_path / "agent-lore" / "Cardinal"

    # parent directory was created
    assert (tmp_path / "agent-lore").is_dir()

    # git clone + git rev-parse HEAD
    assert run.call_count == 2
    clone_cmd = run.call_args_list[0].args[0]
    assert clone_cmd[0:2] == ["git", "clone"]
    assert "https://x-access-token:tok@github.com/agent-lore/Cardinal.git" in clone_cmd
    assert run.call_args_list[1].args[0] == ["git", "rev-parse", "HEAD"]


# --- clone_or_update: update existing ---


def test_clone_or_update_updates_when_present(tmp_path: Path) -> None:
    target = tmp_path / "agent-lore" / "Cardinal"
    (target / ".git").mkdir(parents=True)
    db_path = tmp_path / "cardinal.db"

    with patch("cardinal.repo_cloner.subprocess.run", side_effect=_fake_git()) as run:
        result = clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=db_path,
        )

    assert result.action == "updated"
    assert result.path == target

    # fetch + reset + rev-parse
    assert run.call_count == 3
    fetch_cmd = run.call_args_list[0].args[0]
    reset_cmd = run.call_args_list[1].args[0]
    rev_parse_cmd = run.call_args_list[2].args[0]
    assert fetch_cmd == ["git", "fetch", "--prune", "origin"]
    assert reset_cmd == ["git", "reset", "--hard", "origin/HEAD"]
    assert rev_parse_cmd == ["git", "rev-parse", "HEAD"]
    # all ran in the target directory
    for call in run.call_args_list:
        assert call.kwargs["cwd"] == target


# --- error handling ---


def test_clone_failure_raises_repo_clone_error(tmp_path: Path) -> None:
    err = subprocess.CalledProcessError(
        returncode=128, cmd=["git", "clone"], stderr="boom: secret-tok in url"
    )
    with (
        patch("cardinal.repo_cloner.subprocess.run", side_effect=err),
        pytest.raises(RepoCloneError) as excinfo,
    ):
        clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="secret-tok",
            db_path=tmp_path / "cardinal.db",
        )

    # token is redacted from the error message
    assert "secret-tok" not in str(excinfo.value)
    assert "***" in str(excinfo.value)


def test_clone_missing_git_executable(tmp_path: Path) -> None:
    with (
        patch("cardinal.repo_cloner.subprocess.run", side_effect=FileNotFoundError()),
        pytest.raises(RepoCloneError, match="git executable"),
    ):
        clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=tmp_path / "cardinal.db",
        )


# --- database recording ---


def test_clone_records_repo_in_database(tmp_path: Path) -> None:
    db_path = tmp_path / "cardinal.db"
    with patch("cardinal.repo_cloner.subprocess.run", side_effect=_fake_git("abc123")):
        clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=db_path,
        )

    rows = list_repo_records(db_path)
    assert len(rows) == 1
    record = rows[0]
    assert record.owner_repo == "agent-lore/Cardinal"
    assert record.local_path == tmp_path / "agent-lore" / "Cardinal"
    assert record.head_sha == "abc123"
    assert record.last_fetched.tzinfo is not None  # UTC-aware


def test_update_records_new_head_sha(tmp_path: Path) -> None:
    target = tmp_path / "agent-lore" / "Cardinal"
    (target / ".git").mkdir(parents=True)
    db_path = tmp_path / "cardinal.db"

    with patch("cardinal.repo_cloner.subprocess.run", side_effect=_fake_git("first")):
        clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=db_path,
        )

    with patch("cardinal.repo_cloner.subprocess.run", side_effect=_fake_git("second")):
        clone_or_update(
            "agent-lore/Cardinal",
            base_dir=tmp_path,
            token="tok",
            db_path=db_path,
        )

    rows = list_repo_records(db_path)
    assert len(rows) == 1  # upsert, not append
    assert rows[0].head_sha == "second"
