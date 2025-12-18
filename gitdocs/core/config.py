"""Configuration management for gitdocs."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gitdocs.core.paths import (
    get_repo_config_path,
    get_user_config_path,
    get_repo_root,
)
from gitdocs.core.errors import ConfigError


class JiraConfig(BaseModel):
    """Jira connection configuration."""

    base_url: str = Field(..., description="Jira Cloud base URL (e.g., https://company.atlassian.net)")
    email: str = Field(..., description="Jira account email")
    project_key: str | None = Field(None, description="Default Jira project key")
    default_filters: list[str] = Field(default_factory=list, description="Default JQL filters")
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL is properly formatted."""
        v = v.rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("Jira base URL must use HTTPS")
        return v


class ConfluenceConfig(BaseModel):
    """Confluence connection configuration."""

    base_url: str = Field(..., description="Confluence Cloud base URL")
    email: str = Field(..., description="Confluence account email")
    space_key: str | None = Field(None, description="Default Confluence space key")
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL is properly formatted."""
        v = v.rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("Confluence base URL must use HTTPS")
        return v


class LLMConfig(BaseModel):
    """LLM integration configuration."""

    provider: str = Field("openai", description="LLM provider (openai, anthropic, etc.)")
    model: str = Field("gpt-4o-mini", description="Model to use")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Generation temperature")
    confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence for suggestions"
    )
    max_tokens: int = Field(1000, gt=0, description="Maximum tokens for generation")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(True, description="Enable caching")
    ttl_seconds: int = Field(300, gt=0, description="Cache TTL in seconds")
    max_size_mb: int = Field(100, gt=0, description="Maximum cache size in MB")


class RepoConfig(BaseModel):
    """Repository-level configuration (stored in .gitdocs.yml)."""

    jira: JiraConfig | None = None
    confluence: ConfluenceConfig | None = None
    branch_patterns: dict[str, str] = Field(
        default_factory=lambda: {"feature": "feature/{ticket_key}-{slug}"},
        description="Branch naming patterns",
    )
    commit_patterns: list[str] = Field(
        default_factory=lambda: [r"\b([A-Z]+-\d+)\b"],
        description="Regex patterns to extract ticket keys from commits",
    )


class UserConfig(BaseModel):
    """User-level configuration (stored in ~/.config/gitdocs/config.yml)."""

    default_editor: str = Field("vim", description="Default editor for editing")
    theme: str = Field("dark", description="TUI theme (dark/light)")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    audit_log: bool = Field(True, description="Enable audit logging")
    dry_run_by_default: bool = Field(True, description="Enable dry-run by default for writes")


class GitDocsConfig(BaseModel):
    """Combined configuration from repo and user configs."""

    repo: RepoConfig
    user: UserConfig
    
    @property
    def jira(self) -> JiraConfig | None:
        return self.repo.jira
    
    @property
    def confluence(self) -> ConfluenceConfig | None:
        return self.repo.confluence
    
    @property
    def llm(self) -> LLMConfig:
        return self.user.llm
    
    @property
    def cache(self) -> CacheConfig:
        return self.user.cache


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file."""
    if not path.exists():
        return {}
    
    try:
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        return data
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")


def save_yaml_config(path: Path, data: dict[str, Any]) -> None:
    """Save configuration to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def load_repo_config(repo_root: Path | None = None) -> RepoConfig:
    """Load repository-level configuration."""
    try:
        config_path = get_repo_config_path(repo_root)
        data = load_yaml_config(config_path)
        return RepoConfig(**data)
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        return RepoConfig()


def load_user_config() -> UserConfig:
    """Load user-level configuration."""
    try:
        config_path = get_user_config_path()
        data = load_yaml_config(config_path)
        return UserConfig(**data)
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        return UserConfig()


def load_config(repo_root: Path | None = None) -> GitDocsConfig:
    """
    Load combined configuration from repo and user configs.
    
    Args:
        repo_root: Repository root path. If None, will be discovered.
        
    Returns:
        Combined GitDocsConfig instance.
    """
    repo_config = load_repo_config(repo_root)
    user_config = load_user_config()
    
    return GitDocsConfig(repo=repo_config, user=user_config)


def save_repo_config(config: RepoConfig, repo_root: Path | None = None) -> None:
    """Save repository-level configuration."""
    config_path = get_repo_config_path(repo_root)
    data = config.model_dump(exclude_none=True, exclude_defaults=False)
    save_yaml_config(config_path, data)


def save_user_config(config: UserConfig) -> None:
    """Save user-level configuration."""
    config_path = get_user_config_path()
    data = config.model_dump(exclude_none=True)
    save_yaml_config(config_path, data)

