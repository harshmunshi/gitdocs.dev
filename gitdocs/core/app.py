"""Application dependency container for gitdocs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from gitdocs.core.config import GitDocsConfig, load_config
from gitdocs.core.errors import ConfigError
from gitdocs.core.paths import get_cache_dir, get_repo_root

if TYPE_CHECKING:
    from gitdocs.atlassian.confluence_client import ConfluenceClient
    from gitdocs.atlassian.jira_client import JiraClient
    from gitdocs.git.repo import GitRepo
    from gitdocs.llm.client import LLMClient
    from gitdocs.store.cache import Cache


logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """
    Application context containing all initialized services.

    This is a dependency container that lazily initializes services
    as needed and provides a single point of access.
    """

    config: GitDocsConfig
    repo_root: Path

    _jira_client: JiraClient | None = field(default=None, repr=False)
    _confluence_client: ConfluenceClient | None = field(default=None, repr=False)
    _git_repo: GitRepo | None = field(default=None, repr=False)
    _cache: Cache | None = field(default=None, repr=False)
    _llm_client: LLMClient | None = field(default=None, repr=False)

    @classmethod
    def create(cls, repo_root: Path | None = None) -> AppContext:
        """
        Create an application context.

        Args:
            repo_root: Repository root path. If None, will be discovered.

        Returns:
            Initialized AppContext instance.
        """
        root = repo_root or get_repo_root()
        config = load_config(root)
        return cls(config=config, repo_root=root)

    @property
    def jira(self) -> JiraClient:
        """Get or create Jira client."""
        if self._jira_client is None:
            from gitdocs.atlassian.jira_client import JiraClient
            from gitdocs.core.secrets import get_jira_api_token

            jira_config = self.config.jira
            if not jira_config:
                raise ConfigError("Jira is not configured. Run 'gitdocs init' first.")

            api_token = get_jira_api_token()
            self._jira_client = JiraClient(
                base_url=jira_config.base_url,
                email=jira_config.email,
                api_token=api_token,
            )
        return self._jira_client

    @property
    def confluence(self) -> ConfluenceClient:
        """Get or create Confluence client."""
        if self._confluence_client is None:
            from gitdocs.atlassian.confluence_client import ConfluenceClient
            from gitdocs.core.secrets import get_confluence_api_token

            conf_config = self.config.confluence
            if not conf_config:
                raise ConfigError("Confluence is not configured. Run 'gitdocs init' first.")

            api_token = get_confluence_api_token()
            self._confluence_client = ConfluenceClient(
                base_url=conf_config.base_url,
                email=conf_config.email,
                api_token=api_token,
            )
        return self._confluence_client

    @property
    def git(self) -> GitRepo:
        """Get or create Git repository interface."""
        if self._git_repo is None:
            from gitdocs.git.repo import GitRepo

            self._git_repo = GitRepo(self.repo_root)
        return self._git_repo

    @property
    def cache(self) -> Cache:
        """Get or create cache instance."""
        if self._cache is None:
            from gitdocs.store.cache import Cache

            cache_dir = get_cache_dir(self.repo_root)
            self._cache = Cache(
                cache_dir=cache_dir,
                ttl=self.config.cache.ttl_seconds,
                enabled=self.config.cache.enabled,
            )
        return self._cache

    @property
    def llm(self) -> LLMClient:
        """Get or create LLM client."""
        if self._llm_client is None:
            from gitdocs.llm.client import create_llm_client

            self._llm_client = create_llm_client(self.config.llm)
        return self._llm_client

    def close(self) -> None:
        """Clean up resources."""
        if self._jira_client:
            self._jira_client.close()
        if self._confluence_client:
            self._confluence_client.close()
        if self._cache:
            self._cache.close()


# Global context (initialized lazily)
_context: AppContext | None = None


def get_context(repo_root: Path | None = None) -> AppContext:
    """Get or create the global application context."""
    global _context
    if _context is None:
        _context = AppContext.create(repo_root)
    return _context


def reset_context() -> None:
    """Reset the global context (useful for testing)."""
    global _context
    if _context:
        _context.close()
    _context = None
