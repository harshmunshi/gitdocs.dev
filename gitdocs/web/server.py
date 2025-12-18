"""FastAPI web server for local control plane."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gitdocs import __version__
from gitdocs.web.routes import router

# Create FastAPI app
app = FastAPI(
    title="gitdocs",
    description="Local control plane for gitdocs - Jira & Confluence integration",
    version=__version__,
)

# Include API routes
app.include_router(router, prefix="/api")

# Static files and templates
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Create directories if they don't exist
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Mount static files if directory exists and has files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main dashboard page."""
    # Check if we have a template
    template_path = TEMPLATES_DIR / "index.html"
    if template_path.exists():
        return templates.TemplateResponse("index.html", {"request": request})
    
    # Fallback to inline HTML
    return HTMLResponse(content=get_default_html())


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


def get_default_html() -> str:
    """Return default dashboard HTML."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gitdocs - Control Plane</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --border: #30363d;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }}
        
        h1 {{
            color: var(--accent);
            font-size: 1.5rem;
            font-weight: 600;
        }}
        
        .version {{
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        
        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1.5rem;
        }}
        
        .card h2 {{
            font-size: 1rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        
        .card p {{
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}
        
        .status {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.5rem 0;
        }}
        
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}
        
        .status-dot.connected {{ background: var(--accent-green); }}
        .status-dot.disconnected {{ background: var(--text-secondary); }}
        .status-dot.error {{ background: var(--accent-red); }}
        
        .btn {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            text-decoration: none;
            margin-top: 1rem;
        }}
        
        .btn:hover {{
            opacity: 0.9;
        }}
        
        .btn-secondary {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
        }}
        
        code {{
            background: var(--bg-tertiary);
            padding: 0.125rem 0.375rem;
            border-radius: 3px;
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.875rem;
        }}
        
        pre {{
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        
        .footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 gitdocs</h1>
            <span class="version">v{__version__}</span>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>🔧 Configuration</h2>
                <div class="status" id="jira-status">
                    <span class="status-dot disconnected"></span>
                    <span>Jira: Checking...</span>
                </div>
                <div class="status" id="confluence-status">
                    <span class="status-dot disconnected"></span>
                    <span>Confluence: Checking...</span>
                </div>
                <button class="btn" onclick="testConnections()">Test Connections</button>
            </div>
            
            <div class="card">
                <h2>📋 Quick Start</h2>
                <p>Get started with gitdocs:</p>
                <pre><code>gitdocs init           # Initialize repo
gitdocs tickets ls     # List tickets
gitdocs docs tree      # Browse docs
gitdocs tui            # Launch TUI</code></pre>
            </div>
            
            <div class="card">
                <h2>🔑 Authentication</h2>
                <p>Manage your API credentials:</p>
                <pre><code>gitdocs auth login jira
gitdocs auth login confluence
gitdocs auth status</code></pre>
            </div>
            
            <div class="card">
                <h2>🤖 LLM Integration</h2>
                <p>Enable AI-powered suggestions:</p>
                <pre><code>gitdocs auth login openai
gitdocs sync suggest
gitdocs sync apply PROJ-123</code></pre>
            </div>
        </div>
        
        <div class="card" style="margin-top: 1.5rem;">
            <h2>📖 API Endpoints</h2>
            <p style="margin-bottom: 1rem;">Access the REST API for integration:</p>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 0.5rem 0;"><code>GET /api/config</code></td>
                    <td style="color: var(--text-secondary);">Get current configuration</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 0.5rem 0;"><code>POST /api/config/test</code></td>
                    <td style="color: var(--text-secondary);">Test API connections</td>
                </tr>
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 0.5rem 0;"><code>GET /api/tickets</code></td>
                    <td style="color: var(--text-secondary);">List Jira tickets</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem 0;"><code>GET /api/docs</code></td>
                    <td style="color: var(--text-secondary);">List Confluence pages</td>
                </tr>
            </table>
            <a href="/docs" class="btn btn-secondary" style="margin-top: 1rem;">API Documentation</a>
        </div>
        
        <div class="footer">
            <p>gitdocs - Developer-friendly CLI/TUI for Jira and Confluence</p>
        </div>
    </div>
    
    <script>
        async function testConnections() {{
            try {{
                const response = await fetch('/api/config/test', {{ method: 'POST' }});
                const data = await response.json();
                
                // Update Jira status
                const jiraStatus = document.getElementById('jira-status');
                const jiraDot = jiraStatus.querySelector('.status-dot');
                const jiraText = jiraStatus.querySelector('span:last-child');
                
                if (data.jira?.connected) {{
                    jiraDot.className = 'status-dot connected';
                    jiraText.textContent = 'Jira: Connected (' + data.jira.user + ')';
                }} else if (data.jira?.configured) {{
                    jiraDot.className = 'status-dot error';
                    jiraText.textContent = 'Jira: Connection failed';
                }} else {{
                    jiraDot.className = 'status-dot disconnected';
                    jiraText.textContent = 'Jira: Not configured';
                }}
                
                // Update Confluence status
                const confStatus = document.getElementById('confluence-status');
                const confDot = confStatus.querySelector('.status-dot');
                const confText = confStatus.querySelector('span:last-child');
                
                if (data.confluence?.connected) {{
                    confDot.className = 'status-dot connected';
                    confText.textContent = 'Confluence: Connected (' + data.confluence.user + ')';
                }} else if (data.confluence?.configured) {{
                    confDot.className = 'status-dot error';
                    confText.textContent = 'Confluence: Connection failed';
                }} else {{
                    confDot.className = 'status-dot disconnected';
                    confText.textContent = 'Confluence: Not configured';
                }}
            }} catch (e) {{
                console.error('Error testing connections:', e);
            }}
        }}
        
        // Test on load
        testConnections();
    </script>
</body>
</html>
"""

