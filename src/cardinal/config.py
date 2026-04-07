"""Configuration and environment loading."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_REPO_BASE_DIR = Path.home() / ".cardinal" / "repos"


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


def get_repo_base_dir() -> Path:
    """Return the base directory for cloned repositories.

    Reads CARDINAL_REPO_DIR from environment (or .env), falling back to
    ~/.cardinal/repos. The path is expanded but not created.
    """
    load_dotenv()
    raw = os.environ.get("CARDINAL_REPO_DIR", "")
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_REPO_BASE_DIR
