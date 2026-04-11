"""Configuration and environment loading.

Cardinal is configured by a TOML file (``cardinal.toml``) that describes
global settings and the list of repositories to watch. This module defines
the in-memory representation of that file, validates it on load, and
exposes a small amount of env-backed state (the GitHub token) that does
not live in the config file.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, cast

from dotenv import load_dotenv

from cardinal.errors import ConfigError

__all__ = [
    "DEFAULT_DB_PATH",
    "DEFAULT_REPO_BASE_DIR",
    "CardinalConfig",
    "ConfigError",
    "RepoConfig",
    "RepoImportance",
    "RepoStatus",
    "ReportConfig",
    "ReviewConfig",
    "ReviewerName",
    "StorageConfig",
    "find_config_path",
    "get_github_token",
    "load_config",
    "parse_repo_importance",
    "parse_repo_status",
    "parse_reviewer_name",
]

DEFAULT_REPO_BASE_DIR = Path.home() / ".cardinal" / "repos"
DEFAULT_DB_PATH = Path.home() / ".cardinal" / "cardinal.db"


# ── env-backed helpers ─────────────────────────────────────────────────


def get_github_token() -> str:
    """Return ``CARDINAL_GITHUB_TOKEN`` from the environment.

    The token is never stored in ``cardinal.toml``. ``.env`` files are
    loaded before the lookup.
    """
    load_dotenv()
    token = os.environ.get("CARDINAL_GITHUB_TOKEN", "")
    if not token:
        raise ConfigError(
            "CARDINAL_GITHUB_TOKEN not found. "
            "Set it in your environment or in a .env file."
        )
    return token


# ── Literal types + validators ─────────────────────────────────────────

RepoStatus = Literal[
    "production",
    "active",
    "maintenance",
    "experimental",
    "dormant",
    "abandoned",
]
RepoImportance = Literal["critical", "high", "medium", "low"]
ReviewerName = Literal["claude", "codex"]

_VALID_REPO_STATUS: set[str] = {
    "production",
    "active",
    "maintenance",
    "experimental",
    "dormant",
    "abandoned",
}
_VALID_REPO_IMPORTANCE: set[str] = {"critical", "high", "medium", "low"}
_VALID_REVIEWER_NAME: set[str] = {"claude", "codex"}


def parse_repo_status(value: str) -> RepoStatus:
    """Validate and narrow a string to a ``RepoStatus`` literal."""
    if value not in _VALID_REPO_STATUS:
        raise ConfigError(
            f"Invalid status {value!r}. Valid values: {sorted(_VALID_REPO_STATUS)}"
        )
    return cast(RepoStatus, value)


def parse_repo_importance(value: str) -> RepoImportance:
    """Validate and narrow a string to a ``RepoImportance`` literal."""
    if value not in _VALID_REPO_IMPORTANCE:
        raise ConfigError(
            f"Invalid importance {value!r}. "
            f"Valid values: {sorted(_VALID_REPO_IMPORTANCE)}"
        )
    return cast(RepoImportance, value)


def parse_reviewer_name(value: str) -> ReviewerName:
    """Validate and narrow a string to a ``ReviewerName`` literal."""
    if value not in _VALID_REVIEWER_NAME:
        raise ConfigError(
            f"Invalid reviewer {value!r}. Valid values: {sorted(_VALID_REVIEWER_NAME)}"
        )
    return cast(ReviewerName, value)


# Default importance applied when a repo entry omits ``importance``.
# ``abandoned`` has no meaningful importance — the value is a placeholder
# because callers are expected to skip abandoned repos entirely.
_STATUS_DEFAULT_IMPORTANCE: dict[RepoStatus, RepoImportance] = {
    "production": "critical",
    "active": "high",
    "maintenance": "medium",
    "experimental": "low",
    "dormant": "low",
    "abandoned": "low",
}


# ── Dataclasses ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StorageConfig:
    db_path: Path = DEFAULT_DB_PATH
    clone_dir: Path = DEFAULT_REPO_BASE_DIR


@dataclass(frozen=True)
class ReviewConfig:
    reviewers: tuple[ReviewerName, ...] = ("claude",)
    confidence_threshold: float = 0.7


@dataclass(frozen=True)
class ReportConfig:
    top_n: int = 3


@dataclass(frozen=True)
class RepoConfig:
    owner_repo: str
    status: RepoStatus
    importance: RepoImportance
    allow_reopen_closed: bool = False
    allow_open_new: bool = False
    report_top_n: int | None = None
    lithos_project: str | None = None


@dataclass(frozen=True)
class CardinalConfig:
    storage: StorageConfig
    review: ReviewConfig
    report: ReportConfig
    repos: tuple[RepoConfig, ...]


# ── Discovery and loading ──────────────────────────────────────────────


def _default_config_candidates() -> list[Path]:
    """Return the filesystem candidates checked when CARDINAL_CONFIG is unset.

    Exposed as a helper so tests can monkeypatch the search locations
    without having to override HOME and /etc.
    """
    return [
        Path.cwd() / "cardinal.toml",
        Path.home() / ".cardinal" / "cardinal.toml",
        Path("/etc/cardinal/cardinal.toml"),
    ]


def find_config_path() -> Path:
    """Return the first existing ``cardinal.toml`` in the discovery order.

    Order: ``CARDINAL_CONFIG`` env var, then ``./cardinal.toml``, then
    ``~/.cardinal/cardinal.toml``, then ``/etc/cardinal/cardinal.toml``.
    Raises ``ConfigError`` if none are found.
    """
    load_dotenv()
    explicit = os.environ.get("CARDINAL_CONFIG", "")
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            raise ConfigError(
                f"CARDINAL_CONFIG points at {p}, but no file exists there"
            )
        return p

    candidates = _default_config_candidates()
    for p in candidates:
        if p.exists():
            return p

    joined = "\n  ".join(str(p) for p in candidates)
    raise ConfigError(
        "No cardinal.toml found. Set CARDINAL_CONFIG or create one of:\n  " + joined
    )


def load_config(path: Path | None = None) -> CardinalConfig:
    """Load, validate, and return a ``CardinalConfig``.

    When ``path`` is ``None`` the config file is located via
    :func:`find_config_path`. Env-var overrides (``CARDINAL_DB_PATH``,
    ``CARDINAL_REPO_DIR``) are applied after file parsing so that env
    beats file beats built-in default.
    """
    load_dotenv()
    config_path = path if path is not None else find_config_path()

    try:
        with config_path.open("rb") as fh:
            raw: dict[str, Any] = tomllib.load(fh)
    except OSError as exc:
        raise ConfigError(f"Could not read {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{config_path}: invalid TOML: {exc}") from exc

    cardinal_section = raw.get("cardinal", {})
    if not isinstance(cardinal_section, dict):
        raise ConfigError(f"{config_path}: 'cardinal' must be a table")

    storage = _parse_storage(cardinal_section.get("storage", {}), config_path)
    review = _parse_review(cardinal_section.get("review", {}), config_path)
    report = _parse_report(cardinal_section.get("report", {}), config_path)

    repos_raw = raw.get("repos", [])
    if not isinstance(repos_raw, list) or not repos_raw:
        raise ConfigError(f"{config_path}: at least one [[repos]] entry is required")

    repos: list[RepoConfig] = []
    seen: set[str] = set()
    for index, entry in enumerate(repos_raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"{config_path}: [[repos]] entry {index} must be a table")
        repo = _parse_repo(entry, config_path, index)
        if repo.owner_repo in seen:
            raise ConfigError(f"{config_path}: duplicate repo {repo.owner_repo!r}")
        seen.add(repo.owner_repo)
        repos.append(repo)

    cfg = CardinalConfig(
        storage=storage,
        review=review,
        report=report,
        repos=tuple(repos),
    )
    return _apply_env_overrides(cfg)


# ── Internal parsing helpers ───────────────────────────────────────────


def _parse_storage(data: Any, config_path: Path) -> StorageConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: [cardinal.storage] must be a table")
    db_path = _optional_path(
        data, "db_path", DEFAULT_DB_PATH, config_path, "cardinal.storage"
    )
    clone_dir = _optional_path(
        data, "clone_dir", DEFAULT_REPO_BASE_DIR, config_path, "cardinal.storage"
    )
    return StorageConfig(db_path=db_path, clone_dir=clone_dir)


def _parse_review(data: Any, config_path: Path) -> ReviewConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: [cardinal.review] must be a table")

    reviewers_raw = data.get("reviewers", ["claude"])
    if not isinstance(reviewers_raw, list) or not reviewers_raw:
        raise ConfigError(
            f"{config_path}: [cardinal.review].reviewers must be a non-empty list"
        )
    reviewers: list[ReviewerName] = []
    for entry in reviewers_raw:
        if not isinstance(entry, str):
            raise ConfigError(
                f"{config_path}: [cardinal.review].reviewers entries must be strings"
            )
        try:
            reviewers.append(parse_reviewer_name(entry))
        except ConfigError as exc:
            raise ConfigError(
                f"{config_path}: [cardinal.review].reviewers: {exc}"
            ) from exc

    threshold_raw = data.get("confidence_threshold", 0.7)
    if isinstance(threshold_raw, bool) or not isinstance(threshold_raw, (int, float)):
        raise ConfigError(
            f"{config_path}: [cardinal.review].confidence_threshold must be a number"
        )
    threshold = float(threshold_raw)
    if not 0.0 <= threshold <= 1.0:
        raise ConfigError(
            f"{config_path}: [cardinal.review].confidence_threshold must be "
            f"between 0.0 and 1.0 (got {threshold})"
        )

    return ReviewConfig(
        reviewers=tuple(reviewers),
        confidence_threshold=threshold,
    )


def _parse_report(data: Any, config_path: Path) -> ReportConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{config_path}: [cardinal.report] must be a table")
    top_n_raw = data.get("top_n", 3)
    if isinstance(top_n_raw, bool) or not isinstance(top_n_raw, int) or top_n_raw < 1:
        raise ConfigError(
            f"{config_path}: [cardinal.report].top_n must be an integer >= 1"
        )
    return ReportConfig(top_n=top_n_raw)


def _parse_repo(data: dict[str, Any], config_path: Path, index: int) -> RepoConfig:
    section = f"[[repos]] entry {index}"

    if "owner_repo" not in data:
        raise ConfigError(
            f"{config_path}: {section}: missing required field 'owner_repo'"
        )
    owner_repo_raw = data["owner_repo"]
    if not isinstance(owner_repo_raw, str):
        raise ConfigError(f"{config_path}: {section}: owner_repo must be a string")
    owner_repo = _validate_owner_repo(owner_repo_raw, config_path, section)

    if "status" not in data:
        raise ConfigError(f"{config_path}: {section}: missing required field 'status'")
    status_raw = data["status"]
    if not isinstance(status_raw, str):
        raise ConfigError(f"{config_path}: {section}: status must be a string")
    try:
        status = parse_repo_status(status_raw)
    except ConfigError as exc:
        raise ConfigError(f"{config_path}: {section}: {exc}") from exc

    importance: RepoImportance
    if "importance" in data:
        importance_raw = data["importance"]
        if not isinstance(importance_raw, str):
            raise ConfigError(f"{config_path}: {section}: importance must be a string")
        try:
            importance = parse_repo_importance(importance_raw)
        except ConfigError as exc:
            raise ConfigError(f"{config_path}: {section}: {exc}") from exc
    else:
        importance = _STATUS_DEFAULT_IMPORTANCE[status]

    allow_reopen_closed = _optional_bool(
        data, "allow_reopen_closed", False, config_path, section
    )
    allow_open_new = _optional_bool(data, "allow_open_new", False, config_path, section)

    report_top_n: int | None
    if "report_top_n" in data:
        value = data["report_top_n"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ConfigError(
                f"{config_path}: {section}: report_top_n must be an integer >= 1"
            )
        report_top_n = value
    else:
        report_top_n = None

    lithos_project: str | None
    if "lithos_project" in data:
        lp = data["lithos_project"]
        if not isinstance(lp, str):
            raise ConfigError(
                f"{config_path}: {section}: lithos_project must be a string"
            )
        lithos_project = lp
    else:
        lithos_project = None

    return RepoConfig(
        owner_repo=owner_repo,
        status=status,
        importance=importance,
        allow_reopen_closed=allow_reopen_closed,
        allow_open_new=allow_open_new,
        report_top_n=report_top_n,
        lithos_project=lithos_project,
    )


def _optional_path(
    data: dict[str, Any],
    key: str,
    default: Path,
    config_path: Path,
    section: str,
) -> Path:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, str):
        raise ConfigError(f"{config_path}: [{section}].{key} must be a string path")
    return Path(value).expanduser()


def _optional_bool(
    data: dict[str, Any],
    key: str,
    default: bool,
    config_path: Path,
    section: str,
) -> bool:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, bool):
        raise ConfigError(f"{config_path}: {section}: {key} must be a boolean")
    return value


def _validate_owner_repo(value: str, config_path: Path, section: str) -> str:
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ConfigError(
            f"{config_path}: {section}: owner_repo {value!r} "
            f"must be in 'owner/name' format"
        )
    return value


def _apply_env_overrides(cfg: CardinalConfig) -> CardinalConfig:
    db_override = os.environ.get("CARDINAL_DB_PATH", "")
    clone_override = os.environ.get("CARDINAL_REPO_DIR", "")
    if not db_override and not clone_override:
        return cfg
    new_storage = cfg.storage
    if db_override:
        new_storage = replace(new_storage, db_path=Path(db_override).expanduser())
    if clone_override:
        new_storage = replace(new_storage, clone_dir=Path(clone_override).expanduser())
    return replace(cfg, storage=new_storage)
