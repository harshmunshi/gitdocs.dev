"""Main Textual TUI application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, TabbedContent, TabPane

from gitdocs.tui.components.search import SearchModal
from gitdocs.tui.components.statusbar import StatusBar
from gitdocs.tui.views.docs_tree import DocsTree
from gitdocs.tui.views.ticket_detail import TicketDetail
from gitdocs.tui.views.tickets_tree import TicketsTree


class MainScreen(Screen):
    """Main application screen with split view."""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("/", "search", "Search", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("t", "focus_tickets", "Tickets", show=True),
        Binding("d", "focus_docs", "Docs", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("escape", "back", "Back", show=False),
    ]

    CSS = """
    MainScreen {
        layout: horizontal;
    }
    
    #sidebar {
        width: 35%;
        min-width: 30;
        max-width: 60;
        border-right: solid $primary;
    }
    
    #main-content {
        width: 65%;
    }
    
    #detail-view {
        padding: 1 2;
    }
    
    .tree-container {
        height: 100%;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="sidebar"):
                with TabbedContent(initial="tickets"):
                    with TabPane("Tickets", id="tickets"):
                        yield TicketsTree(id="tickets-tree", classes="tree-container")
                    with TabPane("Docs", id="docs"):
                        yield DocsTree(id="docs-tree", classes="tree-container")

            with Vertical(id="main-content"):
                yield TicketDetail(id="detail-view")

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        self.query_one("#tickets-tree", TicketsTree).focus()

    def action_search(self) -> None:
        """Open search modal."""
        self.app.push_screen(SearchModal())

    def action_refresh(self) -> None:
        """Refresh current view."""
        # Find focused tree and refresh
        try:
            tickets_tree = self.query_one("#tickets-tree", TicketsTree)
            if tickets_tree.has_focus:
                tickets_tree.refresh_issues()
                self.notify("Refreshing tickets...")
                return
        except Exception:
            pass

        try:
            docs_tree = self.query_one("#docs-tree", DocsTree)
            if docs_tree.has_focus:
                docs_tree.refresh_pages()
                self.notify("Refreshing docs...")
        except Exception:
            pass

    def action_focus_tickets(self) -> None:
        """Focus tickets tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "tickets"
        self.query_one("#tickets-tree", TicketsTree).focus()

    def action_focus_docs(self) -> None:
        """Focus docs tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "docs"
        self.query_one("#docs-tree", DocsTree).focus()

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "Keybindings: j/k=navigate, Enter=select, t=tickets, d=docs, /=search, r=refresh, q=quit",
            timeout=5,
        )

    def action_cursor_down(self) -> None:
        """Move cursor down (vim-like)."""
        focused = self.focused
        if hasattr(focused, "action_cursor_down"):
            focused.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim-like)."""
        focused = self.focused
        if hasattr(focused, "action_cursor_up"):
            focused.action_cursor_up()

    def on_tickets_tree_issue_selected(self, event: "TicketsTree.IssueSelected") -> None:
        """Handle issue selection."""
        detail = self.query_one("#detail-view", TicketDetail)
        detail.show_issue(event.issue_key)

    def on_docs_tree_page_selected(self, event: "DocsTree.PageSelected") -> None:
        """Handle page selection."""
        detail = self.query_one("#detail-view", TicketDetail)
        detail.show_page(event.page_id, event.page_title)


class GitDocsTUI(App):
    """Main gitdocs TUI application."""

    TITLE = "gitdocs"
    SUB_TITLE = "Jira & Confluence Terminal Interface"

    CSS = """
    Screen {
        background: $surface;
    }
    
    Header {
        background: $primary;
    }
    
    Footer {
        background: $primary-darken-2;
    }
    
    Tree {
        padding: 1;
    }
    
    Tree > .tree--cursor {
        background: $accent;
        color: $text;
    }
    
    Tree:focus > .tree--cursor {
        background: $accent;
    }
    
    #detail-view {
        background: $surface;
        border: solid $primary-lighten-1;
        margin: 1;
    }
    
    .issue-header {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    
    .issue-meta {
        color: $text-muted;
        margin-bottom: 1;
    }
    
    .issue-description {
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]

    def on_mount(self) -> None:
        """Initialize app."""
        self.push_screen(MainScreen())

    def action_quit(self) -> None:
        """Quit application."""
        self.exit()


if __name__ == "__main__":
    app = GitDocsTUI()
    app.run()
