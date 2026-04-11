# tests/conftest.py
from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from cardinal.models import Commit, Issue


@pytest.fixture
def cli_runner() -> CliRunner:
    """Shared Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def cardinal_config_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a minimal cardinal.toml and set the env vars a CLI run needs.

    Tests that invoke the Click ``cli`` group need (a) a resolvable config
    file, so the group callback can call ``load_config`` without crashing,
    and (b) a GitHub token, so any command that instantiates a
    ``GitHubClient`` does not raise ``ConfigError``. Both storage paths
    point inside ``tmp_path`` so tests that actually write to the DB or
    the clone dir see an isolated filesystem.
    """
    db_path = tmp_path / "cardinal.db"
    clone_dir = tmp_path / "repos"
    config_path = tmp_path / "cardinal.toml"
    config_path.write_text(
        dedent(
            f"""
            [cardinal.storage]
            db_path = "{db_path}"
            clone_dir = "{clone_dir}"

            [[repos]]
            owner_repo = "owner/repo"
            status = "active"
            """
        )
    )
    monkeypatch.setenv("CARDINAL_CONFIG", str(config_path))
    monkeypatch.setenv("CARDINAL_GITHUB_TOKEN", "test-token")
    # Empty strings rather than delenv so a developer's local .env cannot
    # silently inject CARDINAL_DB_PATH / CARDINAL_REPO_DIR via load_dotenv.
    monkeypatch.setenv("CARDINAL_DB_PATH", "")
    monkeypatch.setenv("CARDINAL_REPO_DIR", "")
    return config_path


@pytest.fixture
def sample_issue() -> Issue:
    return Issue(
        number=1,
        title="Bug: something broken",
        body="It does not work",
        state="open",
        created_at=datetime(2025, 1, 15, tzinfo=UTC),
        labels=("bug", "priority"),
    )


@pytest.fixture
def sample_commit() -> Commit:
    return Commit(
        sha="abc1234567890",
        message="Fix the broken thing\n\nDetailed explanation.",
        author="dev",
        date=datetime(2025, 1, 20, tzinfo=UTC),
        url="https://github.com/owner/repo/commit/abc1234567890",
    )
