"""Core modules for gitdocs."""

from gitdocs.core.config import (
    ConfluenceConfig,
    GitDocsConfig,
    JiraConfig,
    RepoConfig,
    UserConfig,
    load_config,
)
from gitdocs.core.errors import ApiError, AuthError, ConfigError, GitDocsError, RepoNotFoundError
from gitdocs.core.paths import (
    get_cache_dir,
    get_repo_config_path,
    get_repo_root,
    get_user_config_dir,
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
