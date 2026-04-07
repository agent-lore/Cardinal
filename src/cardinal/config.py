"""Configuration and environment loading."""

from __future__ import annotations

import os

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing."""


def get_github_token() -> str:
    """Return GITHUB_TOKEN from environment, loading .env first."""
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ConfigError(
            "GITHUB_TOKEN not found. Set it in your environment or in a .env file."
        )
    return token
