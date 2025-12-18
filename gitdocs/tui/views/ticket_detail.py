"""Ticket detail view for TUI."""

from textual.widgets import Static, Markdown
from textual.containers import Vertical, ScrollableContainer
from textual.reactive import reactive
from textual import work

from gitdocs.core.app import get_context
from gitdocs.atlassian.jira_api import JiraAPI
from gitdocs.atlassian.confluence_api import ConfluenceAPI


class TicketDetail(ScrollableContainer):
    """Detail view showing ticket or page content."""
    
    DEFAULT_CSS = """
    TicketDetail {
        padding: 1 2;
    }
    
    TicketDetail .header {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    
    TicketDetail .meta {
        color: $text-muted;
    }
    
    TicketDetail .label {
        color: $text-disabled;
    }
    
    TicketDetail .content {
        margin-top: 1;
    }
    
    TicketDetail .section-title {
        text-style: bold;
        margin-top: 1;
        color: $accent;
    }
    """
    
    current_key: reactive[str] = reactive("")
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._content = Static("Select a ticket or page to view details", classes="content")
    
    def compose(self):
        yield self._content
    
    def show_issue(self, issue_key: str) -> None:
        """Display a Jira issue."""
        self.current_key = issue_key
        self._load_issue(issue_key)
    
    def show_page(self, page_id: str, page_title: str) -> None:
        """Display a Confluence page."""
        self.current_key = page_id
        self._load_page(page_id, page_title)
    
    @work(exclusive=True)
    async def _load_issue(self, issue_key: str) -> None:
        """Load and display issue details."""
        self._content.update(f"Loading {issue_key}...")
        
        try:
            ctx = get_context()
            api = JiraAPI(ctx.jira)
            
            issue = api.get_issue(issue_key)
            comments = api.get_issue_comments(issue_key, max_results=5)
            
            # Build display content
            lines = [
                f"[bold cyan]{issue.key}[/]",
                f"[bold]{issue.summary}[/]",
                "",
                f"[dim]Status:[/] {issue.status.name if issue.status else '-'}",
                f"[dim]Type:[/] {issue.issue_type.name if issue.issue_type else '-'}",
                f"[dim]Priority:[/] {issue.priority.name if issue.priority else '-'}",
                f"[dim]Assignee:[/] {issue.assignee.display_name if issue.assignee else 'Unassigned'}",
                f"[dim]Reporter:[/] {issue.reporter.display_name if issue.reporter else '-'}",
            ]
            
            if issue.labels:
                lines.append(f"[dim]Labels:[/] {', '.join(issue.labels)}")
            
            if issue.description:
                lines.extend([
                    "",
                    "[bold yellow]Description[/]",
                    "─" * 40,
                    issue.description[:1000],
                ])
                if len(issue.description) > 1000:
                    lines.append("...")
            
            if comments:
                lines.extend([
                    "",
                    "[bold yellow]Recent Comments[/]",
                    "─" * 40,
                ])
                for comment in comments[:3]:
                    author = comment.author.display_name if comment.author else "Unknown"
                    lines.append(f"[cyan]{author}[/]:")
                    lines.append(comment.body[:200])
                    if len(comment.body) > 200:
                        lines.append("...")
                    lines.append("")
            
            # URL
            if ctx.config.jira:
                url = f"{ctx.config.jira.base_url}/browse/{issue.key}"
                lines.extend(["", f"[dim]URL: {url}[/]"])
            
            self._content.update("\n".join(lines))
            
        except Exception as e:
            self._content.update(f"[red]Error loading issue:[/] {e}")
    
    @work(exclusive=True)
    async def _load_page(self, page_id: str, page_title: str) -> None:
        """Load and display Confluence page."""
        self._content.update(f"Loading {page_title}...")
        
        try:
            ctx = get_context()
            api = ConfluenceAPI(ctx.confluence)
            
            page = api.get_page(page_id)
            
            # Convert to markdown for display
            md_content = api.page_to_markdown(page)
            
            # Build display
            lines = [
                f"[bold cyan]{page.title}[/]",
                f"[dim]ID: {page.id} | Version: {page.version.number if page.version else '?'}[/]",
                "",
                "─" * 40,
                md_content[:2000],
            ]
            
            if len(md_content) > 2000:
                lines.append("\n[dim]... content truncated ...[/]")
            
            self._content.update("\n".join(lines))
            
        except Exception as e:
            self._content.update(f"[red]Error loading page:[/] {e}")
    
    def clear(self) -> None:
        """Clear the detail view."""
        self.current_key = ""
        self._content.update("Select a ticket or page to view details")

