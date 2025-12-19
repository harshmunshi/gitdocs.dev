"""High-level Jira API operations."""

import logging
from typing import Any

from gitdocs.atlassian.jira_client import JiraClient
from gitdocs.atlassian.models import (
    JiraComment,
    JiraIssue,
    JiraSearchResult,
    JiraStatus,
    JiraTransition,
)

logger = logging.getLogger(__name__)


class JiraAPI:
    """High-level Jira API for common operations."""

    DEFAULT_FIELDS = [
        "summary",
        "description",
        "status",
        "issuetype",
        "priority",
        "assignee",
        "reporter",
        "project",
        "created",
        "updated",
        "labels",
        "components",
        "parent",
        "subtasks",
    ]

    def __init__(self, client: JiraClient) -> None:
        """
        Initialize Jira API.

        Args:
            client: Low-level JiraClient instance
        """
        self.client = client

    def test_connection(self) -> dict[str, Any]:
        """
        Test API connection and return current user info.

        Returns:
            Current user information

        Raises:
            AuthError: If authentication fails
        """
        return self.client.get("myself")

    def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int = 50,
        start_at: int = 0,
        expand: list[str] | None = None,
    ) -> JiraSearchResult:
        """
        Search issues using JQL.

        Uses the new POST /search/jql endpoint (Jira Cloud 2024+).
        The old /search endpoint was deprecated May 2025.

        Args:
            jql: JQL query string
            fields: Fields to return (defaults to common fields)
            max_results: Maximum results to return
            start_at: Pagination offset (note: new API uses cursor pagination)
            expand: Additional data to expand

        Returns:
            JiraSearchResult with matching issues
        """
        fields = fields or self.DEFAULT_FIELDS

        # New search/jql endpoint format
        data: dict[str, Any] = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }

        # Note: new API uses nextPageToken for pagination, not startAt
        # For backward compat, we ignore startAt > 0 for now

        if expand:
            # expand should be a comma-separated string in new API
            data["expand"] = ",".join(expand) if isinstance(expand, list) else expand

        logger.info(f"Searching issues: {jql}")
        response = self.client.post("search/jql", data=data)

        issues = [
            JiraIssue.from_api_response(issue_data) for issue_data in response.get("issues", [])
        ]

        return JiraSearchResult(
            issues=issues,
            total=response.get("total", len(issues)),
            startAt=0,
            maxResults=response.get("maxResults", max_results),
        )

    def get_issue(
        self,
        issue_key: str,
        fields: list[str] | None = None,
        expand: list[str] | None = None,
    ) -> JiraIssue:
        """
        Get a single issue by key.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
            fields: Fields to return
            expand: Additional data to expand

        Returns:
            JiraIssue instance
        """
        fields = fields or self.DEFAULT_FIELDS

        params: dict[str, Any] = {
            "fields": ",".join(fields),
        }

        if expand:
            params["expand"] = ",".join(expand)

        logger.info(f"Getting issue: {issue_key}")
        response = self.client.get(f"issue/{issue_key}", params=params)

        return JiraIssue.from_api_response(response)

    def get_issue_comments(
        self,
        issue_key: str,
        max_results: int = 50,
        order_by: str = "-created",
    ) -> list[JiraComment]:
        """
        Get comments for an issue.

        Args:
            issue_key: Issue key
            max_results: Maximum comments to return
            order_by: Sort order ('-created' for newest first)

        Returns:
            List of JiraComment instances
        """
        params = {
            "maxResults": max_results,
            "orderBy": order_by,
        }

        response = self.client.get(f"issue/{issue_key}/comment", params=params)

        return [
            JiraComment.from_api_response(comment_data)
            for comment_data in response.get("comments", [])
        ]

    def add_comment(
        self,
        issue_key: str,
        body: str,
        visibility: dict[str, str] | None = None,
    ) -> JiraComment:
        """
        Add a comment to an issue.

        Args:
            issue_key: Issue key
            body: Comment text (plain text, will be converted to ADF)
            visibility: Optional visibility restriction

        Returns:
            Created JiraComment instance
        """
        # Convert plain text to Atlassian Document Format
        data: dict[str, Any] = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": body,
                            }
                        ],
                    }
                ],
            }
        }

        if visibility:
            data["visibility"] = visibility

        logger.info(f"Adding comment to {issue_key}")
        response = self.client.post(f"issue/{issue_key}/comment", data=data)

        return JiraComment.from_api_response(response)

    def get_transitions(self, issue_key: str) -> list[JiraTransition]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key

        Returns:
            List of available transitions
        """
        response = self.client.get(f"issue/{issue_key}/transitions")

        transitions = []
        for t in response.get("transitions", []):
            to_status = None
            if to_data := t.get("to"):
                to_status = JiraStatus(
                    id=to_data.get("id", ""),
                    name=to_data.get("name", ""),
                    statusCategory=to_data.get("statusCategory", {}).get("name"),
                )
            transitions.append(
                JiraTransition(
                    id=t["id"],
                    name=t["name"],
                    to=to_status,
                )
            )

        return transitions

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        """
        Transition an issue to a new status.

        Args:
            issue_key: Issue key
            transition_id: ID of the transition to execute
            comment: Optional comment to add with transition
            fields: Optional field updates
        """
        data: dict[str, Any] = {"transition": {"id": transition_id}}

        if fields:
            data["fields"] = fields

        if comment:
            data["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": comment}],
                                    }
                                ],
                            }
                        }
                    }
                ]
            }

        logger.info(f"Transitioning {issue_key} with transition {transition_id}")
        self.client.post(f"issue/{issue_key}/transitions", data=data)

    def get_projects(self) -> list[dict[str, Any]]:
        """Get all accessible projects."""
        response = self.client.get("project")
        return response if isinstance(response, list) else []

    def get_myself(self) -> dict[str, Any]:
        """Get current user information."""
        return self.client.get("myself")

    # =========================================================================
    # Convenience JQL builders
    # =========================================================================

    def search_my_issues(
        self,
        project_key: str | None = None,
        status_category: str | None = None,
        max_results: int = 50,
    ) -> JiraSearchResult:
        """
        Search issues assigned to current user.

        Args:
            project_key: Optional project filter
            status_category: Optional status category (e.g., 'In Progress')
            max_results: Maximum results

        Returns:
            JiraSearchResult
        """
        jql_parts = ["assignee = currentUser()"]

        if project_key:
            jql_parts.append(f"project = {project_key}")

        if status_category:
            jql_parts.append(f'statusCategory = "{status_category}"')

        jql_parts.append("ORDER BY updated DESC")

        jql = " AND ".join(jql_parts[:-1]) + " " + jql_parts[-1]
        return self.search_issues(jql, max_results=max_results)

    def search_sprint_issues(
        self,
        project_key: str | None = None,
        sprint: str = "openSprints()",
        max_results: int = 100,
    ) -> JiraSearchResult:
        """
        Search issues in current sprint.

        Args:
            project_key: Optional project filter
            sprint: Sprint filter (default: open sprints)
            max_results: Maximum results

        Returns:
            JiraSearchResult
        """
        jql_parts = [f"sprint in {sprint}"]

        if project_key:
            jql_parts.append(f"project = {project_key}")

        jql_parts.append("ORDER BY rank ASC")

        jql = " AND ".join(jql_parts[:-1]) + " " + jql_parts[-1]
        return self.search_issues(jql, max_results=max_results)

    def search_recent_issues(
        self,
        project_key: str | None = None,
        days: int = 7,
        max_results: int = 50,
    ) -> JiraSearchResult:
        """
        Search recently updated issues.

        Args:
            project_key: Optional project filter
            days: Number of days to look back
            max_results: Maximum results

        Returns:
            JiraSearchResult
        """
        jql_parts = [f"updated >= -{days}d"]

        if project_key:
            jql_parts.append(f"project = {project_key}")

        jql_parts.append("ORDER BY updated DESC")

        jql = " AND ".join(jql_parts[:-1]) + " " + jql_parts[-1]
        return self.search_issues(jql, max_results=max_results)
