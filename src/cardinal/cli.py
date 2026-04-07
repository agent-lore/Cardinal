"""Cardinal CLI — GitHub repository analysis tool."""

from __future__ import annotations

import click

from cardinal.formatting import (
    echo_closing_info,
    echo_commit_list,
    echo_issue_detail,
    echo_issue_list,
)
from cardinal.github_client import GitHubClient


def _make_client() -> GitHubClient:
    return GitHubClient()


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
def issue(repo: str, number: int) -> None:
    """Show details for issue NUMBER in REPO."""
    client = _make_client()
    result = client.get_issue(repo, number)
    echo_issue_detail(result)


@cli.command()
@click.argument("repo")
@click.option("--limit", default=10, help="Number of recent commits.")
def commits(repo: str, limit: int) -> None:
    """List recent commits for REPO."""
    client = _make_client()
    result = client.get_recent_commits(repo, limit=limit)
    echo_commit_list(result)


@cli.command("closing-pr")
@click.argument("repo")
@click.argument("number", type=int)
def closing_pr(repo: str, number: int) -> None:
    """Find the commit/PR that closed issue NUMBER."""
    client = _make_client()
    info = client.get_closing_info(repo, number)
    echo_closing_info(info, number)
