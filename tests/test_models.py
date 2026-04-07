from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

from cardinal.models import Issue


def test_issue_is_frozen(sample_issue: Issue) -> None:
    with __import__("pytest").raises(FrozenInstanceError):
        sample_issue.title = "changed"  # type: ignore[misc]


def test_issue_defaults() -> None:
    issue = Issue(
        number=1,
        title="t",
        body=None,
        state="open",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    assert issue.labels == ()
    assert issue.comments == ()
    assert issue.closed_at is None
