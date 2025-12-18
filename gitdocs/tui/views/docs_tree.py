"""Docs tree view for TUI."""

from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.message import Message
from textual import work

from gitdocs.core.app import get_context
from gitdocs.core.errors import ConfigError
from gitdocs.atlassian.confluence_api import ConfluenceAPI
from gitdocs.atlassian.models import ConfluencePage


class DocsTree(Tree):
    """Tree widget displaying Confluence documentation."""
    
    class PageSelected(Message):
        """Posted when a page is selected."""
        
        def __init__(self, page_id: str, page_title: str) -> None:
            self.page_id = page_id
            self.page_title = page_title
            super().__init__()
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("Documentation", *args, **kwargs)
        self._pages: dict[str, ConfluencePage] = {}
        self._api: ConfluenceAPI | None = None
    
    def on_mount(self) -> None:
        """Load pages on mount."""
        self.root.expand()
        self.load_pages()
    
    @work(exclusive=True)
    async def load_pages(self) -> None:
        """Load pages from Confluence."""
        try:
            ctx = get_context()
            if not ctx.config.confluence:
                self.root.add_leaf("⚠ Confluence not configured")
                return
            
            space_key = ctx.config.confluence.space_key
            if not space_key:
                self.root.add_leaf("⚠ No space configured")
                return
            
            self._api = ConfluenceAPI(ctx.confluence)
            
            # Clear existing
            self.root.remove_children()
            
            # Add loading indicator
            loading = self.root.add_leaf("Loading...")
            
            # Get page tree
            page_tree = self._api.get_page_tree(space_key)
            
            # Remove loading
            loading.remove()
            
            if not page_tree.root_pages:
                self.root.add_leaf("No pages found")
                return
            
            # Update root label with space key
            self.root.label = f"📚 {space_key}"
            
            # Add pages recursively
            def add_pages(parent_node: TreeNode, pages: list[ConfluencePage]) -> None:
                for page in pages:
                    self._pages[page.id] = page
                    
                    label = f"📄 {page.title}"
                    if page.children:
                        node = parent_node.add(label, data=page.id)
                        add_pages(node, page.children)
                    else:
                        parent_node.add_leaf(label, data=page.id)
            
            add_pages(self.root, page_tree.root_pages)
            
            # Expand root
            self.root.expand()
            
        except ConfigError as e:
            self.root.add_leaf(f"⚠ Config error: {e}")
        except Exception as e:
            self.root.add_leaf(f"⚠ Error: {e}")
    
    def refresh_pages(self) -> None:
        """Refresh pages from Confluence."""
        self.root.remove_children()
        self.load_pages()
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection."""
        if event.node.data:
            page_id = event.node.data
            page = self._pages.get(page_id)
            title = page.title if page else "Unknown"
            self.post_message(self.PageSelected(page_id, title))
    
    def action_cursor_down(self) -> None:
        """Move cursor down."""
        self.select_next_node()
    
    def action_cursor_up(self) -> None:
        """Move cursor up."""
        self.select_previous_node()
    
    def select_next_node(self) -> None:
        """Select next visible node."""
        if self.cursor_node:
            visible = list(self._visible_nodes())
            try:
                idx = visible.index(self.cursor_node)
                if idx < len(visible) - 1:
                    self.select_node(visible[idx + 1])
            except ValueError:
                pass
    
    def select_previous_node(self) -> None:
        """Select previous visible node."""
        if self.cursor_node:
            visible = list(self._visible_nodes())
            try:
                idx = visible.index(self.cursor_node)
                if idx > 0:
                    self.select_node(visible[idx - 1])
            except ValueError:
                pass
    
    def _visible_nodes(self):
        """Iterate visible nodes."""
        def walk(node: TreeNode):
            yield node
            if node.is_expanded:
                for child in node.children:
                    yield from walk(child)
        
        yield from walk(self.root)

