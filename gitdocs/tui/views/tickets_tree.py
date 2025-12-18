"""Tickets tree view for TUI."""

from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.message import Message
from textual import work

from gitdocs.core.app import get_context
from gitdocs.core.errors import ConfigError
from gitdocs.atlassian.jira_api import JiraAPI
from gitdocs.atlassian.models import JiraIssue


class TicketsTree(Tree):
    """Tree widget displaying Jira tickets."""
    
    class IssueSelected(Message):
        """Posted when an issue is selected."""
        
        def __init__(self, issue_key: str) -> None:
            self.issue_key = issue_key
            super().__init__()
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("Tickets", *args, **kwargs)
        self._issues: dict[str, JiraIssue] = {}
        self._api: JiraAPI | None = None
    
    def on_mount(self) -> None:
        """Load issues on mount."""
        self.root.expand()
        self.load_issues()
    
    @work(exclusive=True)
    async def load_issues(self) -> None:
        """Load issues from Jira."""
        try:
            ctx = get_context()
            if not ctx.config.jira:
                self.root.add_leaf("⚠ Jira not configured")
                return
            
            self._api = JiraAPI(ctx.jira)
            
            # Clear existing
            self.root.remove_children()
            
            # Add loading indicator
            loading = self.root.add_leaf("Loading...")
            
            # Get my issues
            result = self._api.search_my_issues(
                project_key=ctx.config.jira.project_key,
                max_results=30,
            )
            
            # Remove loading
            loading.remove()
            
            if not result.issues:
                self.root.add_leaf("No issues assigned to you")
                return
            
            # Group by status
            by_status: dict[str, list[JiraIssue]] = {}
            for issue in result.issues:
                status = issue.status.name if issue.status else "Unknown"
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(issue)
                self._issues[issue.key] = issue
            
            # Add to tree
            for status, issues in by_status.items():
                status_node = self.root.add(f"[bold]{status}[/] ({len(issues)})")
                status_node.expand()
                
                for issue in issues:
                    icon = self._get_type_icon(issue)
                    label = f"{icon} {issue.key}: {issue.summary[:40]}"
                    if len(issue.summary) > 40:
                        label += "..."
                    status_node.add_leaf(label, data=issue.key)
            
        except ConfigError as e:
            self.root.add_leaf(f"⚠ Config error: {e}")
        except Exception as e:
            self.root.add_leaf(f"⚠ Error: {e}")
    
    def refresh_issues(self) -> None:
        """Refresh issues from Jira."""
        self.root.remove_children()
        self.load_issues()
    
    def _get_type_icon(self, issue: JiraIssue) -> str:
        """Get icon for issue type."""
        if not issue.issue_type:
            return "📋"
        
        type_name = issue.issue_type.name.lower()
        if "bug" in type_name:
            return "🐛"
        elif "story" in type_name:
            return "📖"
        elif "task" in type_name:
            return "✅"
        elif "epic" in type_name:
            return "🎯"
        elif "sub" in type_name:
            return "📎"
        else:
            return "📋"
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection."""
        if event.node.data:
            issue_key = event.node.data
            self.post_message(self.IssueSelected(issue_key))
    
    def action_cursor_down(self) -> None:
        """Move cursor down."""
        self.select_next_node()
    
    def action_cursor_up(self) -> None:
        """Move cursor up."""
        self.select_previous_node()
    
    def select_next_node(self) -> None:
        """Select next visible node."""
        if self.cursor_node:
            # Get all visible nodes
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

