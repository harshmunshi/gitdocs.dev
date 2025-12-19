"""gitdocs init command - set up gitdocs for a repository."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from gitdocs.core.config import ConfluenceConfig, JiraConfig, RepoConfig, save_repo_config
from gitdocs.core.errors import RepoNotFoundError
from gitdocs.core.paths import ensure_gitignore_entry, get_repo_config_path, get_repo_root
from gitdocs.core.secrets import set_confluence_api_token, set_jira_api_token

console = Console()


def init_command(
    jira_url: str | None = typer.Option(
        None,
        "--jira-url",
        help="Jira Cloud URL (e.g., https://company.atlassian.net)",
    ),
    jira_email: str | None = typer.Option(
        None,
        "--jira-email",
        help="Jira account email",
    ),
    jira_project: str | None = typer.Option(
        None,
        "--jira-project",
        help="Default Jira project key",
    ),
    confluence_url: str | None = typer.Option(
        None,
        "--confluence-url",
        help="Confluence Cloud URL",
    ),
    confluence_email: str | None = typer.Option(
        None,
        "--confluence-email",
        help="Confluence account email",
    ),
    confluence_space: str | None = typer.Option(
        None,
        "--confluence-space",
        help="Default Confluence space key",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive prompts",
    ),
) -> None:
    """
    Initialize gitdocs for the current repository.

    This creates a .gitdocs.yml configuration file in the repo root
    and stores API credentials securely.
    """
    console.print(
        Panel.fit(
            "[bold cyan]gitdocs init[/]\n\n" "Setting up gitdocs for this repository.",
            border_style="cyan",
        )
    )

    # Check we're in a git repo
    try:
        repo_root = get_repo_root()
        console.print(f"\n[dim]Repository root:[/] {repo_root}")
    except RepoNotFoundError:
        console.print("[red]Error:[/] Not in a git repository.")
        console.print("Please run this command from within a git repository.")
        raise typer.Exit(1)

    # Check for existing config
    config_path = get_repo_config_path(repo_root)
    if config_path.exists():
        if not non_interactive:
            if not Confirm.ask(
                f"\n[yellow]Config already exists at {config_path}.[/] Overwrite?",
                default=False,
            ):
                console.print("Aborted.")
                raise typer.Exit(0)

    # Interactive prompts if not provided
    console.print("\n[bold]Jira Configuration[/]")

    if not jira_url and not non_interactive:
        jira_url = Prompt.ask(
            "  Jira Cloud URL",
            default="https://company.atlassian.net",
        )

    if not jira_email and not non_interactive and jira_url:
        jira_email = Prompt.ask("  Jira email")

    if not jira_project and not non_interactive and jira_url:
        jira_project = (
            Prompt.ask(
                "  Default project key",
                default="",
            )
            or None
        )

    # Get Jira API token
    jira_token = None
    if jira_url and jira_email and not non_interactive:
        console.print("\n  [dim]Create an API token at:[/]")
        console.print("  [link]https://id.atlassian.com/manage-profile/security/api-tokens[/link]")
        jira_token = Prompt.ask("  Jira API token", password=True)

    console.print("\n[bold]Confluence Configuration[/]")

    # Default Confluence URL to same as Jira if on same Atlassian instance
    default_confluence_url = jira_url if jira_url else "https://company.atlassian.net"

    if not confluence_url and not non_interactive:
        confluence_url = Prompt.ask(
            "  Confluence Cloud URL",
            default=default_confluence_url,
        )

    # Default email to Jira email
    default_conf_email = jira_email or ""
    if not confluence_email and not non_interactive and confluence_url:
        confluence_email = Prompt.ask(
            "  Confluence email",
            default=default_conf_email,
        )

    if not confluence_space and not non_interactive and confluence_url:
        confluence_space = (
            Prompt.ask(
                "  Default space key",
                default="",
            )
            or None
        )

    # Get Confluence API token (can reuse Jira token if same domain)
    confluence_token = None
    if confluence_url and confluence_email and not non_interactive:
        if (
            jira_url
            and jira_url.split("//")[1].split("/")[0] == confluence_url.split("//")[1].split("/")[0]
        ):
            if Confirm.ask("  Use same API token as Jira?", default=True):
                confluence_token = jira_token

        if not confluence_token:
            confluence_token = Prompt.ask("  Confluence API token", password=True)

    # Build config
    jira_config = None
    if jira_url and jira_email:
        jira_config = JiraConfig(
            base_url=jira_url,
            email=jira_email,
            project_key=jira_project,
        )

    confluence_config = None
    if confluence_url and confluence_email:
        confluence_config = ConfluenceConfig(
            base_url=confluence_url,
            email=confluence_email,
            space_key=confluence_space,
        )

    repo_config = RepoConfig(
        jira=jira_config,
        confluence=confluence_config,
    )

    # Save config
    console.print("\n[bold]Saving configuration...[/]")

    save_repo_config(repo_config, repo_root)
    console.print(f"  [green]✓[/] Created {config_path}")

    # Store credentials
    if jira_token:
        set_jira_api_token(jira_token)
        console.print("  [green]✓[/] Stored Jira API token")

    if confluence_token:
        set_confluence_api_token(confluence_token)
        console.print("  [green]✓[/] Stored Confluence API token")

    # Update .gitignore
    ensure_gitignore_entry(repo_root)
    console.print("  [green]✓[/] Updated .gitignore")

    # Final message
    console.print(
        Panel.fit(
            "[bold green]gitdocs initialized successfully![/]\n\n"
            "Next steps:\n"
            "  • Run [cyan]gitdocs config --test[/] to verify connectivity\n"
            "  • Run [cyan]gitdocs tickets ls[/] to list Jira issues\n"
            "  • Run [cyan]gitdocs docs tree[/] to browse Confluence\n"
            "  • Run [cyan]gitdocs[/] to launch the TUI",
            border_style="green",
        )
    )
