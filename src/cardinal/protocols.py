"""Protocol interfaces for GitHub data access."""

from __future__ import annotations

from typing import Protocol

from cardinal.models import ClosingInfo, Comment, Commit, Issue


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


class FileRepository(Protocol):
    def get_file_contents(
        self, owner_repo: str, path: str, ref: str | None = None
    ) -> str: ...

    def get_commit_diff(self, owner_repo: str, sha: str) -> str: ...


class IssueWriter(Protocol):
    def post_comment(
        self, owner_repo: str, issue_number: int, body: str
    ) -> Comment: ...

    def reopen_issue(self, owner_repo: str, issue_number: int) -> Issue: ...

    def open_issue(
        self,
        owner_repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> Issue: ...
