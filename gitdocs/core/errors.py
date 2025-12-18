"""Custom exceptions for gitdocs."""

from typing import Any


class GitDocsError(Exception):
    """Base exception for all gitdocs errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(GitDocsError):
    """Configuration-related errors."""

    pass


class AuthError(GitDocsError):
    """Authentication and authorization errors."""

    pass


class ApiError(GitDocsError):
    """API communication errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class RepoNotFoundError(GitDocsError):
    """Raised when not inside a git repository."""

    def __init__(self, path: str | None = None) -> None:
        message = "Not inside a git repository"
        if path:
            message = f"Not inside a git repository: {path}"
        super().__init__(message)
        self.path = path


class JiraError(ApiError):
    """Jira-specific API errors."""

    pass


class ConfluenceError(ApiError):
    """Confluence-specific API errors."""

    pass


class CacheError(GitDocsError):
    """Cache-related errors."""

    pass


class LLMError(GitDocsError):
    """LLM integration errors."""

    pass


class ValidationError(GitDocsError):
    """Data validation errors."""

    pass

