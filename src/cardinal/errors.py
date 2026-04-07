"""Exception hierarchy for Cardinal.

All Cardinal-raised exceptions derive from CardinalError, so callers can catch
a single base type. The GitHubError subtree maps to common HTTP status codes
returned by the GitHub API; the github_client module translates PyGithub and
urllib errors into these types at the boundary.
"""

from __future__ import annotations


class CardinalError(Exception):
    """Base class for all Cardinal exceptions."""


class ConfigError(CardinalError):
    """Raised when required configuration is missing or invalid."""


class RepoCloneError(CardinalError):
    """Raised when cloning or updating a local repository fails."""


class GitHubError(CardinalError):
    """Base class for errors returned by the GitHub API."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status
        self.message = message


class GitHubAuthError(GitHubError):
    """Authentication failed (HTTP 401)."""


class GitHubPermissionError(GitHubError):
    """Token lacks permission for the requested operation (HTTP 403)."""


class GitHubNotFoundError(GitHubError):
    """Requested resource does not exist or is not visible to the token (HTTP 404)."""


class GitHubRateLimitError(GitHubError):
    """GitHub API rate limit exceeded."""
