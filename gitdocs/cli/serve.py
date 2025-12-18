"""gitdocs serve command - local web UI server."""

from typing import Optional

import typer
from rich.console import Console

console = Console()


def serve_command(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        "-p",
        help="Port to bind to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open browser automatically",
    ),
) -> None:
    """
    Start the local configuration web server.
    
    Provides a web interface for:
    - Viewing and editing configuration
    - Managing API keys and repo bindings  
    - Editing documentation style guides
    - Testing API connectivity
    
    Example:
    
        gitdocs serve
        gitdocs serve --port 9000 --no-open
    """
    import uvicorn
    import webbrowser
    from threading import Timer
    
    console.print(f"[bold cyan]Starting gitdocs server...[/]")
    console.print(f"  URL: [link]http://{host}:{port}[/link]")
    console.print(f"  Press [bold]Ctrl+C[/] to stop\n")
    
    def open_browser_delayed():
        webbrowser.open(f"http://{host}:{port}")
    
    if open_browser:
        # Open browser after a short delay
        Timer(1.5, open_browser_delayed).start()
    
    try:
        uvicorn.run(
            "gitdocs.web.server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/]")

