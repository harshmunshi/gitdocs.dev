"""gitdocs tickets commands - Jira issue management."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm

from gitdocs.core.app import get_context
from gitdocs.core.errors import ConfigError, JiraError
from gitdocs.atlassian.jira_api import JiraAPI

console = Console()

app = typer.Typer(
    name="tickets",
    help="Manage Jira tickets.",
)


def _get_jira_api() -> JiraAPI:
    """Get Jira API instance from context."""
    ctx = get_context()
    return JiraAPI(ctx.jira)


@app.command(name="ls")
def list_command(
    jql: Optional[str] = typer.Option(
        None,
        "--jql",
        "-q",
        help="JQL query to filter issues",
    ),
    mine: bool = typer.Option(
        False,
        "--mine",
        "-m",
        help="Show only issues assigned to me",
    ),
    sprint: Optional[str] = typer.Option(
        None,
        "--sprint",
        "-s",
        help="Filter by sprint (e.g., 'current' for open sprints)",
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter by project key",
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status category (e.g., 'In Progress')",
    ),
    limit: int = typer.Option(
        25,
        "--limit",
        "-n",
        help="Maximum number of results",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, or keys",
    ),
) -> None:
    """
    List Jira issues.
    
    Examples:
    
        gitdocs tickets ls --mine
        gitdocs tickets ls --sprint current
        gitdocs tickets ls --jql "project = PROJ AND status = 'In Progress'"
    """
    try:
        api = _get_jira_api()
        ctx = get_context()
        
        # Build JQL
        if jql:
            query = jql
        else:
            parts = []
            
            if mine:
                parts.append("assignee = currentUser()")
            
            if sprint:
                if sprint.lower() == "current":
                    parts.append("sprint in openSprints()")
                else:
                    parts.append(f"sprint = '{sprint}'")
            
            proj = project or (ctx.config.jira.project_key if ctx.config.jira else None)
            if proj:
                parts.append(f"project = {proj}")
            
            if status:
                parts.append(f'statusCategory = "{status}"')
            
            query = " AND ".join(parts) if parts else "ORDER BY updated DESC"
            if parts:
                query += " ORDER BY updated DESC"
        
        console.print(f"[dim]Query:[/] {query}\n")
        
        result = api.search_issues(query, max_results=limit)
        
        if format == "keys":
            for issue in result.issues:
                console.print(issue.key)
            return
        
        if format == "json":
            import json
            data = [
                {
                    "key": i.key,
                    "summary": i.summary,
                    "status": i.status.name if i.status else "",
                    "assignee": i.assignee.display_name if i.assignee else "",
                    "type": i.issue_type.name if i.issue_type else "",
                }
                for i in result.issues
            ]
            console.print(json.dumps(data, indent=2))
            return
        
        # Table format
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Key", style="green", no_wrap=True)
        table.add_column("Type", style="dim")
        table.add_column("Status")
        table.add_column("Summary", max_width=50)
        table.add_column("Assignee", style="dim")
        
        for issue in result.issues:
            status_style = ""
            if issue.status:
                cat = issue.status.status_category
                if cat == "Done":
                    status_style = "green"
                elif cat == "In Progress":
                    status_style = "yellow"
            
            table.add_row(
                issue.key,
                issue.issue_type.name if issue.issue_type else "-",
                f"[{status_style}]{issue.status.name if issue.status else '-'}[/]",
                issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary,
                issue.assignee.display_name if issue.assignee else "-",
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(result.issues)} of {result.total} issues[/]")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except JiraError as e:
        console.print(f"[red]Jira error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="show")
def show_command(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comments: bool = typer.Option(
        False,
        "--comments",
        "-c",
        help="Show comments",
    ),
    transitions: bool = typer.Option(
        False,
        "--transitions",
        "-t",
        help="Show available transitions",
    ),
) -> None:
    """
    Show details of a Jira issue.
    
    Example:
    
        gitdocs tickets show PROJ-123 --comments
    """
    try:
        api = _get_jira_api()
        
        issue = api.get_issue(issue_key)
        
        # Header
        console.print(Panel.fit(
            f"[bold cyan]{issue.key}[/] - {issue.summary}",
            border_style="cyan",
        ))
        
        # Metadata
        meta_table = Table(show_header=False, box=None, padding=(0, 2))
        meta_table.add_column("Field", style="dim")
        meta_table.add_column("Value")
        
        meta_table.add_row("Type", issue.issue_type.name if issue.issue_type else "-")
        meta_table.add_row("Status", issue.status.name if issue.status else "-")
        meta_table.add_row("Priority", issue.priority.name if issue.priority else "-")
        meta_table.add_row("Assignee", issue.assignee.display_name if issue.assignee else "Unassigned")
        meta_table.add_row("Reporter", issue.reporter.display_name if issue.reporter else "-")
        meta_table.add_row("Project", issue.project.name if issue.project else "-")
        
        if issue.labels:
            meta_table.add_row("Labels", ", ".join(issue.labels))
        
        if issue.parent_key:
            meta_table.add_row("Parent", issue.parent_key)
        
        console.print(meta_table)
        
        # Description
        if issue.description:
            console.print("\n[bold]Description[/]")
            console.print(Panel(issue.description, border_style="dim"))
        
        # Comments
        if comments:
            console.print("\n[bold]Comments[/]")
            issue_comments = api.get_issue_comments(issue_key, max_results=10)
            
            if not issue_comments:
                console.print("[dim]No comments[/]")
            else:
                for comment in issue_comments:
                    author = comment.author.display_name if comment.author else "Unknown"
                    console.print(f"\n[cyan]{author}[/] [dim]({comment.created})[/]")
                    console.print(Panel(comment.body, border_style="dim"))
        
        # Transitions
        if transitions:
            console.print("\n[bold]Available Transitions[/]")
            trans = api.get_transitions(issue_key)
            
            if not trans:
                console.print("[dim]No transitions available[/]")
            else:
                for t in trans:
                    to_status = t.to_status.name if t.to_status else "?"
                    console.print(f"  [{t.id}] {t.name} → {to_status}")
        
        # URL
        ctx = get_context()
        if ctx.config.jira:
            url = f"{ctx.config.jira.base_url}/browse/{issue.key}"
            console.print(f"\n[dim]URL:[/] {url}")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except JiraError as e:
        console.print(f"[red]Jira error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="comment")
def comment_command(
    issue_key: str = typer.Argument(..., help="Issue key"),
    message: Optional[str] = typer.Option(
        None,
        "--message",
        "-m",
        help="Comment message (will prompt if not provided)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be posted without actually posting",
    ),
) -> None:
    """
    Add a comment to a Jira issue.
    
    Example:
    
        gitdocs tickets comment PROJ-123 -m "Fixed in commit abc123"
    """
    try:
        api = _get_jira_api()
        
        # Get message
        if not message:
            message = Prompt.ask("Enter comment")
        
        if not message:
            console.print("[red]No comment provided.[/]")
            raise typer.Exit(1)
        
        if dry_run:
            console.print(f"[yellow]Dry run:[/] Would add comment to {issue_key}:")
            console.print(Panel(message, border_style="dim"))
            return
        
        # Confirm
        console.print(f"Adding comment to [cyan]{issue_key}[/]:")
        console.print(Panel(message, border_style="dim"))
        
        if not Confirm.ask("Proceed?", default=True):
            console.print("Aborted.")
            raise typer.Exit(0)
        
        comment = api.add_comment(issue_key, message)
        console.print(f"[green]✓[/] Comment added (ID: {comment.id})")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except JiraError as e:
        console.print(f"[red]Jira error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="transition")
def transition_command(
    issue_key: str = typer.Argument(..., help="Issue key"),
    to_status: Optional[str] = typer.Option(
        None,
        "--to",
        "-t",
        help="Target status name or transition ID",
    ),
    comment: Optional[str] = typer.Option(
        None,
        "--comment",
        "-c",
        help="Add comment with transition",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would happen without making changes",
    ),
) -> None:
    """
    Transition a Jira issue to a new status.
    
    Example:
    
        gitdocs tickets transition PROJ-123 --to "In Progress"
        gitdocs tickets transition PROJ-123 --to Done -c "Completed implementation"
    """
    try:
        api = _get_jira_api()
        
        # Get available transitions
        transitions = api.get_transitions(issue_key)
        
        if not transitions:
            console.print(f"[yellow]No transitions available for {issue_key}[/]")
            raise typer.Exit(0)
        
        # Select transition
        selected = None
        if to_status:
            # Try to match by name or ID
            for t in transitions:
                if t.name.lower() == to_status.lower() or t.id == to_status:
                    selected = t
                    break
                if t.to_status and t.to_status.name.lower() == to_status.lower():
                    selected = t
                    break
            
            if not selected:
                console.print(f"[red]Transition not found:[/] {to_status}")
                console.print("\nAvailable transitions:")
                for t in transitions:
                    to_name = t.to_status.name if t.to_status else "?"
                    console.print(f"  • {t.name} → {to_name}")
                raise typer.Exit(1)
        else:
            # Interactive selection
            console.print(f"\nAvailable transitions for [cyan]{issue_key}[/]:")
            for i, t in enumerate(transitions, 1):
                to_name = t.to_status.name if t.to_status else "?"
                console.print(f"  [{i}] {t.name} → {to_name}")
            
            choice = Prompt.ask(
                "Select transition",
                choices=[str(i) for i in range(1, len(transitions) + 1)],
            )
            selected = transitions[int(choice) - 1]
        
        to_name = selected.to_status.name if selected.to_status else selected.name
        
        if dry_run:
            console.print(f"[yellow]Dry run:[/] Would transition {issue_key} to '{to_name}'")
            if comment:
                console.print(f"  With comment: {comment}")
            return
        
        # Confirm
        console.print(f"\nTransitioning [cyan]{issue_key}[/] → [green]{to_name}[/]")
        if comment:
            console.print(f"Comment: {comment}")
        
        if not Confirm.ask("Proceed?", default=True):
            console.print("Aborted.")
            raise typer.Exit(0)
        
        api.transition_issue(issue_key, selected.id, comment=comment)
        console.print(f"[green]✓[/] Issue transitioned to '{to_name}'")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except JiraError as e:
        console.print(f"[red]Jira error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="search")
def search_command(
    query: str = typer.Argument(..., help="Search text"),
    limit: int = typer.Option(25, "--limit", "-n"),
) -> None:
    """
    Search Jira issues by text.
    
    Example:
    
        gitdocs tickets search "login bug"
    """
    try:
        api = _get_jira_api()
        
        jql = f'text ~ "{query}" ORDER BY updated DESC'
        result = api.search_issues(jql, max_results=limit)
        
        if not result.issues:
            console.print("[yellow]No issues found.[/]")
            return
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Key", style="green")
        table.add_column("Status")
        table.add_column("Summary")
        
        for issue in result.issues:
            table.add_row(
                issue.key,
                issue.status.name if issue.status else "-",
                issue.summary[:60] + "..." if len(issue.summary) > 60 else issue.summary,
            )
        
        console.print(table)
        
    except JiraError as e:
        console.print(f"[red]Jira error:[/] {e}")
        raise typer.Exit(1)

