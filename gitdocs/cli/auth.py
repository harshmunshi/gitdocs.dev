"""gitdocs auth commands - authentication management."""

from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from gitdocs.core.secrets import (
    set_jira_api_token,
    set_confluence_api_token,
    set_openai_api_key,
    get_jira_api_token,
    get_confluence_api_token,
    get_openai_api_key,
)
from gitdocs.core.errors import AuthError

console = Console()

app = typer.Typer(
    name="auth",
    help="Manage authentication credentials.",
)


@app.command(name="login")
def login_command(
    service: str = typer.Argument(
        ...,
        help="Service to authenticate: jira, confluence, or openai",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="API token (will prompt if not provided)",
    ),
) -> None:
    """
    Store API credentials for a service.
    
    Examples:
    
        gitdocs auth login jira
        gitdocs auth login confluence --token YOUR_TOKEN
        gitdocs auth login openai
    """
    service = service.lower()
    
    if service not in ("jira", "confluence", "openai"):
        console.print(f"[red]Unknown service:[/] {service}")
        console.print("Valid services: jira, confluence, openai")
        raise typer.Exit(1)
    
    if not token:
        if service == "jira":
            console.print("[dim]Create an API token at:[/]")
            console.print("[link]https://id.atlassian.com/manage-profile/security/api-tokens[/link]\n")
            token = Prompt.ask("Enter Jira API token", password=True)
        elif service == "confluence":
            console.print("[dim]Create an API token at:[/]")
            console.print("[link]https://id.atlassian.com/manage-profile/security/api-tokens[/link]\n")
            token = Prompt.ask("Enter Confluence API token", password=True)
        else:
            console.print("[dim]Get your API key at:[/]")
            console.print("[link]https://platform.openai.com/api-keys[/link]\n")
            token = Prompt.ask("Enter OpenAI API key", password=True)
    
    if not token:
        console.print("[red]No token provided.[/]")
        raise typer.Exit(1)
    
    try:
        if service == "jira":
            set_jira_api_token(token)
        elif service == "confluence":
            set_confluence_api_token(token)
        else:
            set_openai_api_key(token)
        
        console.print(f"[green]✓[/] {service.title()} credentials stored successfully.")
        
    except Exception as e:
        console.print(f"[red]Error storing credentials:[/] {e}")
        raise typer.Exit(1)


@app.command(name="status")
def status_command() -> None:
    """
    Check authentication status for all services.
    """
    console.print(Panel.fit("[bold]Authentication Status[/]", border_style="cyan"))
    
    # Check Jira
    try:
        token = get_jira_api_token()
        masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
        console.print(f"  [green]✓[/] Jira: configured ({masked})")
    except AuthError:
        console.print("  [yellow]○[/] Jira: not configured")
    
    # Check Confluence
    try:
        token = get_confluence_api_token()
        masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
        console.print(f"  [green]✓[/] Confluence: configured ({masked})")
    except AuthError:
        console.print("  [yellow]○[/] Confluence: not configured")
    
    # Check OpenAI
    key = get_openai_api_key()
    if key:
        masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
        console.print(f"  [green]✓[/] OpenAI: configured ({masked})")
    else:
        console.print("  [yellow]○[/] OpenAI: not configured (optional)")


@app.command(name="test")
def test_command(
    service: Optional[str] = typer.Argument(
        None,
        help="Service to test: jira, confluence, or all",
    ),
) -> None:
    """
    Test API connectivity with stored credentials.
    """
    from gitdocs.core.app import get_context
    from gitdocs.atlassian.jira_api import JiraAPI
    from gitdocs.atlassian.confluence_api import ConfluenceAPI
    
    services_to_test = []
    if service:
        service = service.lower()
        if service == "all":
            services_to_test = ["jira", "confluence"]
        elif service in ("jira", "confluence"):
            services_to_test = [service]
        else:
            console.print(f"[red]Unknown service:[/] {service}")
            raise typer.Exit(1)
    else:
        services_to_test = ["jira", "confluence"]
    
    try:
        ctx = get_context()
    except Exception as e:
        console.print(f"[red]Error loading config:[/] {e}")
        raise typer.Exit(1)
    
    all_passed = True
    
    for svc in services_to_test:
        console.print(f"\n[bold]Testing {svc.title()}...[/]")
        
        try:
            if svc == "jira":
                if not ctx.config.jira:
                    console.print("  [yellow]○[/] Jira not configured")
                    continue
                
                api = JiraAPI(ctx.jira)
                user = api.test_connection()
                console.print(f"  [green]✓[/] Connected as: {user.get('displayName', 'Unknown')}")
                console.print(f"  [dim]Email: {user.get('emailAddress', 'N/A')}[/]")
                
            elif svc == "confluence":
                if not ctx.config.confluence:
                    console.print("  [yellow]○[/] Confluence not configured")
                    continue
                
                api = ConfluenceAPI(ctx.confluence)
                user = api.test_connection()
                console.print(f"  [green]✓[/] Connected as: {user.get('displayName', 'Unknown')}")
                
        except Exception as e:
            console.print(f"  [red]✗[/] Connection failed: {e}")
            all_passed = False
    
    if all_passed:
        console.print("\n[green]All tests passed![/]")
    else:
        console.print("\n[yellow]Some tests failed.[/]")
        raise typer.Exit(1)

