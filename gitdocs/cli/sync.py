"""gitdocs sync commands - LLM-assisted ticket/doc synchronization."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from gitdocs.core.app import get_context
from gitdocs.core.errors import ConfigError

console = Console()

app = typer.Typer(
    name="sync",
    help="Sync commits with Jira tickets (LLM-assisted).",
)


@app.command(name="suggest")
def suggest_command(
    commits: int = typer.Option(
        10,
        "--commits",
        "-n",
        help="Number of recent commits to analyze",
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        "-b",
        help="Branch to analyze (defaults to current)",
    ),
    show_diff: bool = typer.Option(
        False,
        "--diff",
        "-d",
        help="Include diff summaries in analysis",
    ),
) -> None:
    """
    Analyze recent commits and suggest Jira ticket updates.
    
    Uses LLM to:
    - Extract ticket references from commit messages
    - Summarize changes relevant to each ticket
    - Draft Jira comments for review
    
    Example:
    
        gitdocs sync suggest --commits 5
        gitdocs sync suggest --branch feature/login --diff
    """
    try:
        ctx = get_context()
        
        # Check LLM is available
        from gitdocs.core.secrets import get_openai_api_key
        if not get_openai_api_key():
            console.print("[yellow]Warning:[/] OpenAI API key not configured.")
            console.print("Run [cyan]gitdocs auth login openai[/] to enable LLM suggestions.")
            console.print("\n[dim]Falling back to pattern-based extraction...[/]\n")
        
        # Get recent commits
        console.print(f"[dim]Analyzing {commits} recent commits...[/]\n")
        
        git_repo = ctx.git
        recent_commits = git_repo.get_recent_commits(count=commits, branch=branch)
        
        if not recent_commits:
            console.print("[yellow]No commits found.[/]")
            return
        
        # Extract ticket references
        from gitdocs.store.mappings import extract_ticket_keys
        
        commit_tickets: dict[str, list[str]] = {}
        for commit in recent_commits:
            keys = extract_ticket_keys(commit.message, ctx.config.repo.commit_patterns)
            if keys:
                commit_tickets[commit.sha] = keys
        
        if not commit_tickets:
            console.print("[yellow]No ticket references found in commits.[/]")
            console.print("[dim]Tip: Include ticket keys like PROJ-123 in commit messages.[/]")
            return
        
        # Group by ticket
        ticket_commits: dict[str, list] = {}
        for commit in recent_commits:
            if commit.sha in commit_tickets:
                for key in commit_tickets[commit.sha]:
                    if key not in ticket_commits:
                        ticket_commits[key] = []
                    ticket_commits[key].append(commit)
        
        console.print(Panel.fit(
            f"[bold]Found {len(ticket_commits)} tickets with updates[/]",
            border_style="cyan",
        ))
        
        # Try LLM suggestions
        suggestions = []
        try:
            llm = ctx.llm
            
            for ticket_key, ticket_commit_list in ticket_commits.items():
                commit_summaries = "\n".join([
                    f"- {c.sha[:7]}: {c.message.split(chr(10))[0]}"
                    for c in ticket_commit_list
                ])
                
                # Get diff if requested
                diff_summary = ""
                if show_diff and ticket_commit_list:
                    diff_summary = git_repo.get_diff_summary(
                        ticket_commit_list[-1].sha,
                        ticket_commit_list[0].sha if len(ticket_commit_list) > 1 else "HEAD~1",
                    )
                
                suggestion = llm.suggest_ticket_update(
                    ticket_key=ticket_key,
                    commits=commit_summaries,
                    diff_summary=diff_summary,
                )
                
                if suggestion:
                    suggestions.append({
                        "ticket": ticket_key,
                        "commits": len(ticket_commit_list),
                        "comment": suggestion.comment,
                        "confidence": suggestion.confidence,
                    })
        except Exception as e:
            console.print(f"[yellow]LLM unavailable:[/] {e}")
            console.print("[dim]Showing basic commit info instead.[/]\n")
        
        # Display results
        if suggestions:
            for s in suggestions:
                confidence_color = "green" if s["confidence"] >= 0.7 else "yellow"
                console.print(f"\n[bold cyan]{s['ticket']}[/] ({s['commits']} commits)")
                console.print(f"Confidence: [{confidence_color}]{s['confidence']:.0%}[/]")
                console.print(Panel(s["comment"], title="Suggested comment", border_style="dim"))
        else:
            # Fallback: just show ticket-commit mapping
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Ticket", style="green")
            table.add_column("Commits")
            table.add_column("Latest Message")
            
            for ticket_key, ticket_commit_list in ticket_commits.items():
                latest = ticket_commit_list[0]
                msg = latest.message.split("\n")[0][:50]
                table.add_row(
                    ticket_key,
                    str(len(ticket_commit_list)),
                    msg + "..." if len(msg) == 50 else msg,
                )
            
            console.print(table)
            console.print("\n[dim]Configure OpenAI for AI-generated comment suggestions.[/]")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="apply")
def apply_command(
    ticket: str = typer.Argument(..., help="Ticket key to update"),
    message: Optional[str] = typer.Option(
        None,
        "--message",
        "-m",
        help="Comment message (uses suggestion if not provided)",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        "-n",
        help="Preview without posting (default: dry-run)",
    ),
) -> None:
    """
    Apply a suggested update to a Jira ticket.
    
    By default runs in dry-run mode. Use --no-dry-run to actually post.
    
    Example:
    
        gitdocs sync apply PROJ-123 -m "Implemented login feature"
        gitdocs sync apply PROJ-123 --no-dry-run
    """
    try:
        ctx = get_context()
        
        from gitdocs.atlassian.jira_api import JiraAPI
        api = JiraAPI(ctx.jira)
        
        # Get ticket info
        issue = api.get_issue(ticket)
        console.print(f"\n[bold cyan]{issue.key}[/] - {issue.summary}")
        console.print(f"Status: {issue.status.name if issue.status else '-'}")
        
        # Generate or use provided message
        comment_text = message
        if not comment_text:
            # Try to generate suggestion
            try:
                git_repo = ctx.git
                recent = git_repo.get_recent_commits(count=5)
                
                from gitdocs.store.mappings import extract_ticket_keys
                relevant = [
                    c for c in recent
                    if ticket in extract_ticket_keys(c.message, ctx.config.repo.commit_patterns)
                ]
                
                if relevant:
                    commits_str = "\n".join([
                        f"- {c.sha[:7]}: {c.message.split(chr(10))[0]}"
                        for c in relevant
                    ])
                    
                    llm = ctx.llm
                    suggestion = llm.suggest_ticket_update(ticket, commits_str, "")
                    if suggestion:
                        comment_text = suggestion.comment
            except Exception:
                pass
        
        if not comment_text:
            console.print("[red]No message provided and couldn't generate suggestion.[/]")
            raise typer.Exit(1)
        
        console.print("\n[bold]Comment to post:[/]")
        console.print(Panel(comment_text, border_style="dim"))
        
        if dry_run:
            console.print("\n[yellow]Dry run mode.[/] Use --no-dry-run to actually post.")
            return
        
        if not Confirm.ask("\nPost this comment?", default=False):
            console.print("Aborted.")
            raise typer.Exit(0)
        
        comment = api.add_comment(ticket, comment_text)
        console.print(f"[green]✓[/] Comment posted (ID: {comment.id})")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="status")
def status_command() -> None:
    """
    Show sync status between local commits and Jira tickets.
    """
    try:
        ctx = get_context()
        git_repo = ctx.git
        
        # Get current branch and recent commits
        branch = git_repo.get_current_branch()
        commits = git_repo.get_recent_commits(count=20)
        
        console.print(f"[bold]Branch:[/] {branch}")
        console.print(f"[bold]Commits analyzed:[/] {len(commits)}\n")
        
        from gitdocs.store.mappings import extract_ticket_keys
        
        # Extract all ticket references
        all_tickets: set[str] = set()
        for commit in commits:
            keys = extract_ticket_keys(commit.message, ctx.config.repo.commit_patterns)
            all_tickets.update(keys)
        
        if not all_tickets:
            console.print("[yellow]No ticket references found in recent commits.[/]")
            return
        
        console.print(f"[bold]Tickets referenced:[/] {', '.join(sorted(all_tickets))}")
        
        # TODO: Check if tickets have been updated with commit info
        # This would require tracking which commits have been synced
        
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

