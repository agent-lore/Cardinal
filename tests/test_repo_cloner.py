"""Unit tests for the repo_cloner module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cardinal.repo_cloner import (
    RepoCloneError,
    clone_or_update,
    local_path_for,
)

# --- local_path_for ---


def test_local_path_for_builds_org_repo_layout(tmp_path: Path) -> None:
    result = local_path_for("agent-lore/Cardinal", base_dir=tmp_path)
    assert result == tmp_path / "agent-lore" / "Cardinal"


def test_local_path_for_rejects_bad_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="owner/repo"):
        local_path_for("not-a-valid-spec", base_dir=tmp_path)


# --- clone_or_update: fresh clone ---


def test_clone_or_update_clones_when_missing(tmp_path: Path) -> None:
    with patch("cardinal.repo_cloner.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = clone_or_update("agent-lore/Cardinal", base_dir=tmp_path, token="tok")

    assert result.action == "cloned"
    assert result.path == tmp_path / "agent-lore" / "Cardinal"

    # parent directory was created
    assert (tmp_path / "agent-lore").is_dir()

    # one git clone call
    run.assert_called_once()
    cmd = run.call_args.args[0]
    assert cmd[0:2] == ["git", "clone"]
    assert "https://x-access-token:tok@github.com/agent-lore/Cardinal.git" in cmd


# --- clone_or_update: update existing ---


def test_clone_or_update_updates_when_present(tmp_path: Path) -> None:
    target = tmp_path / "agent-lore" / "Cardinal"
    (target / ".git").mkdir(parents=True)

    with patch("cardinal.repo_cloner.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = clone_or_update("agent-lore/Cardinal", base_dir=tmp_path, token="tok")

    assert result.action == "updated"
    assert result.path == target

    assert run.call_count == 2
    fetch_cmd = run.call_args_list[0].args[0]
    reset_cmd = run.call_args_list[1].args[0]
    assert fetch_cmd == ["git", "fetch", "--prune", "origin"]
    assert reset_cmd == ["git", "reset", "--hard", "origin/HEAD"]
    # both ran in the target directory
    assert run.call_args_list[0].kwargs["cwd"] == target
    assert run.call_args_list[1].kwargs["cwd"] == target


# --- error handling ---


def test_clone_failure_raises_repo_clone_error(tmp_path: Path) -> None:
    err = subprocess.CalledProcessError(
        returncode=128, cmd=["git", "clone"], stderr="boom: secret-tok in url"
    )
    with (
        patch("cardinal.repo_cloner.subprocess.run", side_effect=err),
        pytest.raises(RepoCloneError) as excinfo,
    ):
        clone_or_update("agent-lore/Cardinal", base_dir=tmp_path, token="secret-tok")

    # token is redacted from the error message
    assert "secret-tok" not in str(excinfo.value)
    assert "***" in str(excinfo.value)


def test_clone_missing_git_executable(tmp_path: Path) -> None:
    with (
        patch("cardinal.repo_cloner.subprocess.run", side_effect=FileNotFoundError()),
        pytest.raises(RepoCloneError, match="git executable"),
    ):
        clone_or_update("agent-lore/Cardinal", base_dir=tmp_path, token="tok")
