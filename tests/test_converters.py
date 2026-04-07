from datetime import UTC, datetime
from unittest.mock import MagicMock

from cardinal.converters import (
    convert_comment,
    convert_commit,
    convert_issue,
    convert_pull_request,
)


def _make_gh_issue(
    *,
    number: int = 1,
    title: str = "Test issue",
    body: str = "body",
    state: str = "open",
    created_at: datetime | None = None,
    closed_at: datetime | None = None,
    labels: list[str] | None = None,
    is_pr: bool = False,
) -> MagicMock:
    mock = MagicMock()
    mock.number = number
    mock.title = title
    mock.body = body
    mock.state = state
    mock.created_at = created_at or datetime(2025, 1, 1, tzinfo=UTC)
    mock.closed_at = closed_at
    mock.pull_request = MagicMock() if is_pr else None

    label_mocks = []
    for name in labels or []:
        lbl = MagicMock()
        lbl.name = name
        label_mocks.append(lbl)
    mock.labels = label_mocks

    mock.get_comments.return_value = []
    return mock


def test_convert_issue_basic() -> None:
    gh = _make_gh_issue(number=42, title="Broken", labels=["bug"])
    issue = convert_issue(gh)
    assert issue is not None
    assert issue.number == 42
    assert issue.title == "Broken"
    assert issue.labels == ("bug",)
    assert issue.comments == ()


def test_convert_issue_filters_pull_requests() -> None:
    gh = _make_gh_issue(is_pr=True)
    assert convert_issue(gh) is None


def test_convert_issue_with_comments() -> None:
    comment_mock = MagicMock()
    comment_mock.user.login = "alice"
    comment_mock.body = "I see this too"
    comment_mock.created_at = datetime(2025, 1, 2, tzinfo=UTC)

    gh = _make_gh_issue()
    gh.get_comments.return_value = [comment_mock]

    issue = convert_issue(gh, include_comments=True)
    assert issue is not None
    assert len(issue.comments) == 1
    assert issue.comments[0].author == "alice"
    assert issue.comments[0].body == "I see this too"


def test_convert_comment() -> None:
    mock = MagicMock()
    mock.user.login = "bob"
    mock.body = "Looks good"
    mock.created_at = datetime(2025, 2, 1, tzinfo=UTC)

    comment = convert_comment(mock)
    assert comment.author == "bob"
    assert comment.body == "Looks good"


def test_convert_commit() -> None:
    mock = MagicMock()
    mock.sha = "abc123"
    mock.commit.message = "fix stuff"
    mock.commit.author.name = "bob"
    mock.commit.author.date = datetime(2025, 3, 1, tzinfo=UTC)
    mock.html_url = "https://github.com/o/r/commit/abc123"

    commit = convert_commit(mock)
    assert commit.sha == "abc123"
    assert commit.author == "bob"
    assert commit.message == "fix stuff"
    assert commit.url == "https://github.com/o/r/commit/abc123"


def test_convert_pull_request() -> None:
    mock = MagicMock()
    mock.number = 10
    mock.title = "Fix all the things"
    mock.state = "closed"
    mock.merged = True
    mock.merge_commit_sha = "def456"
    mock.diff_url = "https://github.com/o/r/pull/10.diff"

    pr = convert_pull_request(mock)
    assert pr.number == 10
    assert pr.merged is True
    assert pr.diff_url == "https://github.com/o/r/pull/10.diff"
