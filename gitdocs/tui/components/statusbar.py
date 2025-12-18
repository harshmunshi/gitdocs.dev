"""Status bar component for TUI."""

from textual.widgets import Static
from textual.reactive import reactive

from gitdocs.core.app import get_context
from gitdocs.core.errors import RepoNotFoundError


class StatusBar(Static):
    """Status bar showing current context and status."""
    
    DEFAULT_CSS = """
    StatusBar {
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }
    
    StatusBar .connected {
        color: $success;
    }
    
    StatusBar .disconnected {
        color: $error;
    }
    """
    
    message: reactive[str] = reactive("")
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._update_status()
    
    def _update_status(self) -> None:
        """Update status bar content."""
        parts = []
        
        # Get context info
        try:
            from gitdocs.core.paths import get_repo_root
            repo = get_repo_root()
            parts.append(f"📁 {repo.name}")
        except RepoNotFoundError:
            parts.append("📁 [dim]No repo[/]")
        
        try:
            ctx = get_context()
            
            # Jira status
            if ctx.config.jira:
                parts.append(f"[green]●[/] Jira")
            else:
                parts.append("[dim]○ Jira[/]")
            
            # Confluence status
            if ctx.config.confluence:
                parts.append(f"[green]●[/] Confluence")
            else:
                parts.append("[dim]○ Confluence[/]")
            
        except Exception:
            parts.append("[dim]○ Not configured[/]")
        
        # Add message if any
        if self.message:
            parts.append(f"│ {self.message}")
        
        self.update(" │ ".join(parts))
    
    def watch_message(self, message: str) -> None:
        """React to message changes."""
        self._update_status()
    
    def set_message(self, message: str, timeout: float = 3.0) -> None:
        """Set a temporary status message."""
        self.message = message
        
        if timeout > 0:
            self.set_timer(timeout, self._clear_message)
    
    def _clear_message(self) -> None:
        """Clear the status message."""
        self.message = ""

