"""Tests for Confluence integration."""

import pytest
from unittest.mock import Mock

from gitdocs.atlassian.models import (
    ConfluencePage,
    ConfluenceSpace,
    ConfluenceVersion,
    ConfluencePageTree,
)
from gitdocs.atlassian.confluence_api import ConfluenceAPI


class TestConfluenceModels:
    """Tests for Confluence data models."""
    
    def test_confluence_page_from_api_response(self):
        """Test parsing page from API response."""
        response = {
            "id": "12345",
            "title": "Getting Started",
            "spaceId": "SPACE123",
            "parentId": None,
            "status": "current",
            "body": {
                "storage": {
                    "value": "<p>Hello world</p>",
                },
            },
            "version": {
                "number": 5,
                "message": "Updated intro",
            },
        }
        
        page = ConfluencePage.from_api_response(response)
        
        assert page.id == "12345"
        assert page.title == "Getting Started"
        assert page.space_id == "SPACE123"
        assert page.body == "<p>Hello world</p>"
        assert page.version.number == 5
    
    def test_confluence_space(self):
        """Test creating Confluence space."""
        space = ConfluenceSpace(
            id="123",
            key="DOCS",
            name="Documentation",
            type="global",
        )
        
        assert space.key == "DOCS"
        assert space.name == "Documentation"
    
    def test_confluence_page_tree(self):
        """Test page tree structure."""
        parent = ConfluencePage(
            id="1",
            title="Parent",
            body="",
        )
        child = ConfluencePage(
            id="2",
            title="Child",
            parentId="1",
            body="",
        )
        parent.children = [child]
        
        tree = ConfluencePageTree(
            root_pages=[parent],
            total_pages=2,
        )
        
        assert len(tree.root_pages) == 1
        assert len(tree.root_pages[0].children) == 1
        assert tree.total_pages == 2


class TestConfluenceAPI:
    """Tests for ConfluenceAPI high-level operations."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Confluence client."""
        return Mock()
    
    @pytest.fixture
    def api(self, mock_client):
        """Create ConfluenceAPI with mock client."""
        return ConfluenceAPI(mock_client)
    
    def test_get_spaces(self, api, mock_client):
        """Test getting spaces."""
        mock_client.get.return_value = {
            "results": [
                {"id": "1", "key": "DOCS", "name": "Documentation", "type": "global"},
                {"id": "2", "key": "ENG", "name": "Engineering", "type": "global"},
            ]
        }
        
        spaces = api.get_spaces()
        
        assert len(spaces) == 2
        assert spaces[0].key == "DOCS"
        mock_client.get.assert_called_with("spaces", params={"limit": 25})
    
    def test_get_page(self, api, mock_client):
        """Test getting a page."""
        mock_client.get.return_value = {
            "id": "123",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}},
            "version": {"number": 1},
        }
        
        page = api.get_page("123")
        
        assert page.id == "123"
        assert page.title == "Test Page"
    
    def test_create_page(self, api, mock_client):
        """Test creating a page."""
        mock_client.post.return_value = {
            "id": "456",
            "title": "New Page",
            "body": {"storage": {"value": "<p>New content</p>"}},
            "version": {"number": 1},
        }
        
        page = api.create_page(
            space_id="SPACE123",
            title="New Page",
            body="<p>New content</p>",
        )
        
        assert page.id == "456"
        mock_client.post.assert_called_once()
    
    def test_update_page(self, api, mock_client):
        """Test updating a page."""
        mock_client.put.return_value = {
            "id": "123",
            "title": "Updated Page",
            "body": {"storage": {"value": "<p>Updated</p>"}},
            "version": {"number": 2},
        }
        
        page = api.update_page(
            page_id="123",
            title="Updated Page",
            body="<p>Updated</p>",
            version_number=1,
        )
        
        assert page.version.number == 2
        mock_client.put.assert_called_once()
    
    def test_page_to_markdown(self, api):
        """Test converting page to markdown."""
        page = ConfluencePage(
            id="123",
            title="Test",
            body="<h1>Header</h1><p>Paragraph</p>",
            spaceId="SPACE",
        )
        page.version = ConfluenceVersion(number=1)
        
        md = api.page_to_markdown(page)
        
        assert "title:" in md
        assert "page_id:" in md
        assert "Header" in md
    
    def test_markdown_to_storage(self, api):
        """Test converting markdown to storage format."""
        md = """---
title: "Test"
page_id: "123"
---

# Header

This is a paragraph.
"""
        
        storage = api.markdown_to_storage(md)
        
        assert "<h1>" in storage or "Header" in storage
        assert "paragraph" in storage.lower()
    
    def test_diff_pages(self, api):
        """Test diffing local vs remote."""
        remote = ConfluencePage(
            id="123",
            title="Test",
            body="<p>Original</p>",
        )
        remote.version = ConfluenceVersion(number=1)
        
        local = """---
title: "Test"
page_id: "123"
version: 1
---

Modified content
"""
        
        diff = api.diff_pages(local, remote)
        
        assert diff["has_changes"] is True
        assert "diff_lines" in diff

