"""Domain models for GitHub entities.

Pure Python dataclasses with no PyGithub dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Comment:
    author: str
    body: str
    created_at: datetime


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str | None
    state: str  # "open" or "closed"
    created_at: datetime
    closed_at: datetime | None = None
    labels: tuple[str, ...] = ()
    comments: tuple[Comment, ...] = ()


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str
    author: str
    date: datetime
    url: str


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    state: str
    merged: bool
    merge_commit_sha: str | None = None
    diff_url: str | None = None


@dataclass(frozen=True)
class ClosingInfo:
    """Links a closed issue to the commit/PR that closed it."""

    commit: Commit | None = None
    pull_request: PullRequest | None = None
