"""Path utilities for gitdocs configuration and cache locations."""

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from gitdocs.core.errors import RepoNotFoundError

REPO_CONFIG_FILENAME = ".gitdocs.yml"
USER_CONFIG_DIR_NAME = "gitdocs"
CACHE_DIR_NAME = ".gitdocs_cache"


@lru_cache(maxsize=1)
def get_repo_root(path: str | Path | None = None) -> Path:
    """
    Find the root of the git repository.

    Args:
        path: Starting path to search from. Defaults to current directory.

    Returns:
        Path to the repository root.

    Raises:
        RepoNotFoundError: If not inside a git repository.
    """
    start_path = Path(path) if path else Path.cwd()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        raise RepoNotFoundError(str(start_path))
    except FileNotFoundError:
        raise RepoNotFoundError(str(start_path))


def get_repo_config_path(repo_root: Path | None = None) -> Path:
    """
    Get the path to the repository-level config file.

    Args:
        repo_root: Repository root path. If None, will be discovered.

    Returns:
        Path to .gitdocs.yml in the repo root.
    """
    root = repo_root or get_repo_root()
    return root / REPO_CONFIG_FILENAME


def get_user_config_dir() -> Path:
    """
    Get the user-level config directory.

    Returns:
        Path to ~/.config/gitdocs/ (or XDG_CONFIG_HOME/gitdocs/).
    """
    if xdg_config := os.environ.get("XDG_CONFIG_HOME"):
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"

    config_dir = base / USER_CONFIG_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_user_config_path() -> Path:
    """
    Get the path to the user-level config file.

    Returns:
        Path to ~/.config/gitdocs/config.yml.
    """
    return get_user_config_dir() / "config.yml"


def get_cache_dir(repo_root: Path | None = None) -> Path:
    """
    Get the cache directory for the current repo.

    Args:
        repo_root: Repository root path. If None, will be discovered.

    Returns:
        Path to .gitdocs_cache/ in the repo root.
    """
    root = repo_root or get_repo_root()
    cache_dir = root / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_logs_dir() -> Path:
    """
    Get the logs directory for audit logs.

    Returns:
        Path to ~/.config/gitdocs/logs/.
    """
    logs_dir = get_user_config_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_credentials_path() -> Path:
    """
    Get the path to encrypted credentials file (fallback when keyring unavailable).

    Returns:
        Path to ~/.config/gitdocs/credentials.enc.
    """
    return get_user_config_dir() / "credentials.enc"


def ensure_gitignore_entry(repo_root: Path | None = None) -> None:
    """
    Ensure .gitdocs_cache and .gitdocs.local.yml are in .gitignore.

    Args:
        repo_root: Repository root path. If None, will be discovered.
    """
    root = repo_root or get_repo_root()
    gitignore_path = root / ".gitignore"

    entries_to_add = [CACHE_DIR_NAME + "/", ".gitdocs.local.yml"]

    existing_entries: set[str] = set()
    if gitignore_path.exists():
        existing_entries = set(gitignore_path.read_text().splitlines())

    new_entries = [e for e in entries_to_add if e not in existing_entries]

    if new_entries:
        with gitignore_path.open("a") as f:
            if existing_entries and not gitignore_path.read_text().endswith("\n"):
                f.write("\n")
            f.write("\n# gitdocs\n")
            for entry in new_entries:
                f.write(f"{entry}\n")
