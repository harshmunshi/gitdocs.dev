"""Tests for Jira integration."""

from unittest.mock import Mock

import pytest

from gitdocs.atlassian.jira_api import JiraAPI
from gitdocs.atlassian.models import JiraComment, JiraIssue


class TestJiraModels:
    """Tests for Jira data models."""

    def test_jira_issue_from_api_response(self):
        """Test parsing issue from API response."""
        response = {
            "id": "12345",
            "key": "PROJ-123",
            "fields": {
                "summary": "Test issue",
                "description": "A test description",
                "status": {
                    "id": "1",
                    "name": "In Progress",
                    "statusCategory": {"name": "In Progress"},
                },
                "issuetype": {
                    "id": "10001",
                    "name": "Bug",
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
                "labels": ["bug", "critical"],
                "components": [{"name": "backend"}],
            },
        }

        issue = JiraIssue.from_api_response(response)

        assert issue.key == "PROJ-123"
        assert issue.summary == "Test issue"
        assert issue.status.name == "In Progress"
        assert issue.issue_type.name == "Bug"
        assert issue.assignee.display_name == "John Doe"
        assert "bug" in issue.labels
        assert "backend" in issue.components

    def test_jira_comment_from_api_response(self):
        """Test parsing comment from API response."""
        response = {
            "id": "54321",
            "body": "This is a comment",
            "author": {
                "accountId": "user123",
                "displayName": "Jane Doe",
            },
            "created": "2024-01-15T10:30:00.000+0000",
        }

        comment = JiraComment.from_api_response(response)

        assert comment.id == "54321"
        assert comment.body == "This is a comment"
        assert comment.author.display_name == "Jane Doe"

    def test_jira_comment_with_adf_body(self):
        """Test parsing comment with ADF body."""
        response = {
            "id": "54321",
            "body": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Hello "},
                            {"type": "text", "text": "world"},
                        ],
                    }
                ],
            },
            "author": {"accountId": "user123", "displayName": "User"},
        }

        comment = JiraComment.from_api_response(response)

        assert comment.body == "Hello world"


class TestJiraAPI:
    """Tests for JiraAPI high-level operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Jira client."""
        return Mock()

    @pytest.fixture
    def api(self, mock_client):
        """Create JiraAPI with mock client."""
        return JiraAPI(mock_client)

    def test_search_issues(self, api, mock_client):
        """Test searching issues."""
        mock_client.post.return_value = {
            "issues": [
                {
                    "id": "1",
                    "key": "PROJ-1",
                    "fields": {"summary": "Issue 1", "status": {"id": "1", "name": "Open"}},
                },
                {
                    "id": "2",
                    "key": "PROJ-2",
                    "fields": {"summary": "Issue 2", "status": {"id": "2", "name": "Done"}},
                },
            ],
            "total": 2,
            "startAt": 0,
            "maxResults": 50,
        }

        result = api.search_issues("project = PROJ")

        assert len(result.issues) == 2
        assert result.issues[0].key == "PROJ-1"
        assert result.total == 2
        mock_client.post.assert_called_once()

    def test_get_issue(self, api, mock_client):
        """Test getting single issue."""
        mock_client.get.return_value = {
            "id": "1",
            "key": "PROJ-123",
            "fields": {
                "summary": "Test issue",
                "description": "Description",
            },
        }

        issue = api.get_issue("PROJ-123")

        assert issue.key == "PROJ-123"
        assert issue.summary == "Test issue"

    def test_add_comment(self, api, mock_client):
        """Test adding comment."""
        mock_client.post.return_value = {
            "id": "99999",
            "body": {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Test comment"}]}
                ],
            },
            "author": {"accountId": "user1", "displayName": "User"},
        }

        comment = api.add_comment("PROJ-123", "Test comment")

        assert comment.id == "99999"
        mock_client.post.assert_called_once()

    def test_get_transitions(self, api, mock_client):
        """Test getting transitions."""
        mock_client.get.return_value = {
            "transitions": [
                {"id": "11", "name": "Start Progress", "to": {"id": "3", "name": "In Progress"}},
                {"id": "21", "name": "Done", "to": {"id": "5", "name": "Done"}},
            ]
        }

        transitions = api.get_transitions("PROJ-123")

        assert len(transitions) == 2
        assert transitions[0].name == "Start Progress"

    def test_search_my_issues_builds_jql(self, api, mock_client):
        """Test JQL building for my issues."""
        mock_client.post.return_value = {
            "issues": [],
            "total": 0,
            "startAt": 0,
            "maxResults": 50,
        }

        api.search_my_issues(project_key="PROJ")

        call_args = mock_client.post.call_args
        data = call_args[1]["data"]
        jql = data["jql"]

        assert "assignee = currentUser()" in jql
        assert "project = PROJ" in jql
