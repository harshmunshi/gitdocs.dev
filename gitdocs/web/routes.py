"""API routes for the web server."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gitdocs.core.app import get_context
from gitdocs.core.config import load_config
from gitdocs.core.errors import AuthError, ConfigError, RepoNotFoundError
from gitdocs.core.paths import get_user_config_path
from gitdocs.core.secrets import SecretsManager

router = APIRouter()


# =============================================================================
# Models
# =============================================================================


class ConfigResponse(BaseModel):
    """Configuration response."""

    jira_configured: bool
    jira_url: str | None = None
    jira_email: str | None = None
    jira_project: str | None = None
    confluence_configured: bool
    confluence_url: str | None = None
    confluence_email: str | None = None
    confluence_space: str | None = None
    llm_provider: str = "none"


class ConnectionTestResponse(BaseModel):
    """Connection test response."""

    jira: dict | None = None
    confluence: dict | None = None


class TicketResponse(BaseModel):
    """Jira ticket response."""

    key: str
    summary: str
    status: str | None = None
    type: str | None = None
    assignee: str | None = None


class PageResponse(BaseModel):
    """Confluence page response."""

    id: str
    title: str
    space_id: str | None = None


# =============================================================================
# Config endpoints
# =============================================================================


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    try:
        config = load_config()

        return ConfigResponse(
            jira_configured=config.jira is not None,
            jira_url=config.jira.base_url if config.jira else None,
            jira_email=config.jira.email if config.jira else None,
            jira_project=config.jira.project_key if config.jira else None,
            confluence_configured=config.confluence is not None,
            confluence_url=config.confluence.base_url if config.confluence else None,
            confluence_email=config.confluence.email if config.confluence else None,
            confluence_space=config.confluence.space_key if config.confluence else None,
            llm_provider=config.llm.provider,
        )
    except RepoNotFoundError:
        return ConfigResponse(
            jira_configured=False,
            confluence_configured=False,
            llm_provider="none",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/test", response_model=ConnectionTestResponse)
async def test_connections():
    """Test API connections."""
    result = ConnectionTestResponse()

    try:
        ctx = get_context()

        # Test Jira
        if ctx.config.jira:
            try:
                from gitdocs.atlassian.jira_api import JiraAPI

                jira_api = JiraAPI(ctx.jira)
                user = jira_api.test_connection()
                result.jira = {
                    "configured": True,
                    "connected": True,
                    "user": user.get("displayName", "Unknown"),
                }
            except Exception as e:
                result.jira = {
                    "configured": True,
                    "connected": False,
                    "error": str(e),
                }
        else:
            result.jira = {"configured": False, "connected": False}

        # Test Confluence
        if ctx.config.confluence:
            try:
                from gitdocs.atlassian.confluence_api import ConfluenceAPI

                confluence_api = ConfluenceAPI(ctx.confluence)
                user = confluence_api.test_connection()
                result.confluence = {
                    "configured": True,
                    "connected": True,
                    "user": user.get("displayName", "Unknown"),
                }
            except Exception as e:
                result.confluence = {
                    "configured": True,
                    "connected": False,
                    "error": str(e),
                }
        else:
            result.confluence = {"configured": False, "connected": False}

    except RepoNotFoundError:
        result.jira = {"configured": False, "connected": False, "error": "Not in a git repository"}
        result.confluence = {
            "configured": False,
            "connected": False,
            "error": "Not in a git repository",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


# =============================================================================
# Tickets endpoints
# =============================================================================


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    jql: str | None = Query(None, description="JQL query"),
    mine: bool = Query(False, description="Only assigned to me"),
    limit: int = Query(25, description="Maximum results"),
):
    """List Jira tickets."""
    try:
        ctx = get_context()

        if not ctx.config.jira:
            raise HTTPException(status_code=400, detail="Jira not configured")

        from gitdocs.atlassian.jira_api import JiraAPI

        api = JiraAPI(ctx.jira)

        if jql:
            result = api.search_issues(jql, max_results=limit)
        elif mine:
            result = api.search_my_issues(
                project_key=ctx.config.jira.project_key,
                max_results=limit,
            )
        else:
            query = "ORDER BY updated DESC"
            if ctx.config.jira.project_key:
                query = f"project = {ctx.config.jira.project_key} " + query
            result = api.search_issues(query, max_results=limit)

        return [
            TicketResponse(
                key=issue.key,
                summary=issue.summary,
                status=issue.status.name if issue.status else None,
                type=issue.issue_type.name if issue.issue_type else None,
                assignee=issue.assignee.display_name if issue.assignee else None,
            )
            for issue in result.issues
        ]

    except RepoNotFoundError:
        raise HTTPException(status_code=400, detail="Not in a git repository")
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/{issue_key}")
async def get_ticket(issue_key: str):
    """Get a single Jira ticket."""
    try:
        ctx = get_context()

        if not ctx.config.jira:
            raise HTTPException(status_code=400, detail="Jira not configured")

        from gitdocs.atlassian.jira_api import JiraAPI

        api = JiraAPI(ctx.jira)

        issue = api.get_issue(issue_key)

        return {
            "key": issue.key,
            "summary": issue.summary,
            "description": issue.description,
            "status": issue.status.name if issue.status else None,
            "type": issue.issue_type.name if issue.issue_type else None,
            "priority": issue.priority.name if issue.priority else None,
            "assignee": issue.assignee.display_name if issue.assignee else None,
            "reporter": issue.reporter.display_name if issue.reporter else None,
            "labels": issue.labels,
            "created": issue.created.isoformat() if issue.created else None,
            "updated": issue.updated.isoformat() if issue.updated else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Docs endpoints
# =============================================================================


@router.get("/docs", response_model=list[PageResponse])
async def list_pages(
    space: str | None = Query(None, description="Space key"),
    limit: int = Query(50, description="Maximum results"),
):
    """List Confluence pages."""
    try:
        ctx = get_context()

        if not ctx.config.confluence:
            raise HTTPException(status_code=400, detail="Confluence not configured")

        from gitdocs.atlassian.confluence_api import ConfluenceAPI

        api = ConfluenceAPI(ctx.confluence)

        space_key = space or ctx.config.confluence.space_key
        if not space_key:
            raise HTTPException(status_code=400, detail="No space specified")

        space_obj = api.get_space(space_key)
        pages = api.get_pages_in_space(space_obj.id, limit=limit)

        return [
            PageResponse(
                id=page.id,
                title=page.title,
                space_id=page.space_id,
            )
            for page in pages
        ]

    except RepoNotFoundError:
        raise HTTPException(status_code=400, detail="Not in a git repository")
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docs/{page_id}")
async def get_page(
    page_id: str,
    format: str = Query("storage", description="Body format: storage, markdown"),
):
    """Get a Confluence page."""
    try:
        ctx = get_context()

        if not ctx.config.confluence:
            raise HTTPException(status_code=400, detail="Confluence not configured")

        from gitdocs.atlassian.confluence_api import ConfluenceAPI

        api = ConfluenceAPI(ctx.confluence)

        page = api.get_page(page_id)

        body = page.body
        if format == "markdown":
            body = api.page_to_markdown(page)

        return {
            "id": page.id,
            "title": page.title,
            "space_id": page.space_id,
            "version": page.version.number if page.version else None,
            "body": body,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Spaces endpoint
# =============================================================================


@router.get("/spaces")
async def list_spaces():
    """List available Confluence spaces."""
    try:
        ctx = get_context()

        if not ctx.config.confluence:
            raise HTTPException(status_code=400, detail="Confluence not configured")

        from gitdocs.atlassian.confluence_api import ConfluenceAPI

        api = ConfluenceAPI(ctx.confluence)

        spaces = api.get_spaces()

        return [
            {
                "id": space.id,
                "key": space.key,
                "name": space.name,
                "type": space.type,
            }
            for space in spaces
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Credentials endpoints
# =============================================================================


class JiraCredentials(BaseModel):
    """Jira credentials input."""

    url: str | None = None
    email: str | None = None
    project: str | None = None
    token: str | None = None


class ConfluenceCredentials(BaseModel):
    """Confluence credentials input."""

    url: str | None = None
    email: str | None = None
    space: str | None = None
    token: str | None = None


class OpenAICredentials(BaseModel):
    """OpenAI credentials input."""

    key: str | None = None


@router.post("/credentials/jira")
async def save_jira_credentials(creds: JiraCredentials):
    """Save Jira credentials."""
    import yaml

    try:
        # Get user config path
        user_config_path = get_user_config_path()
        user_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if user_config_path.exists():
            with open(user_config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update Jira config
        if "jira" not in config:
            config["jira"] = {}

        if creds.url:
            config["jira"]["base_url"] = creds.url.rstrip("/")
        if creds.email:
            config["jira"]["email"] = creds.email
        if creds.project:
            config["jira"]["project_key"] = creds.project

        # Save config
        with open(user_config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        # Save token to secrets if provided
        if creds.token:
            secrets = SecretsManager()
            base_url = creds.url or config["jira"].get("base_url", "")
            if base_url:
                secrets.store_jira_token(base_url, creds.token)

        return {"status": "ok", "message": "Jira settings saved"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credentials/confluence")
async def save_confluence_credentials(creds: ConfluenceCredentials):
    """Save Confluence credentials."""
    import yaml

    try:
        # Get user config path
        user_config_path = get_user_config_path()
        user_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if user_config_path.exists():
            with open(user_config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update Confluence config
        if "confluence" not in config:
            config["confluence"] = {}

        if creds.url:
            config["confluence"]["base_url"] = creds.url.rstrip("/")
        if creds.email:
            config["confluence"]["email"] = creds.email
        if creds.space:
            config["confluence"]["space_key"] = creds.space

        # Save config
        with open(user_config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        # Save token to secrets if provided
        if creds.token:
            secrets = SecretsManager()
            base_url = creds.url or config["confluence"].get("base_url", "")
            if base_url:
                secrets.store_confluence_token(base_url, creds.token)

        return {"status": "ok", "message": "Confluence settings saved"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credentials/openai")
async def save_openai_credentials(creds: OpenAICredentials):
    """Save OpenAI API key."""
    import yaml

    try:
        # Get user config path
        user_config_path = get_user_config_path()
        user_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if user_config_path.exists():
            with open(user_config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update LLM config
        if "llm" not in config:
            config["llm"] = {}

        config["llm"]["provider"] = "openai"

        # Save config
        with open(user_config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        # Save key to secrets if provided
        if creds.key:
            secrets = SecretsManager()
            secrets.store_openai_key(creds.key)

        return {"status": "ok", "message": "OpenAI key saved"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/credentials")
async def clear_credentials():
    """Clear all stored credentials."""
    try:
        secrets = SecretsManager()

        # Try to clear all known credentials
        try:
            secrets.clear_all()
        except Exception:
            pass

        # Also clear the user config file
        user_config_path = get_user_config_path()
        if user_config_path.exists():
            user_config_path.unlink()

        return {"status": "ok", "message": "All credentials cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
