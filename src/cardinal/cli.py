"""Cardinal CLI — GitHub repository analysis tool."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

import click

from cardinal.errors import CardinalError
from cardinal.formatting import (
    echo_closing_info,
    echo_commit_list,
    echo_issue_detail,
    echo_issue_list,
)
from cardinal.github_client import GitHubClient
from cardinal.repo_cloner import clone_or_update


def _make_client() -> GitHubClient:
    return GitHubClient()


def _friendly_errors[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Render any CardinalError as a clean CLI error instead of a stack trace."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except CardinalError as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapper


@click.group()
@click.version_option(package_name="cardinal")
def cli() -> None:
    """Cardinal — GitHub repository analysis tool."""


@cli.command()
@click.argument("repo")
@click.option(
    "--state",
    type=click.Choice(["open", "closed"]),
    default="open",
    help="Filter by issue state.",
)
@click.option("--limit", default=30, help="Max issues to fetch.")
@_friendly_errors
def issues(repo: str, state: str, limit: int) -> None:
    """List issues for REPO (owner/repo format)."""
    client = _make_client()
    if state == "open":
        result = client.get_open_issues(repo, limit=limit)
    else:
        result = client.get_closed_issues(repo, limit=limit)
    echo_issue_list(result)


@cli.command()
@click.argument("repo")
@click.argument("number", type=int)
@_friendly_errors
def issue(repo: str, number: int) -> None:
    """Show details for issue NUMBER in REPO."""
    client = _make_client()
    result = client.get_issue(repo, number)
    echo_issue_detail(result)


@cli.command()
@click.argument("repo")
@click.option("--limit", default=10, help="Number of recent commits.")
@_friendly_errors
def commits(repo: str, limit: int) -> None:
    """List recent commits for REPO."""
    client = _make_client()
    result = client.get_recent_commits(repo, limit=limit)
    echo_commit_list(result)


@cli.command("closing-pr")
@click.argument("repo")
@click.argument("number", type=int)
@_friendly_errors
def closing_pr(repo: str, number: int) -> None:
    """Find the commit/PR that closed issue NUMBER."""
    client = _make_client()
    info = client.get_closing_info(repo, number)
    echo_closing_info(info, number)


# --- temporary commands for exercising write/file methods ---


@cli.command("file")
@click.argument("repo")
@click.argument("path")
@click.option("--ref", default=None, help="Branch, tag, or commit SHA.")
@_friendly_errors
def file_contents(repo: str, path: str, ref: str | None) -> None:
    """Print the contents of PATH in REPO."""
    client = _make_client()
    click.echo(client.get_file_contents(repo, path, ref=ref))


@cli.command("diff")
@click.argument("repo")
@click.argument("sha")
@_friendly_errors
def commit_diff(repo: str, sha: str) -> None:
    """Print the unified diff for commit SHA in REPO."""
    client = _make_client()
    click.echo(client.get_commit_diff(repo, sha))


@cli.command("comment")
@click.argument("repo")
@click.argument("number", type=int)
@click.argument("body")
@_friendly_errors
def comment(repo: str, number: int, body: str) -> None:
    """Post BODY as a comment on issue NUMBER in REPO."""
    client = _make_client()
    posted = client.post_comment(repo, number, body)
    click.echo(f"Posted comment by {posted.author} at {posted.created_at:%Y-%m-%d}")


@cli.command("reopen")
@click.argument("repo")
@click.argument("number", type=int)
@_friendly_errors
def reopen(repo: str, number: int) -> None:
    """Reopen issue NUMBER in REPO."""
    client = _make_client()
    issue = client.reopen_issue(repo, number)
    click.echo(f"#{issue.number} {issue.title} is now {issue.state}")


@cli.command("clone")
@click.argument("repo")
@_friendly_errors
def clone(repo: str) -> None:
    """Clone REPO locally, or update it if already cloned."""
    result = clone_or_update(repo)
    click.echo(f"{result.action}: {result.path}")


@cli.command("new-issue")
@click.argument("repo")
@click.argument("title")
@click.argument("body")
@click.option("--label", "labels", multiple=True, help="Label to apply (repeatable).")
@_friendly_errors
def new_issue(repo: str, title: str, body: str, labels: tuple[str, ...]) -> None:
    """Open a new issue in REPO."""
    client = _make_client()
    issue = client.open_issue(repo, title, body, labels=list(labels) or None)
    click.echo(f"Opened #{issue.number}: {issue.title}")
