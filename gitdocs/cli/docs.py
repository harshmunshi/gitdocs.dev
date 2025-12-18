"""gitdocs docs commands - Confluence documentation management."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Confirm
from rich.syntax import Syntax

from gitdocs.core.app import get_context
from gitdocs.core.errors import ConfigError, ConfluenceError
from gitdocs.atlassian.confluence_api import ConfluenceAPI

console = Console()

app = typer.Typer(
    name="docs",
    help="Manage Confluence documentation.",
)


def _get_confluence_api() -> ConfluenceAPI:
    """Get Confluence API instance from context."""
    ctx = get_context()
    return ConfluenceAPI(ctx.confluence)


@app.command(name="spaces")
def spaces_command(
    limit: int = typer.Option(25, "--limit", "-n"),
) -> None:
    """
    List accessible Confluence spaces.
    """
    try:
        api = _get_confluence_api()
        
        spaces = api.get_spaces(limit=limit)
        
        if not spaces:
            console.print("[yellow]No spaces found.[/]")
            return
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Key", style="green")
        table.add_column("Name")
        table.add_column("Type", style="dim")
        
        for space in spaces:
            table.add_row(space.key, space.name, space.type)
        
        console.print(table)
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="tree")
def tree_command(
    space_key: Optional[str] = typer.Option(
        None,
        "--space",
        "-s",
        help="Space key (uses default from config if not provided)",
    ),
    max_depth: int = typer.Option(
        3,
        "--depth",
        "-d",
        help="Maximum tree depth",
    ),
) -> None:
    """
    Display page tree for a Confluence space.
    
    Example:
    
        gitdocs docs tree --space DOCS
    """
    try:
        api = _get_confluence_api()
        ctx = get_context()
        
        # Get space key
        key = space_key or (ctx.config.confluence.space_key if ctx.config.confluence else None)
        if not key:
            console.print("[red]No space key provided.[/]")
            console.print("Use --space or set a default in .gitdocs.yml")
            raise typer.Exit(1)
        
        console.print(f"[dim]Fetching page tree for space: {key}[/]\n")
        
        page_tree = api.get_page_tree(key, max_depth=max_depth)
        
        if not page_tree.root_pages:
            console.print(f"[yellow]No pages found in space {key}[/]")
            return
        
        # Build rich tree
        tree = Tree(f"[bold cyan]{key}[/]")
        
        def add_pages(parent_tree: Tree, pages: list) -> None:
            for page in pages:
                node = parent_tree.add(f"[green]{page.title}[/] [dim]({page.id})[/]")
                if page.children:
                    add_pages(node, page.children)
        
        add_pages(tree, page_tree.root_pages)
        
        console.print(tree)
        console.print(f"\n[dim]Total pages: {page_tree.total_pages}[/]")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="show")
def show_command(
    page_id: str = typer.Argument(..., help="Page ID or title"),
    space_key: Optional[str] = typer.Option(
        None,
        "--space",
        "-s",
        help="Space key (required if using title instead of ID)",
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: markdown, html, or raw",
    ),
) -> None:
    """
    Show a Confluence page.
    
    Example:
    
        gitdocs docs show 12345678
        gitdocs docs show "Getting Started" --space DOCS
    """
    try:
        api = _get_confluence_api()
        ctx = get_context()
        
        # Try to get page by ID or title
        page = None
        if page_id.isdigit():
            page = api.get_page(page_id)
        else:
            # It's a title, need space key
            key = space_key or (ctx.config.confluence.space_key if ctx.config.confluence else None)
            if not key:
                console.print("[red]Space key required when using page title.[/]")
                raise typer.Exit(1)
            
            page = api.get_page_by_title(key, page_id)
            if not page:
                console.print(f"[red]Page not found:[/] {page_id}")
                raise typer.Exit(1)
        
        # Display
        console.print(Panel.fit(
            f"[bold cyan]{page.title}[/]",
            subtitle=f"ID: {page.id} | Version: {page.version.number if page.version else '?'}",
            border_style="cyan",
        ))
        
        if format == "markdown":
            md_content = api.page_to_markdown(page)
            console.print(Syntax(md_content, "markdown"))
        elif format == "html":
            console.print(Syntax(page.body, "html"))
        else:
            console.print(page.body)
        
        # URL
        if ctx.config.confluence:
            url = f"{ctx.config.confluence.base_url}/wiki/spaces/{page.space_id}/pages/{page.id}"
            console.print(f"\n[dim]URL:[/] {url}")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="pull")
def pull_command(
    page_id: str = typer.Argument(..., help="Page ID"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to {title}.md)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file",
    ),
) -> None:
    """
    Pull a Confluence page to local markdown file.
    
    Example:
    
        gitdocs docs pull 12345678
        gitdocs docs pull 12345678 -o docs/guide.md
    """
    try:
        api = _get_confluence_api()
        
        console.print(f"[dim]Fetching page {page_id}...[/]")
        page = api.get_page(page_id)
        
        # Determine output path
        if output:
            out_path = output
        else:
            # Sanitize title for filename
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in page.title)
            safe_title = safe_title.strip().replace(" ", "-").lower()
            out_path = Path(f"{safe_title}.md")
        
        # Check if exists
        if out_path.exists() and not force:
            if not Confirm.ask(f"[yellow]{out_path} exists.[/] Overwrite?", default=False):
                console.print("Aborted.")
                raise typer.Exit(0)
        
        # Convert and save
        md_content = api.page_to_markdown(page)
        out_path.write_text(md_content)
        
        console.print(f"[green]✓[/] Saved to {out_path}")
        console.print(f"  Title: {page.title}")
        console.print(f"  Version: {page.version.number if page.version else '?'}")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="push")
def push_command(
    file: Path = typer.Argument(..., help="Markdown file to push"),
    page_id: Optional[str] = typer.Option(
        None,
        "--page-id",
        "-p",
        help="Target page ID (reads from frontmatter if not provided)",
    ),
    message: str = typer.Option(
        "",
        "--message",
        "-m",
        help="Version message",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show diff without making changes",
    ),
) -> None:
    """
    Push a local markdown file to Confluence.
    
    Example:
    
        gitdocs docs push docs/guide.md --dry-run
        gitdocs docs push docs/guide.md -m "Updated installation steps"
    """
    try:
        api = _get_confluence_api()
        
        if not file.exists():
            console.print(f"[red]File not found:[/] {file}")
            raise typer.Exit(1)
        
        content = file.read_text()
        
        # Parse frontmatter for page ID
        target_id = page_id
        title = None
        if content.startswith("---"):
            import yaml
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if not target_id and frontmatter.get("page_id"):
                        target_id = frontmatter["page_id"]
                    if frontmatter.get("title"):
                        title = frontmatter["title"]
                except yaml.YAMLError:
                    pass
        
        if not target_id:
            console.print("[red]No page ID provided.[/]")
            console.print("Use --page-id or include page_id in markdown frontmatter.")
            raise typer.Exit(1)
        
        # Get current page
        console.print(f"[dim]Fetching current version of page {target_id}...[/]")
        remote_page = api.get_page(target_id)
        
        title = title or remote_page.title
        
        # Show diff
        diff_info = api.diff_pages(content, remote_page)
        
        if not diff_info["has_changes"]:
            console.print("[green]No changes detected.[/]")
            return
        
        console.print(Panel.fit("[bold]Changes detected[/]", border_style="yellow"))
        for line in diff_info["diff_lines"][:50]:  # Show first 50 lines
            if line.startswith("+"):
                console.print(f"[green]{line}[/]")
            elif line.startswith("-"):
                console.print(f"[red]{line}[/]")
            else:
                console.print(f"[dim]{line}[/]")
        
        if len(diff_info["diff_lines"]) > 50:
            console.print(f"[dim]... and {len(diff_info['diff_lines']) - 50} more lines[/]")
        
        if dry_run:
            console.print("\n[yellow]Dry run:[/] No changes made.")
            return
        
        # Confirm
        if not Confirm.ask("\nPush changes?", default=False):
            console.print("Aborted.")
            raise typer.Exit(0)
        
        # Convert to storage format and update
        storage_body = api.markdown_to_storage(content)
        current_version = remote_page.version.number if remote_page.version else 1
        
        updated = api.update_page(
            page_id=target_id,
            title=title,
            body=storage_body,
            version_number=current_version,
            version_message=message or f"Updated via gitdocs",
        )
        
        console.print(f"[green]✓[/] Page updated successfully!")
        console.print(f"  New version: {updated.version.number if updated.version else '?'}")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e}")
        raise typer.Exit(1)
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)


@app.command(name="search")
def search_command(
    query: str = typer.Argument(..., help="Search text"),
    space_key: Optional[str] = typer.Option(
        None,
        "--space",
        "-s",
        help="Limit search to space",
    ),
    limit: int = typer.Option(25, "--limit", "-n"),
) -> None:
    """
    Search Confluence pages.
    """
    try:
        api = _get_confluence_api()
        
        # For now, just list pages and filter
        # TODO: Use CQL search when available
        ctx = get_context()
        key = space_key or (ctx.config.confluence.space_key if ctx.config.confluence else None)
        
        if key:
            space = api.get_space(key)
            pages = api.get_pages_in_space(space.id, limit=100)
            
            # Simple text filter
            query_lower = query.lower()
            matching = [p for p in pages if query_lower in p.title.lower()]
            
            if not matching:
                console.print(f"[yellow]No pages matching '{query}' in space {key}[/]")
                return
            
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim")
            table.add_column("Title", style="green")
            
            for page in matching[:limit]:
                table.add_row(page.id, page.title)
            
            console.print(table)
        else:
            console.print("[red]Space key required for search.[/]")
            raise typer.Exit(1)
        
    except ConfluenceError as e:
        console.print(f"[red]Confluence error:[/] {e}")
        raise typer.Exit(1)

