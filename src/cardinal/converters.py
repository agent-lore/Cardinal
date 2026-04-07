"""Convert PyGithub objects to domain dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cardinal.models import Comment, Commit, Issue, PullRequest

if TYPE_CHECKING:
    from github.Commit import Commit as GHCommit
    from github.Issue import Issue as GHIssue
    from github.IssueComment import IssueComment as GHIssueComment
    from github.PullRequest import PullRequest as GHPullRequest


def convert_comment(gh_comment: GHIssueComment) -> Comment:
    return Comment(
        author=gh_comment.user.login if gh_comment.user else "<unknown>",
        body=gh_comment.body or "",
        created_at=gh_comment.created_at,
    )


def convert_issue(gh_issue: GHIssue, *, include_comments: bool = False) -> Issue | None:
    """Convert a GitHub issue to a domain Issue.

    Returns None if the GitHub "issue" is actually a pull request.
    """
    if gh_issue.pull_request is not None:
        return None

    comments: tuple[Comment, ...] = ()
    if include_comments:
        comments = tuple(convert_comment(c) for c in gh_issue.get_comments())

    return Issue(
        number=gh_issue.number,
        title=gh_issue.title,
        body=gh_issue.body,
        state=gh_issue.state,
        created_at=gh_issue.created_at,
        closed_at=gh_issue.closed_at,
        labels=tuple(label.name for label in gh_issue.labels),
        comments=comments,
    )


def convert_commit(gh_commit: GHCommit) -> Commit:
    author = gh_commit.commit.author
    committer = gh_commit.commit.committer

    author_name = (author.name if author else None) or "<unknown>"
    date = (author.date if author else None) or (committer.date if committer else None)
    if date is None:
        msg = f"Commit {gh_commit.sha} has no author or committer date"
        raise ValueError(msg)

    return Commit(
        sha=gh_commit.sha,
        message=gh_commit.commit.message,
        author=author_name,
        date=date,
        url=gh_commit.html_url,
    )


def convert_pull_request(gh_pr: GHPullRequest) -> PullRequest:
    return PullRequest(
        number=gh_pr.number,
        title=gh_pr.title,
        state=gh_pr.state,
        merged=gh_pr.merged,
        merge_commit_sha=gh_pr.merge_commit_sha,
        diff_url=gh_pr.diff_url,
    )
