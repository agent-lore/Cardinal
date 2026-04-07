"""Protocol interfaces for GitHub data access."""

from __future__ import annotations

from typing import Protocol

from cardinal.models import ClosingInfo, Commit, Issue


class IssueRepository(Protocol):
    def get_open_issues(self, owner_repo: str, *, limit: int = 100) -> list[Issue]: ...

    def get_closed_issues(
        self, owner_repo: str, *, limit: int = 100
    ) -> list[Issue]: ...

    def get_issue(self, owner_repo: str, number: int) -> Issue: ...

    def get_closing_info(self, owner_repo: str, number: int) -> ClosingInfo | None: ...


class CommitRepository(Protocol):
    def get_recent_commits(
        self, owner_repo: str, *, limit: int = 10
    ) -> list[Commit]: ...
