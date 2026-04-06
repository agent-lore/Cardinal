# tests/conftest.py
import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Shared Click CLI test runner."""
    return CliRunner()
