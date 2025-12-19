"""Pydantic models for Atlassian API payloads."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Jira Models
# =============================================================================


class JiraUser(BaseModel):
    """Jira user representation."""

    account_id: str = Field(default="", alias="accountId")
    display_name: str = Field(default="", alias="displayName")
    email_address: str | None = Field(default=None, alias="emailAddress")
    avatar_url: str | None = Field(default=None, alias="avatarUrls")

    class Config:
        populate_by_name = True


class JiraStatus(BaseModel):
    """Jira issue status."""

    id: str
    name: str
    status_category: str | None = Field(None, alias="statusCategory")

    class Config:
        populate_by_name = True


class JiraPriority(BaseModel):
    """Jira issue priority."""

    id: str
    name: str
    icon_url: str | None = Field(None, alias="iconUrl")

    class Config:
        populate_by_name = True


class JiraIssueType(BaseModel):
    """Jira issue type."""

    id: str
    name: str
    icon_url: str | None = Field(None, alias="iconUrl")
    subtask: bool = False

    class Config:
        populate_by_name = True


class JiraProject(BaseModel):
    """Jira project."""

    id: str
    key: str
    name: str

    class Config:
        populate_by_name = True


class JiraSprint(BaseModel):
    """Jira sprint."""

    id: int
    name: str
    state: str
    start_date: datetime | None = Field(None, alias="startDate")
    end_date: datetime | None = Field(None, alias="endDate")

    class Config:
        populate_by_name = True


class JiraIssue(BaseModel):
    """Jira issue representation."""

    id: str = ""
    key: str = ""
    summary: str = ""
    description: str | None = None
    status: JiraStatus | None = None
    issue_type: JiraIssueType | None = Field(default=None, alias="issuetype")
    priority: JiraPriority | None = None
    assignee: JiraUser | None = None
    reporter: JiraUser | None = None
    project: JiraProject | None = None
    created: datetime | None = None
    updated: datetime | None = None
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    sprint: JiraSprint | None = None
    story_points: float | None = Field(default=None, alias="storyPoints")
    parent_key: str | None = Field(default=None, alias="parentKey")
    subtasks: list[str] = Field(default_factory=list)

    # Raw fields for additional data
    raw: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "JiraIssue":
        """Parse a Jira issue from API response."""
        fields = data.get("fields", {})

        # Extract status
        status = None
        if status_data := fields.get("status"):
            status = JiraStatus(
                id=status_data.get("id", ""),
                name=status_data.get("name", ""),
                statusCategory=status_data.get("statusCategory", {}).get("name"),
            )

        # Extract issue type
        issue_type = None
        if type_data := fields.get("issuetype"):
            issue_type = JiraIssueType(
                id=type_data.get("id", ""),
                name=type_data.get("name", ""),
                iconUrl=type_data.get("iconUrl"),
                subtask=type_data.get("subtask", False),
            )

        # Extract priority
        priority = None
        if priority_data := fields.get("priority"):
            priority = JiraPriority(
                id=priority_data.get("id", ""),
                name=priority_data.get("name", ""),
                iconUrl=priority_data.get("iconUrl"),
            )

        # Extract assignee
        assignee = None
        if assignee_data := fields.get("assignee"):
            assignee = JiraUser(
                accountId=assignee_data.get("accountId", ""),
                displayName=assignee_data.get("displayName", ""),
                emailAddress=assignee_data.get("emailAddress"),
            )

        # Extract reporter
        reporter = None
        if reporter_data := fields.get("reporter"):
            reporter = JiraUser(
                accountId=reporter_data.get("accountId", ""),
                displayName=reporter_data.get("displayName", ""),
                emailAddress=reporter_data.get("emailAddress"),
            )

        # Extract project
        project = None
        if project_data := fields.get("project"):
            project = JiraProject(
                id=project_data.get("id", ""),
                key=project_data.get("key", ""),
                name=project_data.get("name", ""),
            )

        # Extract sprint from custom field (placeholder for future implementation)
        # Sprint parsing from custom fields would be done here

        # Extract labels and components
        labels = fields.get("labels", [])
        components = [c.get("name", "") for c in fields.get("components", [])]

        # Extract subtasks
        subtasks = [st.get("key", "") for st in fields.get("subtasks", [])]

        # Extract parent
        parent_key = None
        if parent := fields.get("parent"):
            parent_key = parent.get("key")

        # Handle description - can be string or ADF (Atlassian Document Format)
        description = fields.get("description")
        if isinstance(description, dict):
            description = _extract_text_from_adf(description)

        return cls(
            id=data.get("id", ""),
            key=data.get("key", ""),
            summary=fields.get("summary", ""),
            description=description,
            status=status,
            issuetype=issue_type,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            project=project,
            created=fields.get("created"),
            updated=fields.get("updated"),
            labels=labels,
            components=components,
            parentKey=parent_key,
            subtasks=subtasks,
            raw=data,
        )


class JiraComment(BaseModel):
    """Jira issue comment."""

    id: str
    body: str
    author: JiraUser | None = None
    created: datetime | None = None
    updated: datetime | None = None

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "JiraComment":
        """Parse a comment from API response."""
        author = None
        if author_data := data.get("author"):
            author = JiraUser(
                accountId=author_data.get("accountId", ""),
                displayName=author_data.get("displayName", ""),
            )

        # Handle body that could be ADF or plain text
        body = data.get("body", "")
        if isinstance(body, dict):
            # Extract text from ADF format
            body = _extract_text_from_adf(body)

        return cls(
            id=data.get("id", ""),
            body=body,
            author=author,
            created=data.get("created"),
            updated=data.get("updated"),
        )


class JiraTransition(BaseModel):
    """Jira workflow transition."""

    id: str
    name: str
    to_status: JiraStatus | None = Field(None, alias="to")

    class Config:
        populate_by_name = True


class JiraSearchResult(BaseModel):
    """Jira search (JQL) result."""

    issues: list[JiraIssue]
    total: int
    start_at: int = Field(alias="startAt")
    max_results: int = Field(alias="maxResults")

    class Config:
        populate_by_name = True


# =============================================================================
# Confluence Models
# =============================================================================


class ConfluenceUser(BaseModel):
    """Confluence user representation."""

    account_id: str = Field(alias="accountId")
    display_name: str = Field("", alias="displayName")
    email: str | None = None

    class Config:
        populate_by_name = True


class ConfluenceSpace(BaseModel):
    """Confluence space."""

    id: str = ""
    key: str = ""
    name: str = ""
    type: str = "global"
    homepage_id: str | None = Field(default=None, alias="homepageId")

    class Config:
        populate_by_name = True


class ConfluenceVersion(BaseModel):
    """Confluence page version."""

    number: int = 1
    message: str = ""
    created_at: datetime | None = Field(default=None, alias="createdAt")
    author: ConfluenceUser | None = None

    class Config:
        populate_by_name = True


class ConfluencePage(BaseModel):
    """Confluence page representation."""

    id: str = ""
    title: str = ""
    space_id: str | None = Field(default=None, alias="spaceId")
    parent_id: str | None = Field(default=None, alias="parentId")
    status: str = "current"
    body: str = ""  # Storage format or converted markdown
    version: ConfluenceVersion | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    author: ConfluenceUser | None = None

    # For tree navigation
    children: list["ConfluencePage"] = Field(default_factory=list)

    # Raw data
    raw: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ConfluencePage":
        """Parse a page from Confluence API v2 response."""
        version = None
        if version_data := data.get("version"):
            author = None
            if author_data := version_data.get("authorId"):
                author = ConfluenceUser(accountId=author_data, displayName="")
            version = ConfluenceVersion(
                number=version_data.get("number", 1),
                message=version_data.get("message", ""),
                createdAt=version_data.get("createdAt"),
                author=author,
            )

        # Extract body - prefer storage format
        body = ""
        if body_data := data.get("body"):
            if storage := body_data.get("storage"):
                body = storage.get("value", "")
            elif view := body_data.get("view"):
                body = view.get("value", "")

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            spaceId=data.get("spaceId"),
            parentId=data.get("parentId"),
            status=data.get("status", "current"),
            body=body,
            version=version,
            createdAt=data.get("createdAt"),
            raw=data,
        )


class ConfluencePageTree(BaseModel):
    """Tree structure of Confluence pages."""

    root_pages: list[ConfluencePage] = Field(default_factory=list)
    total_pages: int = 0


# =============================================================================
# Helpers
# =============================================================================


def _extract_text_from_adf(adf: dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format."""
    text_parts: list[str] = []

    def extract_recursive(node: dict[str, Any] | list[Any]) -> None:
        if isinstance(node, list):
            for item in node:
                extract_recursive(item)
        elif isinstance(node, dict):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            if "content" in node:
                extract_recursive(node["content"])

    extract_recursive(adf)
    return "".join(text_parts)
