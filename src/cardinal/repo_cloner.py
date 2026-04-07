"""Clone and update GitHub repositories using the git CLI."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from cardinal.config import get_github_token, get_repo_base_dir
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
) -> CloneResult:
    """Clone owner_repo if missing, otherwise fetch + reset to origin/HEAD."""
    target = local_path_for(owner_repo, base_dir=base_dir)
    auth_token = token or get_github_token()

    if (target / ".git").is_dir():
        _update_existing(target)
        return CloneResult(path=target, action="updated")

    target.parent.mkdir(parents=True, exist_ok=True)
    _clone_fresh(owner_repo, target, auth_token)
    return CloneResult(path=target, action="cloned")


def _clone_fresh(owner_repo: str, target: Path, token: str) -> None:
    url = f"https://x-access-token:{token}@github.com/{owner_repo}.git"
    _run_git(["clone", url, str(target)], cwd=None, redact=token)


def _update_existing(target: Path) -> None:
    _run_git(["fetch", "--prune", "origin"], cwd=target)
    _run_git(["reset", "--hard", "origin/HEAD"], cwd=target)


def _run_git(args: list[str], *, cwd: Path | None, redact: str | None = None) -> None:
    cmd = ["git", *args]
    try:
        subprocess.run(  # noqa: S603 (args list, no shell)
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
