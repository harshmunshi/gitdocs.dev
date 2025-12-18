"""Main Typer CLI application for gitdocs."""

import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from gitdocs import __version__

# Create the main app
app = typer.Typer(
    name="gitdocs",
    help="Developer-friendly CLI/TUI for Jira tickets and Confluence documentation.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold cyan]gitdocs[/] version [green]{__version__}[/]")
        raise typer.Exit()


def setup_logging(verbose: bool) -> None:
    """Configure logging with rich output."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=verbose,
            )
        ],
    )


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose output.",
    ),
) -> None:
    """
    gitdocs - Work with Jira tickets and Confluence docs from the terminal.
    
    Run [bold cyan]gitdocs[/] without arguments to launch the interactive TUI.
    
    [dim]Examples:[/]
    
      [green]gitdocs init[/]              Set up gitdocs for this repository
      [green]gitdocs tickets ls[/]        List Jira tickets
      [green]gitdocs docs tree[/]         Browse Confluence pages
      [green]gitdocs serve[/]             Start local configuration server
    """
    setup_logging(verbose)


# Import and register subcommands
from gitdocs.cli import init as init_cmd
from gitdocs.cli import auth as auth_cmd
from gitdocs.cli import tickets as tickets_cmd
from gitdocs.cli import docs as docs_cmd
from gitdocs.cli import serve as serve_cmd
from gitdocs.cli import sync as sync_cmd

app.add_typer(auth_cmd.app, name="auth")
app.add_typer(tickets_cmd.app, name="tickets")
app.add_typer(docs_cmd.app, name="docs")
app.command(name="init")(init_cmd.init_command)
app.command(name="serve")(serve_cmd.serve_command)
app.add_typer(sync_cmd.app, name="sync")


@app.command()
def tui() -> None:
    """
    Launch the interactive TUI.
    
    Opens a terminal interface with:
    - Left pane: ticket/docs tree view
    - Right pane: detail preview
    - Vim-like keybindings
    """
    from gitdocs.tui.main import GitDocsTUI
    
    tui_app = GitDocsTUI()
    tui_app.run()


@app.command(name="config")
def config_command(
    test: bool = typer.Option(
        False,
        "--test",
        "-t",
        help="Test configuration and API connectivity.",
    ),
    show: bool = typer.Option(
        False,
        "--show",
        "-s",
        help="Show current configuration.",
    ),
) -> None:
    """
    View and test gitdocs configuration.
    """
    from gitdocs.core.config import load_config
    from gitdocs.core.paths import get_repo_root, get_repo_config_path, get_user_config_path
    from gitdocs.core.errors import RepoNotFoundError
    from rich.table import Table
    from rich.panel import Panel
    import yaml
    
    if show:
        try:
            repo_root = get_repo_root()
            repo_config_path = get_repo_config_path(repo_root)
            
            console.print(Panel(f"[bold]Repository root:[/] {repo_root}"))
            
            if repo_config_path.exists():
                console.print(f"\n[bold cyan]Repo config[/] ({repo_config_path}):")
                console.print(repo_config_path.read_text())
            else:
                console.print(f"\n[yellow]No repo config found at {repo_config_path}[/]")
        except RepoNotFoundError:
            console.print("[yellow]Not in a git repository[/]")
        
        user_config_path = get_user_config_path()
        if user_config_path.exists():
            console.print(f"\n[bold cyan]User config[/] ({user_config_path}):")
            console.print(user_config_path.read_text())
        else:
            console.print(f"\n[yellow]No user config found at {user_config_path}[/]")
        
        return
    
    if test:
        from gitdocs.core.app import get_context
        from gitdocs.atlassian.jira_api import JiraAPI
        from gitdocs.atlassian.confluence_api import ConfluenceAPI
        
        console.print("[bold]Testing configuration...[/]\n")
        
        try:
            ctx = get_context()
            
            # Test Jira
            if ctx.config.jira:
                console.print("[cyan]Testing Jira connection...[/]")
                try:
                    jira_api = JiraAPI(ctx.jira)
                    user = jira_api.test_connection()
                    console.print(f"  [green]✓[/] Connected as: {user.get('displayName', 'Unknown')}")
                except Exception as e:
                    console.print(f"  [red]✗[/] Jira error: {e}")
            else:
                console.print("[yellow]  Jira not configured[/]")
            
            # Test Confluence
            if ctx.config.confluence:
                console.print("[cyan]Testing Confluence connection...[/]")
                try:
                    conf_api = ConfluenceAPI(ctx.confluence)
                    user = conf_api.test_connection()
                    console.print(f"  [green]✓[/] Connected as: {user.get('displayName', 'Unknown')}")
                except Exception as e:
                    console.print(f"  [red]✗[/] Confluence error: {e}")
            else:
                console.print("[yellow]  Confluence not configured[/]")
            
            console.print("\n[green]Configuration test complete![/]")
            
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(1)
        
        return
    
    # Default: show help
    console.print("Use [cyan]--show[/] to display config or [cyan]--test[/] to test connectivity.")


if __name__ == "__main__":
    app()

