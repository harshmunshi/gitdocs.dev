"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from gitdocs.core.config import (
    JiraConfig,
    ConfluenceConfig,
    RepoConfig,
    UserConfig,
    GitDocsConfig,
    load_yaml_config,
    save_yaml_config,
)


class TestJiraConfig:
    """Tests for JiraConfig."""
    
    def test_valid_config(self):
        """Test creating valid Jira config."""
        config = JiraConfig(
            base_url="https://company.atlassian.net",
            email="user@company.com",
            project_key="PROJ",
        )
        
        assert config.base_url == "https://company.atlassian.net"
        assert config.email == "user@company.com"
        assert config.project_key == "PROJ"
    
    def test_url_normalization(self):
        """Test that trailing slashes are removed."""
        config = JiraConfig(
            base_url="https://company.atlassian.net/",
            email="user@company.com",
        )
        
        assert config.base_url == "https://company.atlassian.net"
    
    def test_requires_https(self):
        """Test that HTTP URLs are rejected."""
        with pytest.raises(ValueError, match="HTTPS"):
            JiraConfig(
                base_url="http://company.atlassian.net",
                email="user@company.com",
            )


class TestConfluenceConfig:
    """Tests for ConfluenceConfig."""
    
    def test_valid_config(self):
        """Test creating valid Confluence config."""
        config = ConfluenceConfig(
            base_url="https://company.atlassian.net",
            email="user@company.com",
            space_key="DOCS",
        )
        
        assert config.space_key == "DOCS"


class TestRepoConfig:
    """Tests for RepoConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = RepoConfig()
        
        assert config.jira is None
        assert config.confluence is None
        assert "feature" in config.branch_patterns
        assert len(config.commit_patterns) > 0
    
    def test_with_jira(self):
        """Test config with Jira settings."""
        config = RepoConfig(
            jira=JiraConfig(
                base_url="https://company.atlassian.net",
                email="user@company.com",
            )
        )
        
        assert config.jira is not None
        assert config.jira.email == "user@company.com"


class TestUserConfig:
    """Tests for UserConfig."""
    
    def test_default_values(self):
        """Test default values."""
        config = UserConfig()
        
        assert config.default_editor == "vim"
        assert config.theme == "dark"
        assert config.llm.provider == "openai"
        assert config.cache.enabled is True
        assert config.dry_run_by_default is True


class TestYamlConfig:
    """Tests for YAML config loading/saving."""
    
    def test_load_nonexistent(self):
        """Test loading nonexistent file returns empty dict."""
        data = load_yaml_config(Path("/nonexistent/path.yml"))
        assert data == {}
    
    def test_save_and_load(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            
            data = {
                "jira": {
                    "base_url": "https://company.atlassian.net",
                    "email": "user@company.com",
                }
            }
            
            save_yaml_config(config_path, data)
            loaded = load_yaml_config(config_path)
            
            assert loaded == data
    
    def test_creates_parent_dirs(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "deep" / "config.yml"
            
            save_yaml_config(config_path, {"key": "value"})
            
            assert config_path.exists()


class TestGitDocsConfig:
    """Tests for combined GitDocsConfig."""
    
    def test_properties(self):
        """Test property accessors."""
        jira = JiraConfig(
            base_url="https://company.atlassian.net",
            email="user@company.com",
        )
        
        config = GitDocsConfig(
            repo=RepoConfig(jira=jira),
            user=UserConfig(),
        )
        
        assert config.jira == jira
        assert config.confluence is None
        assert config.llm.provider == "openai"
        assert config.cache.enabled is True

