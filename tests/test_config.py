import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cardinal.config import (
    DEFAULT_DB_PATH,
    DEFAULT_REPO_BASE_DIR,
    ConfigError,
    get_db_path,
    get_github_token,
    get_repo_base_dir,
)


def test_get_token_from_env() -> None:
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
        assert get_github_token() == "ghp_test123"


def test_missing_token_raises() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("cardinal.config.load_dotenv"),
        pytest.raises(ConfigError),
    ):
        get_github_token()


def test_dotenv_is_called() -> None:
    with (
        patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_x"}),
        patch("cardinal.config.load_dotenv") as mock_load,
    ):
        get_github_token()
        mock_load.assert_called_once()


def test_repo_base_dir_default() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_repo_base_dir() == DEFAULT_REPO_BASE_DIR


def test_repo_base_dir_from_env() -> None:
    with (
        patch.dict(os.environ, {"CARDINAL_REPO_DIR": "/tmp/cardinal-test"}),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_repo_base_dir() == Path("/tmp/cardinal-test")


def test_repo_base_dir_expands_user() -> None:
    with (
        patch.dict(os.environ, {"CARDINAL_REPO_DIR": "~/custom-repos"}),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_repo_base_dir() == Path.home() / "custom-repos"


def test_db_path_default() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_db_path() == DEFAULT_DB_PATH


def test_db_path_from_env() -> None:
    with (
        patch.dict(os.environ, {"CARDINAL_DB_PATH": "/tmp/cardinal-test.db"}),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_db_path() == Path("/tmp/cardinal-test.db")


def test_db_path_expands_user() -> None:
    with (
        patch.dict(os.environ, {"CARDINAL_DB_PATH": "~/custom.db"}),
        patch("cardinal.config.load_dotenv"),
    ):
        assert get_db_path() == Path.home() / "custom.db"
