"""Configuration and environment loading."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from cardinal.errors import ConfigError

__all__ = [
    "DEFAULT_DB_PATH",
    "DEFAULT_REPO_BASE_DIR",
    "ConfigError",
    "get_db_path",
    "get_github_token",
    "get_repo_base_dir",
]

DEFAULT_REPO_BASE_DIR = Path.home() / ".cardinal" / "repos"
DEFAULT_DB_PATH = Path.home() / ".cardinal" / "cardinal.db"


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


def get_db_path() -> Path:
    """Return the SQLite database path.

    Reads CARDINAL_DB_PATH from environment (or .env), falling back to
    ~/.cardinal/cardinal.db. The path is expanded but not created.
    """
    load_dotenv()
    raw = os.environ.get("CARDINAL_DB_PATH", "")
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_DB_PATH
