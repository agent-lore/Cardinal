"""Terminal output formatting for domain models."""

from __future__ import annotations

import click

from cardinal.models import ClosingInfo, Commit, Issue


def format_issue_line(issue: Issue) -> str:
    labels = f" [{', '.join(issue.labels)}]" if issue.labels else ""
    return f"#{issue.number} {issue.title}{labels}"


def echo_issue_list(issues: list[Issue]) -> None:
    for issue in issues:
        click.echo(format_issue_line(issue))


def echo_issue_detail(issue: Issue) -> None:
    click.echo(f"#{issue.number} {issue.title} ({issue.state})")
    click.echo(f"Created: {issue.created_at:%Y-%m-%d}")
    if issue.closed_at:
        click.echo(f"Closed: {issue.closed_at:%Y-%m-%d}")
    if issue.labels:
        click.echo(f"Labels: {', '.join(issue.labels)}")
    click.echo("")
    click.echo(issue.body or "(no description)")
    if issue.comments:
        click.echo(f"\n--- {len(issue.comments)} comment(s) ---")
        for c in issue.comments:
            click.echo(f"\n{c.author} ({c.created_at:%Y-%m-%d}):")
            click.echo(c.body)


def echo_commit_list(commits: list[Commit]) -> None:
    for c in commits:
        first_line = c.message.split("\n", 1)[0]
        click.echo(f"{c.sha[:7]} {c.date:%Y-%m-%d} {first_line}")


def echo_closing_info(info: ClosingInfo | None, issue_number: int) -> None:
    if info is None:
        click.echo(f"Issue #{issue_number} is not closed.")
        return
    if info.commit:
        first_line = info.commit.message.split("\n", 1)[0]
        click.echo(f"Closing commit: {info.commit.sha[:7]} - {first_line}")
        click.echo(f"URL: {info.commit.url}")
    if info.pull_request:
        click.echo(
            f"Closing PR: #{info.pull_request.number} - {info.pull_request.title}"
        )
        click.echo(f"Diff: {info.pull_request.diff_url}")
    if not info.commit and not info.pull_request:
        click.echo(f"Issue #{issue_number} was closed manually (no linked commit/PR).")
