"""Concrete GitHub client wrapping PyGithub."""

from __future__ import annotations

from github import Github
from github.GithubException import UnknownObjectException

from cardinal.config import get_github_token
from cardinal.converters import (
    convert_commit,
    convert_issue,
    convert_pull_request,
)
from cardinal.models import ClosingInfo, Commit, Issue, PullRequest


class GitHubClient:
    """GitHub client that satisfies IssueRepository and CommitRepository protocols."""

    def __init__(self, token: str | None = None) -> None:
        self._gh = Github(token or get_github_token())

    def get_open_issues(self, owner_repo: str, *, limit: int = 100) -> list[Issue]:
        return self._list_issues(owner_repo, state="open", limit=limit)

    def get_closed_issues(self, owner_repo: str, *, limit: int = 100) -> list[Issue]:
        return self._list_issues(owner_repo, state="closed", limit=limit)

    def get_issue(self, owner_repo: str, number: int) -> Issue:
        repo = self._gh.get_repo(owner_repo)
        gh_issue = repo.get_issue(number)
        issue = convert_issue(gh_issue, include_comments=True)
        if issue is None:
            msg = f"#{number} is a pull request, not an issue"
            raise ValueError(msg)
        return issue

    def get_recent_commits(self, owner_repo: str, *, limit: int = 10) -> list[Commit]:
        repo = self._gh.get_repo(owner_repo)
        gh_commits = repo.get_commits()
        results: list[Commit] = []
        for gh_commit in gh_commits:
            if len(results) >= limit:
                break
            results.append(convert_commit(gh_commit))
        return results

    def get_closing_info(self, owner_repo: str, number: int) -> ClosingInfo | None:
        repo = self._gh.get_repo(owner_repo)
        gh_issue = repo.get_issue(number)
        if gh_issue.state != "closed":
            return None

        for event in gh_issue.get_events():
            if event.event == "closed" and event.commit_id:
                commit = convert_commit(repo.get_commit(event.commit_id))
                pr = self._find_pr_for_commit(repo, event.commit_id)
                return ClosingInfo(commit=commit, pull_request=pr)

        return ClosingInfo()  # Closed manually, no linked commit

    def _list_issues(self, owner_repo: str, *, state: str, limit: int) -> list[Issue]:
        repo = self._gh.get_repo(owner_repo)
        gh_issues = repo.get_issues(state=state, sort="created", direction="desc")
        results: list[Issue] = []
        for gh_issue in gh_issues:
            if len(results) >= limit:
                break
            issue = convert_issue(gh_issue)
            if issue is not None:
                results.append(issue)
        return results

    @staticmethod
    def _find_pr_for_commit(repo, sha: str) -> PullRequest | None:  # type: ignore[no-untyped-def]
        try:
            gh_commit = repo.get_commit(sha)
            for pr in gh_commit.get_pulls():
                return convert_pull_request(pr)
        except UnknownObjectException:
            pass
        return None
