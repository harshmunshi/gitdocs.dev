"""Search modal component for TUI."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static

from gitdocs.atlassian.jira_api import JiraAPI
from gitdocs.core.app import get_context


class SearchModal(ModalScreen):
    """Modal for searching tickets and docs."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("enter", "select", "Select", show=True),
    ]

    DEFAULT_CSS = """
    SearchModal {
        align: center middle;
    }
    
    SearchModal > Container {
        width: 60%;
        max-width: 80;
        height: auto;
        max-height: 70%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    
    SearchModal Input {
        margin-bottom: 1;
    }
    
    SearchModal ListView {
        height: auto;
        max-height: 20;
        border: solid $primary-lighten-2;
    }
    
    SearchModal ListItem {
        padding: 0 1;
    }
    
    SearchModal .result-key {
        color: $accent;
        text-style: bold;
    }
    
    SearchModal .result-summary {
        color: $text;
    }
    
    SearchModal .no-results {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._results: list[dict] = []

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("[bold]Search Jira[/]")
            yield Input(placeholder="Search issues...", id="search-input")
            yield ListView(id="results-list")

    def on_mount(self) -> None:
        """Focus search input on mount."""
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()
        if len(query) >= 2:
            self._search(query)
        else:
            self._clear_results()

    @work(exclusive=True)
    async def _search(self, query: str) -> None:
        """Perform search."""
        results_list = self.query_one("#results-list", ListView)

        try:
            ctx = get_context()
            if not ctx.config.jira:
                return

            api = JiraAPI(ctx.jira)

            # Search using text
            jql = f'text ~ "{query}" ORDER BY updated DESC'
            result = api.search_issues(jql, max_results=10)

            # Clear and populate
            results_list.clear()
            self._results = []

            if not result.issues:
                results_list.append(
                    ListItem(Static("[dim]No results found[/]", classes="no-results"))
                )
                return

            for issue in result.issues:
                self._results.append(
                    {
                        "key": issue.key,
                        "summary": issue.summary,
                        "status": issue.status.name if issue.status else "",
                    }
                )

                item = ListItem(
                    Static(
                        f"[cyan]{issue.key}[/] {issue.summary[:50]}... "
                        f"[dim]({issue.status.name if issue.status else '-'})[/]"
                    )
                )
                results_list.append(item)

        except Exception as e:
            results_list.clear()
            results_list.append(ListItem(Static(f"[red]Error: {e}[/]")))

    def _clear_results(self) -> None:
        """Clear search results."""
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()
        self._results = []

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle result selection."""
        if event.item and self._results:
            try:
                idx = event.item.index
                if idx is not None and idx < len(self._results):
                    result = self._results[idx]
                    # TODO: Navigate to selected issue
                    self.dismiss(result)
            except Exception:
                pass

    def action_select(self) -> None:
        """Select current result."""
        results_list = self.query_one("#results-list", ListView)
        if results_list.highlighted_child:
            idx = results_list.index
            if idx is not None and idx < len(self._results):
                self.dismiss(self._results[idx])

    def action_dismiss(self) -> None:
        """Close modal."""
        self.dismiss(None)
