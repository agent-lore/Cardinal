import os
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from cardinal.config import (
    DEFAULT_DB_PATH,
    DEFAULT_REPO_BASE_DIR,
    CardinalConfig,
    ConfigError,
    get_github_token,
    load_config,
    parse_repo_importance,
    parse_repo_status,
    parse_reviewer_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- env-backed helpers ---


def test_get_token_from_env() -> None:
    with patch.dict(os.environ, {"CARDINAL_GITHUB_TOKEN": "ghp_test123"}):
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
        patch.dict(os.environ, {"CARDINAL_GITHUB_TOKEN": "ghp_x"}),
        patch("cardinal.config.load_dotenv") as mock_load,
    ):
        get_github_token()
        mock_load.assert_called_once()


# --- Literal parsers ---


def test_parse_repo_status_accepts_valid() -> None:
    assert parse_repo_status("production") == "production"


def test_parse_repo_status_rejects_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid status"):
        parse_repo_status("nope")


def test_parse_repo_importance_accepts_valid() -> None:
    assert parse_repo_importance("high") == "high"


def test_parse_repo_importance_rejects_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid importance"):
        parse_repo_importance("urgent")


def test_parse_reviewer_name_accepts_valid() -> None:
    assert parse_reviewer_name("codex") == "codex"


def test_parse_reviewer_name_rejects_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid reviewer"):
        parse_reviewer_name("gemini")


# --- TOML config: happy path ---


def _write(tmp_path: Path, body: str, name: str = "cardinal.toml") -> Path:
    p = tmp_path / name
    p.write_text(dedent(body))
    return p


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set to empty strings rather than deleting: load_config() calls
    # load_dotenv(), which only populates variables that are missing from
    # os.environ. Leaving them absent would let a developer's local .env
    # silently inject CARDINAL_DB_PATH / CARDINAL_REPO_DIR into tests.
    monkeypatch.delenv("CARDINAL_CONFIG", raising=False)
    monkeypatch.setenv("CARDINAL_DB_PATH", "")
    monkeypatch.setenv("CARDINAL_REPO_DIR", "")


def test_load_minimal_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "agent-lore/Cardinal"
        status = "active"
        """,
    )
    cfg = load_config(path)
    assert isinstance(cfg, CardinalConfig)
    assert cfg.storage.db_path == DEFAULT_DB_PATH
    assert cfg.storage.clone_dir == DEFAULT_REPO_BASE_DIR
    assert cfg.review.reviewers == ("claude",)
    assert cfg.review.confidence_threshold == 0.7
    assert cfg.report.top_n == 3
    assert len(cfg.repos) == 1
    repo = cfg.repos[0]
    assert repo.owner_repo == "agent-lore/Cardinal"
    assert repo.status == "active"
    assert repo.importance == "high"  # defaulted from status
    assert repo.allow_reopen_closed is False
    assert repo.allow_open_new is False
    assert repo.report_top_n is None
    assert repo.lithos_project is None


def test_load_full_example(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    cfg = load_config(REPO_ROOT / "cardinal.example.toml")
    assert len(cfg.repos) == 3

    lithos, cardinal, ralph = cfg.repos
    assert lithos.owner_repo == "agent-lore/lithos"
    assert lithos.status == "production"
    assert lithos.importance == "critical"  # defaulted
    assert lithos.allow_reopen_closed is True
    assert lithos.allow_open_new is True
    assert lithos.lithos_project == "projects/lithos"

    assert cardinal.owner_repo == "agent-lore/Cardinal"
    assert cardinal.status == "active"
    assert cardinal.importance == "critical"  # explicit override
    assert cardinal.report_top_n == 5

    assert ralph.owner_repo == "agent-lore/ralph-plus-plus"
    assert ralph.status == "experimental"
    assert ralph.importance == "low"  # defaulted


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("production", "critical"),
        ("active", "high"),
        ("maintenance", "medium"),
        ("experimental", "low"),
        ("dormant", "low"),
        ("abandoned", "low"),
    ],
)
def test_importance_defaults_from_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    expected: str,
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        f"""
        [[repos]]
        owner_repo = "owner/repo"
        status = "{status}"
        """,
    )
    cfg = load_config(path)
    assert cfg.repos[0].importance == expected


def test_importance_explicit_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "experimental"
        importance = "critical"
        """,
    )
    cfg = load_config(path)
    assert cfg.repos[0].importance == "critical"


def test_report_top_n_per_repo_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [cardinal.report]
        top_n = 3

        [[repos]]
        owner_repo = "owner/a"
        status = "active"
        report_top_n = 7

        [[repos]]
        owner_repo = "owner/b"
        status = "active"
        """,
    )
    cfg = load_config(path)
    assert cfg.report.top_n == 3
    assert cfg.repos[0].report_top_n == 7
    assert cfg.repos[1].report_top_n is None


def test_defaults_used_when_sections_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    cfg = load_config(path)
    assert cfg.storage.db_path == DEFAULT_DB_PATH
    assert cfg.review.reviewers == ("claude",)
    assert cfg.report.top_n == 3


# --- TOML config: discovery ---


def test_discovery_uses_cardinal_config_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    monkeypatch.setenv("CARDINAL_CONFIG", str(path))
    cfg = load_config()
    assert cfg.repos[0].owner_repo == "owner/repo"


def test_discovery_falls_back_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    monkeypatch.setattr(
        "cardinal.config._default_config_candidates",
        lambda: [path],
    )
    cfg = load_config()
    assert cfg.repos[0].owner_repo == "owner/repo"


def test_discovery_error_when_no_file_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setattr(
        "cardinal.config._default_config_candidates",
        lambda: [tmp_path / "nowhere" / "cardinal.toml"],
    )
    with pytest.raises(ConfigError, match="No cardinal.toml found"):
        load_config()


def test_discovery_raises_if_cardinal_config_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("CARDINAL_CONFIG", str(tmp_path / "does-not-exist.toml"))
    with pytest.raises(ConfigError, match="CARDINAL_CONFIG points at"):
        load_config()


# --- TOML config: env overrides ---


def test_env_override_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [cardinal.storage]
        db_path = "/from/file.db"

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    monkeypatch.setenv("CARDINAL_DB_PATH", "/from/env.db")
    cfg = load_config(path)
    assert cfg.storage.db_path == Path("/from/env.db")


def test_env_override_repo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [cardinal.storage]
        clone_dir = "/from/file"

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    monkeypatch.setenv("CARDINAL_REPO_DIR", "/from/env")
    cfg = load_config(path)
    assert cfg.storage.clone_dir == Path("/from/env")


def test_env_overrides_expand_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _write(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    monkeypatch.setenv("CARDINAL_DB_PATH", "~/override.db")
    cfg = load_config(path)
    assert cfg.storage.db_path == Path.home() / "override.db"


# --- TOML config: validation errors ---


def _bad(tmp_path: Path, body: str) -> Path:
    return _write(tmp_path, body)


def test_invalid_owner_repo_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "not-a-valid-spec"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="owner/name"):
        load_config(path)


def test_invalid_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "nope"
        """,
    )
    with pytest.raises(ConfigError, match="Invalid status"):
        load_config(path)


def test_invalid_importance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        importance = "urgent"
        """,
    )
    with pytest.raises(ConfigError, match="Invalid importance"):
        load_config(path)


def test_invalid_reviewer_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.review]
        reviewers = ["gemini"]

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="Invalid reviewer"):
        load_config(path)


def test_empty_reviewers_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.review]
        reviewers = []

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="non-empty list"):
        load_config(path)


def test_confidence_threshold_below_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.review]
        confidence_threshold = -0.1

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="between 0.0 and 1.0"):
        load_config(path)


def test_confidence_threshold_above_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.review]
        confidence_threshold = 1.5

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="between 0.0 and 1.0"):
        load_config(path)


def test_top_n_below_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.report]
        top_n = 0

        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="top_n"):
        load_config(path)


def test_report_top_n_below_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"
        report_top_n = 0
        """,
    )
    with pytest.raises(ConfigError, match="report_top_n"):
        load_config(path)


def test_no_repos_defined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [cardinal.storage]
        db_path = "/tmp/x.db"
        """,
    )
    with pytest.raises(ConfigError, match="at least one"):
        load_config(path)


def test_duplicate_owner_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        status = "active"

        [[repos]]
        owner_repo = "owner/repo"
        status = "maintenance"
        """,
    )
    with pytest.raises(ConfigError, match="duplicate repo"):
        load_config(path)


def test_missing_owner_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        status = "active"
        """,
    )
    with pytest.raises(ConfigError, match="owner_repo"):
        load_config(path)


def test_missing_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = _bad(
        tmp_path,
        """
        [[repos]]
        owner_repo = "owner/repo"
        """,
    )
    with pytest.raises(ConfigError, match="status"):
        load_config(path)


def test_invalid_toml_syntax(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    path = tmp_path / "cardinal.toml"
    path.write_text("this = not = valid = toml\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(path)
