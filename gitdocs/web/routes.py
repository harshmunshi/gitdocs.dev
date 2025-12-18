"""API routes for the web server."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gitdocs.core.app import get_context
from gitdocs.core.config import load_config, load_repo_config, load_user_config
from gitdocs.core.errors import ConfigError, AuthError, RepoNotFoundError

router = APIRouter()


# =============================================================================
# Models
# =============================================================================

class ConfigResponse(BaseModel):
    """Configuration response."""
    
    jira_configured: bool
    jira_url: Optional[str] = None
    jira_project: Optional[str] = None
    confluence_configured: bool
    confluence_url: Optional[str] = None
    confluence_space: Optional[str] = None
    llm_provider: str = "none"


class ConnectionTestResponse(BaseModel):
    """Connection test response."""
    
    jira: Optional[dict] = None
    confluence: Optional[dict] = None


class TicketResponse(BaseModel):
    """Jira ticket response."""
    
    key: str
    summary: str
    status: Optional[str] = None
    type: Optional[str] = None
    assignee: Optional[str] = None


class PageResponse(BaseModel):
    """Confluence page response."""
    
    id: str
    title: str
    space_id: Optional[str] = None


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
            jira_project=config.jira.project_key if config.jira else None,
            confluence_configured=config.confluence is not None,
            confluence_url=config.confluence.base_url if config.confluence else None,
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
                api = JiraAPI(ctx.jira)
                user = api.test_connection()
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
                api = ConfluenceAPI(ctx.confluence)
                user = api.test_connection()
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
        result.confluence = {"configured": False, "connected": False, "error": "Not in a git repository"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return result


# =============================================================================
# Tickets endpoints
# =============================================================================

@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    jql: Optional[str] = Query(None, description="JQL query"),
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
    space: Optional[str] = Query(None, description="Space key"),
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

