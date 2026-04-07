"""Unit tests for GitHubClient methods (with PyGithub fully mocked)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from cardinal.github_client import GitHubClient


@pytest.fixture
def client_with_mock_gh():
    """Build a GitHubClient where the underlying Github instance is a MagicMock."""
    with patch("cardinal.github_client.Github") as gh_cls:
        mock_gh = MagicMock()
        gh_cls.return_value = mock_gh
        client = GitHubClient(token="test-token")
        yield client, mock_gh


def _make_gh_issue_mock(*, number: int = 1, title: str = "T", state: str = "open"):
    mock = MagicMock()
    mock.number = number
    mock.title = title
    mock.body = "body"
    mock.state = state
    mock.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    mock.closed_at = None
    mock.pull_request = None
    mock.labels = []
    mock.get_comments.return_value = []
    return mock


# --- get_file_contents ---


def test_get_file_contents_returns_decoded_text(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    content = MagicMock()
    content.decoded_content = b"hello world"
    # Patch isinstance check by making content an actual ContentFile-like object
    with patch("cardinal.github_client.ContentFile", MagicMock):
        repo.get_contents.return_value = content
        result = client.get_file_contents("o/r", "README.md")

    assert result == "hello world"
    repo.get_contents.assert_called_once_with("README.md")


def test_get_file_contents_with_ref(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    content = MagicMock()
    content.decoded_content = b"on branch"
    with patch("cardinal.github_client.ContentFile", MagicMock):
        repo.get_contents.return_value = content
        result = client.get_file_contents("o/r", "README.md", ref="dev")

    assert result == "on branch"
    repo.get_contents.assert_called_once_with("README.md", ref="dev")


def test_get_file_contents_directory_raises(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo
    repo.get_contents.return_value = [MagicMock(), MagicMock()]

    with pytest.raises(ValueError, match="directory"):
        client.get_file_contents("o/r", "src")


# --- get_commit_diff ---


def test_get_commit_diff_uses_diff_media_type(client_with_mock_gh) -> None:
    client, _ = client_with_mock_gh

    fake_response = MagicMock()
    fake_response.read.return_value = b"diff --git a/x b/x\n@@ -1 +1 @@\n-a\n+b\n"
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("cardinal.github_client.urllib.request.urlopen") as urlopen:
        urlopen.return_value = fake_response
        result = client.get_commit_diff("o/r", "abc123")

    assert "diff --git" in result
    req = urlopen.call_args.args[0]
    assert req.full_url == "https://api.github.com/repos/o/r/commits/abc123"
    assert req.headers["Accept"] == "application/vnd.github.v3.diff"
    assert req.headers["Authorization"] == "Bearer test-token"


# --- post_comment ---


def test_post_comment_returns_comment(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    gh_issue = MagicMock()
    repo.get_issue.return_value = gh_issue

    posted = MagicMock()
    posted.user.login = "alice"
    posted.body = "looks good"
    posted.created_at = datetime(2025, 2, 1, tzinfo=UTC)
    gh_issue.create_comment.return_value = posted

    result = client.post_comment("o/r", 1, "looks good")

    gh_issue.create_comment.assert_called_once_with("looks good")
    assert result.author == "alice"
    assert result.body == "looks good"


# --- reopen_issue ---


def test_reopen_issue_edits_and_returns_issue(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    gh_issue = _make_gh_issue_mock(number=42, title="Reopened", state="open")
    repo.get_issue.return_value = gh_issue

    result = client.reopen_issue("o/r", 42)

    gh_issue.edit.assert_called_once_with(state="open")
    assert result.number == 42
    assert result.title == "Reopened"


def test_reopen_issue_rejects_pull_request(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    gh_issue = _make_gh_issue_mock()
    gh_issue.pull_request = MagicMock()
    repo.get_issue.return_value = gh_issue

    with pytest.raises(ValueError, match="pull request"):
        client.reopen_issue("o/r", 1)


# --- open_issue ---


def test_open_issue_creates_and_returns(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    created = _make_gh_issue_mock(number=99, title="New issue")
    repo.create_issue.return_value = created

    result = client.open_issue("o/r", "New issue", "details", labels=["bug"])

    repo.create_issue.assert_called_once_with(
        title="New issue", body="details", labels=["bug"]
    )
    assert result.number == 99
    assert result.title == "New issue"


def test_open_issue_default_labels(client_with_mock_gh) -> None:
    client, mock_gh = client_with_mock_gh
    repo = MagicMock()
    mock_gh.get_repo.return_value = repo

    repo.create_issue.return_value = _make_gh_issue_mock()

    client.open_issue("o/r", "T", "B")

    repo.create_issue.assert_called_once_with(title="T", body="B", labels=[])
