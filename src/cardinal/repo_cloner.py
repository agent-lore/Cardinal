"""Clone and update GitHub repositories using the git CLI."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cardinal.config import get_db_path, get_github_token, get_repo_base_dir
from cardinal.database import RepoRecord, record_repo_fetch
from cardinal.errors import RepoCloneError

__all__ = ["CloneResult", "RepoCloneError", "clone_or_update", "local_path_for"]


@dataclass(frozen=True)
class CloneResult:
    """Outcome of a clone-or-update operation."""

    path: Path
    action: str  # "cloned" or "updated"


def local_path_for(owner_repo: str, base_dir: Path | None = None) -> Path:
    """Return the on-disk path for a given owner/repo."""
    owner, _, name = owner_repo.partition("/")
    if not owner or not name:
        msg = f"Expected 'owner/repo' format, got {owner_repo!r}"
        raise ValueError(msg)
    base = base_dir if base_dir is not None else get_repo_base_dir()
    return base / owner / name


def clone_or_update(
    owner_repo: str,
    *,
    base_dir: Path | None = None,
    token: str | None = None,
    db_path: Path | None = None,
) -> CloneResult:
    """Clone owner_repo if missing, otherwise fetch + reset to origin/HEAD.

    On success, records (or upserts) a row in the repos table with the
    current HEAD SHA and a UTC timestamp.
    """
    target = local_path_for(owner_repo, base_dir=base_dir)
    auth_token = token or get_github_token()

    if (target / ".git").is_dir():
        _update_existing(target)
        action = "updated"
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        _clone_fresh(owner_repo, target, auth_token)
        action = "cloned"

    head_sha = _head_sha(target)
    record_repo_fetch(
        db_path or get_db_path(),
        RepoRecord(
            owner_repo=owner_repo,
            local_path=target,
            head_sha=head_sha,
            last_fetched=datetime.now(UTC),
        ),
    )
    return CloneResult(path=target, action=action)


def _clone_fresh(owner_repo: str, target: Path, token: str) -> None:
    url = f"https://x-access-token:{token}@github.com/{owner_repo}.git"
    _run_git(["clone", url, str(target)], cwd=None, redact=token)


def _update_existing(target: Path) -> None:
    _run_git(["fetch", "--prune", "origin"], cwd=target)
    _run_git(["reset", "--hard", "origin/HEAD"], cwd=target)


def _head_sha(target: Path) -> str:
    result = _run_git(["rev-parse", "HEAD"], cwd=target)
    return result.stdout.strip()


def _run_git(
    args: list[str], *, cwd: Path | None, redact: str | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    try:
        return subprocess.run(  # noqa: S603 (args list, no shell)
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        msg = "git executable not found on PATH"
        raise RepoCloneError(msg) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        msg = f"git {' '.join(args)} failed: {stderr}"
        if redact:
            msg = msg.replace(redact, "***")
        raise RepoCloneError(msg) from exc
