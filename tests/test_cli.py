from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cardinal.cli import cli
from cardinal.models import ClosingInfo, Comment, Commit, Issue


def test_issues_command(cli_runner: CliRunner, sample_issue: Issue) -> None:
    mock_client = MagicMock()
    mock_client.get_open_issues.return_value = [sample_issue]

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["issues", "owner/repo"])

    assert result.exit_code == 0
    assert "#1" in result.output
    assert "Bug: something broken" in result.output


def test_issues_closed(cli_runner: CliRunner, sample_issue: Issue) -> None:
    mock_client = MagicMock()
    mock_client.get_closed_issues.return_value = [sample_issue]

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["issues", "owner/repo", "--state", "closed"])

    assert result.exit_code == 0
    mock_client.get_closed_issues.assert_called_once()


def test_issue_detail(cli_runner: CliRunner, sample_issue: Issue) -> None:
    mock_client = MagicMock()
    mock_client.get_issue.return_value = sample_issue

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["issue", "owner/repo", "1"])

    assert result.exit_code == 0
    assert "Bug: something broken" in result.output
    assert "It does not work" in result.output


def test_commits_command(cli_runner: CliRunner, sample_commit: Commit) -> None:
    mock_client = MagicMock()
    mock_client.get_recent_commits.return_value = [sample_commit]

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["commits", "owner/repo"])

    assert result.exit_code == 0
    assert "abc1234" in result.output
    assert "Fix the broken thing" in result.output


def test_closing_pr_command(cli_runner: CliRunner, sample_commit: Commit) -> None:
    info = ClosingInfo(commit=sample_commit)
    mock_client = MagicMock()
    mock_client.get_closing_info.return_value = info

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["closing-pr", "owner/repo", "1"])

    assert result.exit_code == 0
    assert "abc1234" in result.output


def test_version(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# --- temporary command tests ---


def test_file_command(cli_runner: CliRunner) -> None:
    mock_client = MagicMock()
    mock_client.get_file_contents.return_value = "file body here"

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["file", "owner/repo", "README.md"])

    assert result.exit_code == 0
    assert "file body here" in result.output
    mock_client.get_file_contents.assert_called_once_with(
        "owner/repo", "README.md", ref=None
    )


def test_file_command_with_ref(cli_runner: CliRunner) -> None:
    mock_client = MagicMock()
    mock_client.get_file_contents.return_value = "branch body"

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(
            cli, ["file", "owner/repo", "README.md", "--ref", "dev"]
        )

    assert result.exit_code == 0
    mock_client.get_file_contents.assert_called_once_with(
        "owner/repo", "README.md", ref="dev"
    )


def test_diff_command(cli_runner: CliRunner) -> None:
    mock_client = MagicMock()
    mock_client.get_commit_diff.return_value = "diff --git a/x b/x\n"

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["diff", "owner/repo", "abc123"])

    assert result.exit_code == 0
    assert "diff --git" in result.output
    mock_client.get_commit_diff.assert_called_once_with("owner/repo", "abc123")


def test_comment_command(cli_runner: CliRunner) -> None:
    mock_client = MagicMock()
    mock_client.post_comment.return_value = Comment(
        author="alice",
        body="hi",
        created_at=datetime(2025, 3, 1, tzinfo=UTC),
    )

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["comment", "owner/repo", "1", "hi"])

    assert result.exit_code == 0
    assert "alice" in result.output
    mock_client.post_comment.assert_called_once_with("owner/repo", 1, "hi")


def test_reopen_command(cli_runner: CliRunner, sample_issue: Issue) -> None:
    mock_client = MagicMock()
    mock_client.reopen_issue.return_value = sample_issue

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(cli, ["reopen", "owner/repo", "1"])

    assert result.exit_code == 0
    assert "open" in result.output
    mock_client.reopen_issue.assert_called_once_with("owner/repo", 1)


def test_clone_command(cli_runner: CliRunner, tmp_path) -> None:
    from cardinal.repo_cloner import CloneResult

    fake = CloneResult(path=tmp_path / "owner" / "repo", action="cloned")
    with patch("cardinal.cli.clone_or_update", return_value=fake) as mock_clone:
        result = cli_runner.invoke(cli, ["clone", "owner/repo"])

    assert result.exit_code == 0
    assert "cloned" in result.output
    assert "owner/repo" in result.output
    mock_clone.assert_called_once_with("owner/repo")


def test_new_issue_command(cli_runner: CliRunner, sample_issue: Issue) -> None:
    mock_client = MagicMock()
    mock_client.open_issue.return_value = sample_issue

    with patch("cardinal.cli._make_client", return_value=mock_client):
        result = cli_runner.invoke(
            cli,
            ["new-issue", "owner/repo", "T", "B", "--label", "bug", "--label", "ci"],
        )

    assert result.exit_code == 0
    assert "Opened #1" in result.output
    mock_client.open_issue.assert_called_once_with(
        "owner/repo", "T", "B", labels=["bug", "ci"]
    )
