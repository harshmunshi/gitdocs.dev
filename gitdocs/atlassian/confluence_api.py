"""High-level Confluence API operations."""

import logging
from typing import Any

from markdownify import markdownify
from markdown import markdown

from gitdocs.atlassian.confluence_client import ConfluenceClient
from gitdocs.atlassian.models import (
    ConfluencePage,
    ConfluenceSpace,
    ConfluencePageTree,
)
from gitdocs.core.errors import ConfluenceError

logger = logging.getLogger(__name__)


class ConfluenceAPI:
    """High-level Confluence API for common operations."""
    
    def __init__(self, client: ConfluenceClient) -> None:
        """
        Initialize Confluence API.
        
        Args:
            client: Low-level ConfluenceClient instance
        """
        self.client = client
    
    def test_connection(self) -> dict[str, Any]:
        """
        Test API connection.
        
        Returns:
            Current user information
        """
        # Use legacy API for user info
        return self.client.get_legacy("user/current")
    
    def get_spaces(self, limit: int = 25) -> list[ConfluenceSpace]:
        """
        Get all accessible spaces.
        
        Args:
            limit: Maximum spaces to return
            
        Returns:
            List of ConfluenceSpace instances
        """
        params = {"limit": limit}
        response = self.client.get("spaces", params=params)
        
        spaces = []
        for space_data in response.get("results", []):
            spaces.append(
                ConfluenceSpace(
                    id=space_data.get("id", ""),
                    key=space_data.get("key", ""),
                    name=space_data.get("name", ""),
                    type=space_data.get("type", "global"),
                    homepageId=space_data.get("homepageId"),
                )
            )
        
        return spaces
    
    def get_space(self, space_key: str) -> ConfluenceSpace:
        """
        Get a space by key.
        
        Args:
            space_key: Space key
            
        Returns:
            ConfluenceSpace instance
        """
        # Find space ID from key using spaces endpoint
        params = {"keys": space_key}
        response = self.client.get("spaces", params=params)
        
        results = response.get("results", [])
        if not results:
            raise ConfluenceError(f"Space not found: {space_key}", status_code=404)
        
        space_data = results[0]
        return ConfluenceSpace(
            id=space_data.get("id", ""),
            key=space_data.get("key", ""),
            name=space_data.get("name", ""),
            type=space_data.get("type", "global"),
            homepageId=space_data.get("homepageId"),
        )
    
    def get_pages_in_space(
        self,
        space_id: str,
        limit: int = 50,
        status: str = "current",
    ) -> list[ConfluencePage]:
        """
        Get all pages in a space.
        
        Args:
            space_id: Space ID
            limit: Maximum pages to return
            status: Page status filter
            
        Returns:
            List of ConfluencePage instances
        """
        params = {
            "space-id": space_id,
            "limit": limit,
            "status": status,
            "body-format": "storage",
        }
        
        response = self.client.get("pages", params=params)
        
        pages = []
        for page_data in response.get("results", []):
            pages.append(ConfluencePage.from_api_response(page_data))
        
        return pages
    
    def get_page(
        self,
        page_id: str,
        body_format: str = "storage",
    ) -> ConfluencePage:
        """
        Get a page by ID.
        
        Args:
            page_id: Page ID
            body_format: Body format ('storage', 'atlas_doc_format', 'view')
            
        Returns:
            ConfluencePage instance
        """
        params = {"body-format": body_format}
        response = self.client.get(f"pages/{page_id}", params=params)
        
        return ConfluencePage.from_api_response(response)
    
    def get_page_by_title(
        self,
        space_key: str,
        title: str,
    ) -> ConfluencePage | None:
        """
        Find a page by title in a space.
        
        Args:
            space_key: Space key
            title: Page title
            
        Returns:
            ConfluencePage if found, None otherwise
        """
        # First get space ID
        space = self.get_space(space_key)
        
        params = {
            "space-id": space.id,
            "title": title,
            "body-format": "storage",
        }
        
        response = self.client.get("pages", params=params)
        results = response.get("results", [])
        
        if results:
            return ConfluencePage.from_api_response(results[0])
        return None
    
    def get_page_children(
        self,
        page_id: str,
        limit: int = 50,
    ) -> list[ConfluencePage]:
        """
        Get child pages of a page.
        
        Args:
            page_id: Parent page ID
            limit: Maximum children to return
            
        Returns:
            List of child pages
        """
        params = {"limit": limit}
        response = self.client.get(f"pages/{page_id}/children", params=params)
        
        children = []
        for page_data in response.get("results", []):
            children.append(ConfluencePage.from_api_response(page_data))
        
        return children
    
    def get_page_tree(
        self,
        space_key: str,
        max_depth: int = 3,
    ) -> ConfluencePageTree:
        """
        Get page tree for a space.
        
        Args:
            space_key: Space key
            max_depth: Maximum depth to traverse
            
        Returns:
            ConfluencePageTree with hierarchical structure
        """
        space = self.get_space(space_key)
        
        # Get root pages (pages without parent)
        all_pages = self.get_pages_in_space(space.id, limit=100)
        
        # Build parent-child relationships
        pages_by_id: dict[str, ConfluencePage] = {p.id: p for p in all_pages}
        root_pages: list[ConfluencePage] = []
        
        for page in all_pages:
            if page.parent_id and page.parent_id in pages_by_id:
                parent = pages_by_id[page.parent_id]
                parent.children.append(page)
            elif not page.parent_id:
                root_pages.append(page)
        
        return ConfluencePageTree(
            root_pages=root_pages,
            total_pages=len(all_pages),
        )
    
    def create_page(
        self,
        space_id: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        body_format: str = "storage",
    ) -> ConfluencePage:
        """
        Create a new page.
        
        Args:
            space_id: Space ID
            title: Page title
            body: Page content
            parent_id: Optional parent page ID
            body_format: Content format
            
        Returns:
            Created ConfluencePage
        """
        data: dict[str, Any] = {
            "spaceId": space_id,
            "title": title,
            "body": {
                "representation": body_format,
                "value": body,
            },
        }
        
        if parent_id:
            data["parentId"] = parent_id
        
        logger.info(f"Creating page: {title}")
        response = self.client.post("pages", data=data)
        
        return ConfluencePage.from_api_response(response)
    
    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version_number: int,
        body_format: str = "storage",
        version_message: str = "",
    ) -> ConfluencePage:
        """
        Update an existing page.
        
        Args:
            page_id: Page ID to update
            title: New title
            body: New content
            version_number: Current version number (for optimistic locking)
            body_format: Content format
            version_message: Version comment
            
        Returns:
            Updated ConfluencePage
        """
        data: dict[str, Any] = {
            "id": page_id,
            "title": title,
            "body": {
                "representation": body_format,
                "value": body,
            },
            "version": {
                "number": version_number + 1,
                "message": version_message,
            },
        }
        
        logger.info(f"Updating page {page_id}: {title}")
        response = self.client.put(f"pages/{page_id}", data=data)
        
        return ConfluencePage.from_api_response(response)
    
    # =========================================================================
    # Format conversion helpers
    # =========================================================================
    
    def page_to_markdown(self, page: ConfluencePage) -> str:
        """
        Convert page storage format to Markdown.
        
        Args:
            page: Page with storage format body
            
        Returns:
            Markdown string
        """
        # Use markdownify to convert HTML-like storage format
        md = markdownify(page.body, heading_style="ATX")
        
        # Add frontmatter
        frontmatter = f"""---
title: "{page.title}"
page_id: "{page.id}"
space_id: "{page.space_id}"
version: {page.version.number if page.version else 1}
---

"""
        return frontmatter + md
    
    def markdown_to_storage(self, md_content: str) -> str:
        """
        Convert Markdown to Confluence storage format.
        
        Args:
            md_content: Markdown string
            
        Returns:
            Confluence storage format (XHTML)
        """
        # Strip frontmatter if present
        if md_content.startswith("---"):
            parts = md_content.split("---", 2)
            if len(parts) >= 3:
                md_content = parts[2].strip()
        
        # Convert to HTML
        html = markdown(md_content, extensions=["tables", "fenced_code"])
        
        return html
    
    def diff_pages(
        self,
        local_content: str,
        remote_page: ConfluencePage,
    ) -> dict[str, Any]:
        """
        Generate diff between local markdown and remote page.
        
        Args:
            local_content: Local markdown content
            remote_page: Remote Confluence page
            
        Returns:
            Dict with diff information
        """
        remote_md = self.page_to_markdown(remote_page)
        
        # Simple line-based diff
        local_lines = local_content.splitlines()
        remote_lines = remote_md.splitlines()
        
        import difflib
        diff = list(difflib.unified_diff(
            remote_lines,
            local_lines,
            fromfile="remote",
            tofile="local",
            lineterm="",
        ))
        
        return {
            "has_changes": bool(diff),
            "diff_lines": diff,
            "local_lines": len(local_lines),
            "remote_lines": len(remote_lines),
        }

