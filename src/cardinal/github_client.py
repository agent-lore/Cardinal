"""Concrete GitHub client wrapping PyGithub."""

from __future__ import annotations

import urllib.request

from github import Github
from github.GithubException import UnknownObjectException

from cardinal.config import get_github_token
from cardinal.converters import (
    convert_comment,
    convert_commit,
    convert_issue,
    convert_pull_request,
)
from cardinal.models import ClosingInfo, Comment, Commit, Issue, PullRequest

_GITHUB_API = "https://api.github.com"


class GitHubClient:
    """GitHub client that satisfies the cardinal.protocols interfaces."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or get_github_token()
        self._gh = Github(self._token)

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

    def get_file_contents(
        self, owner_repo: str, path: str, ref: str | None = None
    ) -> str:
        repo = self._gh.get_repo(owner_repo)
        contents = repo.get_contents(path, ref=ref) if ref else repo.get_contents(path)
        if isinstance(contents, list):
            msg = f"{path!r} is a directory, not a file"
            raise ValueError(msg)
        return contents.decoded_content.decode("utf-8")

    def get_commit_diff(self, owner_repo: str, sha: str) -> str:
        url = f"{_GITHUB_API}/repos/{owner_repo}/commits/{sha}"
        req = urllib.request.Request(  # noqa: S310 (https URL is fixed)
            url,
            headers={
                "Accept": "application/vnd.github.v3.diff",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "cardinal",
            },
        )
        with urllib.request.urlopen(req) as response:  # noqa: S310
            return response.read().decode("utf-8")

    def post_comment(self, owner_repo: str, issue_number: int, body: str) -> Comment:
        repo = self._gh.get_repo(owner_repo)
        gh_issue = repo.get_issue(issue_number)
        gh_comment = gh_issue.create_comment(body)
        return convert_comment(gh_comment)

    def reopen_issue(self, owner_repo: str, issue_number: int) -> Issue:
        repo = self._gh.get_repo(owner_repo)
        gh_issue = repo.get_issue(issue_number)
        gh_issue.edit(state="open")
        issue = convert_issue(gh_issue)
        if issue is None:
            msg = f"#{issue_number} is a pull request, cannot reopen as issue"
            raise ValueError(msg)
        return issue

    def open_issue(
        self,
        owner_repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> Issue:
        repo = self._gh.get_repo(owner_repo)
        gh_issue = repo.create_issue(title=title, body=body, labels=labels or [])
        issue = convert_issue(gh_issue)
        if issue is None:
            msg = "Newly created issue unexpectedly classified as a pull request"
            raise ValueError(msg)
        return issue

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
