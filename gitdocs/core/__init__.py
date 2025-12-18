"""Core modules for gitdocs."""

from gitdocs.core.config import (
    GitDocsConfig,
    JiraConfig,
    ConfluenceConfig,
    RepoConfig,
    UserConfig,
    load_config,
)
from gitdocs.core.paths import (
    get_repo_root,
    get_repo_config_path,
    get_user_config_dir,
    get_cache_dir,
)
from gitdocs.core.errors import (
    GitDocsError,
    ConfigError,
    AuthError,
    ApiError,
    RepoNotFoundError,
)

__all__ = [
    "GitDocsConfig",
    "JiraConfig",
    "ConfluenceConfig",
    "RepoConfig",
    "UserConfig",
    "load_config",
    "get_repo_root",
    "get_repo_config_path",
    "get_user_config_dir",
    "get_cache_dir",
    "GitDocsError",
    "ConfigError",
    "AuthError",
    "ApiError",
    "RepoNotFoundError",
]

