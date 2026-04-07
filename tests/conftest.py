# tests/conftest.py
from datetime import UTC, datetime

import pytest
from click.testing import CliRunner

from cardinal.models import Commit, Issue


@pytest.fixture
def cli_runner() -> CliRunner:
    """Shared Click CLI test runner."""
    return CliRunner()


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
