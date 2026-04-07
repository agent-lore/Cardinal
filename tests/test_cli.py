from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cardinal.cli import cli
from cardinal.models import ClosingInfo, Commit, Issue


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
