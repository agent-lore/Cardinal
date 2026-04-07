import os
from unittest.mock import patch

import pytest

from cardinal.config import ConfigError, get_github_token


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
