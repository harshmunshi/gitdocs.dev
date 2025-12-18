"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository."""
    import subprocess
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        capture_output=True,
    )
    
    # Create initial commit
    readme = temp_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir,
        capture_output=True,
    )
    
    yield temp_dir


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    client = Mock()
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.fixture
def mock_confluence_client():
    """Create a mock Confluence client."""
    client = Mock()
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.fixture
def sample_jira_issue():
    """Return sample Jira issue data."""
    return {
        "id": "12345",
        "key": "PROJ-123",
        "fields": {
            "summary": "Test issue summary",
            "description": "This is a test issue description",
            "status": {
                "id": "1",
                "name": "In Progress",
                "statusCategory": {"name": "In Progress"},
            },
            "issuetype": {
                "id": "10001",
                "name": "Bug",
                "iconUrl": "https://example.com/bug.png",
                "subtask": False,
            },
            "priority": {
                "id": "2",
                "name": "High",
            },
            "assignee": {
                "accountId": "user123",
                "displayName": "John Doe",
                "emailAddress": "john@example.com",
            },
            "reporter": {
                "accountId": "user456",
                "displayName": "Jane Smith",
            },
            "project": {
                "id": "10000",
                "key": "PROJ",
                "name": "Test Project",
            },
            "labels": ["bug", "critical"],
            "components": [{"name": "backend"}],
            "created": "2024-01-15T10:00:00.000+0000",
            "updated": "2024-01-16T15:30:00.000+0000",
        },
    }


@pytest.fixture
def sample_confluence_page():
    """Return sample Confluence page data."""
    return {
        "id": "98765",
        "title": "Getting Started Guide",
        "spaceId": "SPACE123",
        "parentId": None,
        "status": "current",
        "body": {
            "storage": {
                "value": "<h1>Getting Started</h1><p>Welcome to our documentation.</p>",
            },
        },
        "version": {
            "number": 3,
            "message": "Updated introduction",
            "createdAt": "2024-01-16T12:00:00.000Z",
        },
    }


@pytest.fixture
def gitdocs_config(temp_dir):
    """Create a sample .gitdocs.yml config."""
    config_content = """
jira:
  base_url: https://company.atlassian.net
  email: user@company.com
  project_key: PROJ

confluence:
  base_url: https://company.atlassian.net
  email: user@company.com
  space_key: DOCS
"""
    config_path = temp_dir / ".gitdocs.yml"
    config_path.write_text(config_content)
    return config_path

