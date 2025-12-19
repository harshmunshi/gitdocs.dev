"""FastAPI web server for local control plane."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    """Serve the admin configuration page."""
    return HTMLResponse(content=get_admin_html())


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


def get_default_html() -> str:
    """Return default dashboard HTML matching the git/doc landing page style."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gitdocs - Transform Code Into Living Documentation</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #f8f9fa;
            --bg-white: #ffffff;
            --bg-dark: #1a1d21;
            --text-primary: #1a1d21;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --accent: #1a1d21;
            --accent-hover: #2d3138;
            --border: #e5e7eb;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Dotted grid background */
        .bg-pattern {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: radial-gradient(circle, #d1d5db 1px, transparent 1px);
            background-size: 24px 24px;
            pointer-events: none;
            z-index: -1;
        }}
        
        /* Header */
        header {{
            background: var(--bg-white);
            border-bottom: 1px solid var(--border);
            padding: 0 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 64px;
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.25rem;
            color: var(--text-primary);
            text-decoration: none;
        }}
        
        .logo-icon {{
            width: 36px;
            height: 36px;
            background: var(--bg-dark);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1rem;
        }}
        
        nav {{
            display: flex;
            align-items: center;
            gap: 2rem;
        }}
        
        nav a {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: color 0.2s;
        }}
        
        nav a:hover {{
            color: var(--text-primary);
        }}
        
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1.25rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }}
        
        .btn-primary {{
            background: var(--accent);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: var(--accent-hover);
        }}
        
        .btn-secondary {{
            background: var(--bg-white);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }}
        
        .btn-secondary:hover {{
            background: var(--bg-primary);
        }}
        
        .btn-large {{
            padding: 1rem 2rem;
            font-size: 1rem;
        }}
        
        /* Hero Section */
        .hero {{
            padding: 5rem 2rem;
            text-align: center;
        }}
        
        .hero-content {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-dark);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 2rem;
        }}
        
        .badge svg {{
            width: 16px;
            height: 16px;
        }}
        
        h1 {{
            font-size: 4rem;
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.03em;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
        }}
        
        .hero-subtitle {{
            font-size: 1.25rem;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 2.5rem;
            line-height: 1.7;
        }}
        
        .hero-actions {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}
        
        /* Terminal Preview */
        .terminal-preview {{
            max-width: 900px;
            margin: 4rem auto 0;
            background: var(--bg-dark);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }}
        
        .terminal-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 1rem 1.25rem;
            background: rgba(255,255,255,0.05);
        }}
        
        .terminal-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        
        .terminal-dot.red {{ background: #ff5f56; }}
        .terminal-dot.yellow {{ background: #ffbd2e; }}
        .terminal-dot.green {{ background: #27ca40; }}
        
        .terminal-title {{
            flex: 1;
            text-align: center;
            color: #9ca3af;
            font-size: 0.85rem;
        }}
        
        .terminal-body {{
            padding: 1.5rem;
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.9rem;
            line-height: 1.8;
            color: #e5e7eb;
        }}
        
        .terminal-line {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 0.5rem;
        }}
        
        .terminal-prompt {{
            color: #10b981;
            margin-right: 0.75rem;
            user-select: none;
        }}
        
        .terminal-command {{
            color: #f9fafb;
        }}
        
        .terminal-output {{
            color: #9ca3af;
            padding-left: 1.5rem;
        }}
        
        .terminal-success {{
            color: #10b981;
        }}
        
        .terminal-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.85rem;
        }}
        
        .terminal-table th,
        .terminal-table td {{
            text-align: left;
            padding: 0.6rem 1rem;
            border: 1px solid #374151;
        }}
        
        .terminal-table th {{
            background: #1f2937;
            color: #9ca3af;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        
        .terminal-table td {{
            color: #e5e7eb;
        }}
        
        .terminal-table td.key {{
            color: #60a5fa;
            font-weight: 500;
        }}
        
        .terminal-table tbody tr:hover {{
            background: rgba(255,255,255,0.03);
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        
        .status-badge.progress {{
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
        }}
        
        .status-badge.todo {{
            background: rgba(156, 163, 175, 0.2);
            color: #9ca3af;
        }}
        
        .status-badge.done {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        
        /* Features Section */
        .features {{
            padding: 5rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .features h2 {{
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 3rem;
        }}
        
        .features-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
        }}
        
        .feature-card {{
            background: var(--bg-white);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            transition: box-shadow 0.2s, transform 0.2s;
        }}
        
        .feature-card:hover {{
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        
        .feature-icon {{
            width: 48px;
            height: 48px;
            background: var(--bg-primary);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .feature-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .feature-card p {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        /* Status Section */
        .status-section {{
            padding: 3rem 2rem;
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .status-card {{
            background: var(--bg-white);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
        }}
        
        .status-card h3 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .status-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .status-item:last-of-type {{
            border-bottom: none;
        }}
        
        .status-label {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--text-muted);
        }}
        
        .status-dot.connected {{
            background: var(--success);
            box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2);
        }}
        
        .status-dot.error {{
            background: var(--error);
            box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.2);
        }}
        
        .status-value {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .status-actions {{
            margin-top: 1.5rem;
            display: flex;
            gap: 1rem;
        }}
        
        /* Footer */
        footer {{
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            h1 {{
                font-size: 2.5rem;
            }}
            
            .hero-subtitle {{
                font-size: 1.1rem;
            }}
            
            nav {{
                display: none;
            }}
            
            .hero-actions {{
                flex-direction: column;
                align-items: center;
            }}
            
            .btn-large {{
                width: 100%;
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    
    <header>
        <div class="header-content">
            <a href="/" class="logo">
                <div class="logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                </div>
                &lt;git/docs&gt;
            </a>
            
            <nav>
                <a href="#features">Features</a>
                <a href="/docs">API Docs</a>
                <a href="#status">Status</a>
                <a href="/admin">Settings</a>
            </nav>
            
            <div class="header-actions">
                <span style="color: var(--text-muted); font-size: 0.85rem;">v{__version__}</span>
                <a href="/admin" class="btn btn-secondary" style="margin-right: 0.5rem;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Settings
                </a>
                <a href="/docs" class="btn btn-primary">API Docs</a>
            </div>
        </div>
    </header>
    
    <main>
        <section class="hero">
            <div class="hero-content">
                <div class="badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    Now with Confluence Integration
                </div>
                
                <h1>Transform Code Into Living Documentation</h1>
                
                <p class="hero-subtitle">
                    Developer-friendly CLI/TUI that lets engineers work with Jira tickets 
                    and Confluence documentation directly from the terminal. No context switching.
                </p>
                
                <div class="hero-actions">
                    <a href="#status" class="btn btn-primary btn-large">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                        Check Status
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                    </a>
                    <a href="/docs" class="btn btn-secondary btn-large">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
                        </svg>
                        View API Docs
                    </a>
                </div>
            </div>
            
            <div class="terminal-preview">
                <div class="terminal-header">
                    <div class="terminal-dot red"></div>
                    <div class="terminal-dot yellow"></div>
                    <div class="terminal-dot green"></div>
                    <span class="terminal-title">gitdocs — Terminal</span>
                </div>
                <div class="terminal-body">
                    <div class="terminal-line">
                        <span class="terminal-prompt">$</span>
                        <span class="terminal-command">gitdocs tickets ls --mine</span>
                    </div>
                    <table class="terminal-table">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Summary</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="key">PROJ-142</td>
                                <td>Story</td>
                                <td><span class="status-badge progress">In Progress</span></td>
                                <td>Add OAuth2 authentication</td>
                            </tr>
                            <tr>
                                <td class="key">PROJ-138</td>
                                <td>Bug</td>
                                <td><span class="status-badge todo">To Do</span></td>
                                <td>Fix pagination issue</td>
                            </tr>
                            <tr>
                                <td class="key">PROJ-135</td>
                                <td>Task</td>
                                <td><span class="status-badge done">Done</span></td>
                                <td>Update API documentation</td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="terminal-line" style="margin-top: 1.5rem;">
                        <span class="terminal-prompt">$</span>
                        <span class="terminal-command">gitdocs sync suggest</span>
                    </div>
                    <div class="terminal-output terminal-success">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline; vertical-align: middle; margin-right: 6px;">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                        Found 3 tickets with updates from recent commits
                    </div>
                </div>
            </div>
        </section>
        
        <section class="features" id="features">
            <h2>Everything you need</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🎯</div>
                    <h3>Jira Integration</h3>
                    <p>List, search, comment, and transition issues directly from the command line.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📝</div>
                    <h3>Confluence Sync</h3>
                    <p>Browse page trees, pull to markdown, push updates with diff preview.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🖥️</div>
                    <h3>Terminal UI</h3>
                    <p>Neovim-like split view with vim keybindings for keyboard-first workflow.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🤖</div>
                    <h3>AI-Powered</h3>
                    <p>LLM suggestions for ticket updates based on your commit history.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⚡</div>
                    <h3>Fast & Cached</h3>
                    <p>Smart caching with TTL to minimize API calls and maximize speed.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <h3>Secure</h3>
                    <p>Credentials stored in system keyring. Dry-run by default for safety.</p>
                </div>
            </div>
        </section>
        
        <section class="status-section" id="status">
            <div class="status-card">
                <h3>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    Connection Status
                </h3>
                
                <div class="status-item" id="jira-status">
                    <div class="status-label">
                        <span class="status-dot"></span>
                        <span>Jira</span>
                    </div>
                    <span class="status-value">Checking...</span>
                </div>
                
                <div class="status-item" id="confluence-status">
                    <div class="status-label">
                        <span class="status-dot"></span>
                        <span>Confluence</span>
                    </div>
                    <span class="status-value">Checking...</span>
                </div>
                
                <div class="status-actions">
                    <button class="btn btn-primary" onclick="testConnections()" style="flex: 1;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M23 4v6h-6M1 20v-6h6"/>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                        </svg>
                        Test Connections
                    </button>
                    <a href="/docs" class="btn btn-secondary" style="flex: 1; justify-content: center;">
                        API Reference
                    </a>
                </div>
            </div>
        </section>
    </main>
    
    <footer>
        <p>gitdocs v{__version__} — Developer-friendly CLI/TUI for Jira and Confluence</p>
    </footer>
    
    <script>
        async function testConnections() {{
            // Update UI to show loading
            document.querySelectorAll('.status-value').forEach(el => el.textContent = 'Testing...');
            
            try {{
                const response = await fetch('/api/config/test', {{ method: 'POST' }});
                const data = await response.json();
                
                // Update Jira status
                const jiraStatus = document.getElementById('jira-status');
                const jiraDot = jiraStatus.querySelector('.status-dot');
                const jiraValue = jiraStatus.querySelector('.status-value');
                
                if (data.jira?.connected) {{
                    jiraDot.className = 'status-dot connected';
                    jiraValue.textContent = 'Connected as ' + data.jira.user;
                }} else if (data.jira?.configured) {{
                    jiraDot.className = 'status-dot error';
                    jiraValue.textContent = 'Connection failed';
                }} else {{
                    jiraDot.className = 'status-dot';
                    jiraValue.textContent = 'Not configured';
                }}
                
                // Update Confluence status
                const confStatus = document.getElementById('confluence-status');
                const confDot = confStatus.querySelector('.status-dot');
                const confValue = confStatus.querySelector('.status-value');
                
                if (data.confluence?.connected) {{
                    confDot.className = 'status-dot connected';
                    confValue.textContent = 'Connected as ' + data.confluence.user;
                }} else if (data.confluence?.configured) {{
                    confDot.className = 'status-dot error';
                    confValue.textContent = 'Connection failed';
                }} else {{
                    confDot.className = 'status-dot';
                    confValue.textContent = 'Not configured';
                }}
            }} catch (e) {{
                console.error('Error testing connections:', e);
                document.querySelectorAll('.status-value').forEach(el => el.textContent = 'Error');
            }}
        }}
        
        // Test connections on page load
        testConnections();
    </script>
</body>
</html>
"""


def get_admin_html() -> str:
    """Return admin configuration page HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gitdocs - Settings</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #f8f9fa;
            --bg-white: #ffffff;
            --bg-dark: #1a1d21;
            --text-primary: #1a1d21;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --accent: #1a1d21;
            --accent-blue: #3b82f6;
            --border: #e5e7eb;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }
        
        /* Header */
        header {
            background: var(--bg-white);
            border-bottom: 1px solid var(--border);
            padding: 0 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 64px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.25rem;
            color: var(--text-primary);
            text-decoration: none;
        }
        
        .logo-icon {
            width: 36px;
            height: 36px;
            background: var(--bg-dark);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        nav { display: flex; align-items: center; gap: 2rem; }
        nav a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; }
        nav a:hover { color: var(--text-primary); }
        nav a.active { color: var(--text-primary); }
        
        /* Main Content */
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .page-header {
            margin-bottom: 2rem;
        }
        
        .page-header h1 {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .page-header p {
            color: var(--text-secondary);
        }
        
        /* Cards */
        .card {
            background: var(--bg-white);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .card-title {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .card-title svg {
            color: var(--text-secondary);
        }
        
        .card-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--text-muted);
        }
        
        .status-indicator.connected { background: var(--success); }
        .status-indicator.error { background: var(--error); }
        
        /* Form Elements */
        .form-group {
            margin-bottom: 1.25rem;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        
        label {
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }
        
        .label-hint {
            font-weight: 400;
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        
        input[type="text"],
        input[type="email"],
        input[type="password"],
        input[type="url"] {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--bg-white);
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        input:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        input::placeholder {
            color: var(--text-muted);
        }
        
        .input-with-icon {
            position: relative;
        }
        
        .input-with-icon input {
            padding-right: 2.5rem;
        }
        
        .input-icon {
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            cursor: pointer;
        }
        
        .input-icon:hover {
            color: var(--text-secondary);
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }
        
        .btn-primary {
            background: var(--accent);
            color: white;
        }
        
        .btn-primary:hover {
            background: #2d3138;
        }
        
        .btn-secondary {
            background: var(--bg-white);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .btn-secondary:hover {
            background: var(--bg-primary);
        }
        
        .btn-success {
            background: var(--success);
            color: white;
        }
        
        .btn-danger {
            background: var(--error);
            color: white;
        }
        
        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
        }
        
        .btn-block {
            width: 100%;
        }
        
        .btn-group {
            display: flex;
            gap: 0.75rem;
            margin-top: 1.5rem;
        }
        
        /* Alerts */
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }
        
        .alert-success {
            background: rgba(16, 185, 129, 0.1);
            color: #047857;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        
        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            color: #b91c1c;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        .alert-info {
            background: rgba(59, 130, 246, 0.1);
            color: #1d4ed8;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        
        /* Help text */
        .help-text {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }
        
        .help-text a {
            color: var(--accent-blue);
            text-decoration: none;
        }
        
        .help-text a:hover {
            text-decoration: underline;
        }
        
        /* Divider */
        .divider {
            height: 1px;
            background: var(--border);
            margin: 1.5rem 0;
        }
        
        /* Hidden class */
        .hidden {
            display: none !important;
        }
        
        /* Toast */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            background: var(--bg-dark);
            color: white;
            font-size: 0.9rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
        }
        
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .toast.success {
            background: var(--success);
        }
        
        .toast.error {
            background: var(--error);
        }
        
        @media (max-width: 768px) {
            .form-row {
                grid-template-columns: 1fr;
            }
            
            nav { display: none; }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">
                <div class="logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                        <polyline points="14,2 14,8 20,8"/>
                    </svg>
                </div>
                &lt;git/docs&gt;
            </a>
            
            <nav>
                <a href="/">Home</a>
                <a href="/docs">API Docs</a>
                <a href="/admin" class="active">Settings</a>
            </nav>
        </div>
    </header>
    
    <main class="container">
        <div class="page-header">
            <h1>Settings</h1>
            <p>Configure your Jira, Confluence, and API integrations</p>
        </div>
        
        <div id="alert-container"></div>
        
        <!-- Jira Configuration -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    Jira Configuration
                </div>
                <div class="card-status" id="jira-connection-status">
                    <span class="status-indicator"></span>
                    <span>Checking...</span>
                </div>
            </div>
            
            <form id="jira-form">
                <div class="form-group">
                    <label for="jira-url">Jira URL</label>
                    <input type="url" id="jira-url" name="jira_url" 
                           placeholder="https://your-company.atlassian.net">
                    <p class="help-text">Your Atlassian Cloud URL</p>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="jira-email">Email</label>
                        <input type="email" id="jira-email" name="jira_email" 
                               placeholder="you@company.com">
                    </div>
                    <div class="form-group">
                        <label for="jira-project">Default Project <span class="label-hint">(optional)</span></label>
                        <input type="text" id="jira-project" name="jira_project" 
                               placeholder="PROJ">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="jira-token">API Token</label>
                    <div class="input-with-icon">
                        <input type="password" id="jira-token" name="jira_token" 
                               placeholder="Enter your Jira API token">
                        <span class="input-icon" onclick="togglePassword('jira-token')">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                <circle cx="12" cy="12" r="3"/>
                            </svg>
                        </span>
                    </div>
                    <p class="help-text">
                        Create an API token at 
                        <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank">
                            Atlassian Account Settings
                        </a>
                    </p>
                </div>
                
                <div class="btn-group">
                    <button type="submit" class="btn btn-primary">Save Jira Settings</button>
                    <button type="button" class="btn btn-secondary" onclick="testJira()">Test Connection</button>
                </div>
            </form>
        </div>
        
        <!-- Confluence Configuration -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    Confluence Configuration
                </div>
                <div class="card-status" id="confluence-connection-status">
                    <span class="status-indicator"></span>
                    <span>Checking...</span>
                </div>
            </div>
            
            <form id="confluence-form">
                <div class="form-group">
                    <label for="confluence-url">Confluence URL</label>
                    <input type="url" id="confluence-url" name="confluence_url" 
                           placeholder="https://your-company.atlassian.net">
                    <p class="help-text">Usually the same as your Jira URL</p>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="confluence-email">Email</label>
                        <input type="email" id="confluence-email" name="confluence_email" 
                               placeholder="you@company.com">
                    </div>
                    <div class="form-group">
                        <label for="confluence-space">Default Space <span class="label-hint">(optional)</span></label>
                        <input type="text" id="confluence-space" name="confluence_space" 
                               placeholder="DOCS">
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="confluence-token">API Token</label>
                    <div class="input-with-icon">
                        <input type="password" id="confluence-token" name="confluence_token" 
                               placeholder="Enter your Confluence API token">
                        <span class="input-icon" onclick="togglePassword('confluence-token')">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                <circle cx="12" cy="12" r="3"/>
                            </svg>
                        </span>
                    </div>
                    <p class="help-text">Can use the same API token as Jira if on the same Atlassian instance</p>
                </div>
                
                <div class="btn-group">
                    <button type="submit" class="btn btn-primary">Save Confluence Settings</button>
                    <button type="button" class="btn btn-secondary" onclick="testConfluence()">Test Connection</button>
                </div>
            </form>
        </div>
        
        <!-- OpenAI Configuration -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"/>
                        <path d="M12 16v-4M12 8h.01"/>
                    </svg>
                    OpenAI / LLM Configuration
                    <span class="label-hint">(optional)</span>
                </div>
            </div>
            
            <div class="alert alert-info">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 16v-4M12 8h.01"/>
                </svg>
                <div>
                    Enable AI-powered suggestions for ticket updates based on your commit history.
                    Requires an OpenAI API key.
                </div>
            </div>
            
            <form id="openai-form">
                <div class="form-group">
                    <label for="openai-key">OpenAI API Key</label>
                    <div class="input-with-icon">
                        <input type="password" id="openai-key" name="openai_key" 
                               placeholder="sk-...">
                        <span class="input-icon" onclick="togglePassword('openai-key')">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                <circle cx="12" cy="12" r="3"/>
                            </svg>
                        </span>
                    </div>
                    <p class="help-text">
                        Get your API key from 
                        <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Platform</a>
                    </p>
                </div>
                
                <div class="btn-group">
                    <button type="submit" class="btn btn-primary">Save OpenAI Key</button>
                </div>
            </form>
        </div>
        
        <!-- Danger Zone -->
        <div class="card" style="border-color: var(--error);">
            <div class="card-header" style="border-color: rgba(239, 68, 68, 0.2);">
                <div class="card-title" style="color: var(--error);">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    Danger Zone
                </div>
            </div>
            
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                Clear all stored credentials from this machine.
            </p>
            
            <button type="button" class="btn btn-danger" onclick="clearCredentials()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Clear All Credentials
            </button>
        </div>
    </main>
    
    <div id="toast" class="toast"></div>
    
    <script>
        // Load current config on page load
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const config = await response.json();
                
                // Populate Jira fields
                if (config.jira_url) document.getElementById('jira-url').value = config.jira_url;
                if (config.jira_email) document.getElementById('jira-email').value = config.jira_email;
                if (config.jira_project) document.getElementById('jira-project').value = config.jira_project;
                
                // Populate Confluence fields
                if (config.confluence_url) document.getElementById('confluence-url').value = config.confluence_url;
                if (config.confluence_email) document.getElementById('confluence-email').value = config.confluence_email;
                if (config.confluence_space) document.getElementById('confluence-space').value = config.confluence_space;
                
                // Test connections
                testConnections();
            } catch (e) {
                console.error('Error loading config:', e);
            }
        }
        
        // Test all connections
        async function testConnections() {
            try {
                const response = await fetch('/api/config/test', { method: 'POST' });
                const data = await response.json();
                
                updateConnectionStatus('jira', data.jira);
                updateConnectionStatus('confluence', data.confluence);
            } catch (e) {
                console.error('Error testing connections:', e);
            }
        }
        
        function updateConnectionStatus(service, status) {
            const statusEl = document.getElementById(`${service}-connection-status`);
            const indicator = statusEl.querySelector('.status-indicator');
            const text = statusEl.querySelector('span:last-child');
            
            if (status?.connected) {
                indicator.className = 'status-indicator connected';
                text.textContent = `Connected as ${status.user}`;
            } else if (status?.configured) {
                indicator.className = 'status-indicator error';
                text.textContent = 'Connection failed';
            } else {
                indicator.className = 'status-indicator';
                text.textContent = 'Not configured';
            }
        }
        
        // Test individual connections
        async function testJira() {
            showToast('Testing Jira connection...', '');
            await testConnections();
        }
        
        async function testConfluence() {
            showToast('Testing Confluence connection...', '');
            await testConnections();
        }
        
        // Form submissions
        document.getElementById('jira-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/credentials/jira', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: formData.get('jira_url'),
                        email: formData.get('jira_email'),
                        project: formData.get('jira_project'),
                        token: formData.get('jira_token')
                    })
                });
                
                if (response.ok) {
                    showToast('Jira settings saved successfully!', 'success');
                    testConnections();
                } else {
                    const err = await response.json();
                    showToast(err.detail || 'Failed to save settings', 'error');
                }
            } catch (e) {
                showToast('Error saving settings', 'error');
            }
        });
        
        document.getElementById('confluence-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/credentials/confluence', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: formData.get('confluence_url'),
                        email: formData.get('confluence_email'),
                        space: formData.get('confluence_space'),
                        token: formData.get('confluence_token')
                    })
                });
                
                if (response.ok) {
                    showToast('Confluence settings saved successfully!', 'success');
                    testConnections();
                } else {
                    const err = await response.json();
                    showToast(err.detail || 'Failed to save settings', 'error');
                }
            } catch (e) {
                showToast('Error saving settings', 'error');
            }
        });
        
        document.getElementById('openai-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/credentials/openai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        key: formData.get('openai_key')
                    })
                });
                
                if (response.ok) {
                    showToast('OpenAI key saved successfully!', 'success');
                } else {
                    const err = await response.json();
                    showToast(err.detail || 'Failed to save key', 'error');
                }
            } catch (e) {
                showToast('Error saving key', 'error');
            }
        });
        
        // Clear credentials
        async function clearCredentials() {
            if (!confirm('Are you sure you want to clear all stored credentials? This cannot be undone.')) {
                return;
            }
            
            try {
                const response = await fetch('/api/credentials', { method: 'DELETE' });
                if (response.ok) {
                    showToast('All credentials cleared', 'success');
                    testConnections();
                    // Clear form fields
                    document.querySelectorAll('input').forEach(input => input.value = '');
                } else {
                    showToast('Failed to clear credentials', 'error');
                }
            } catch (e) {
                showToast('Error clearing credentials', 'error');
            }
        }
        
        // Toggle password visibility
        function togglePassword(inputId) {
            const input = document.getElementById(inputId);
            input.type = input.type === 'password' ? 'text' : 'password';
        }
        
        // Toast notification
        function showToast(message, type = '') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = `toast show ${type}`;
            
            setTimeout(() => {
                toast.className = 'toast';
            }, 3000);
        }
        
        // Initialize
        loadConfig();
    </script>
</body>
</html>
"""
