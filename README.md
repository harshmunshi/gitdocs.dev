# gitdocs 📚

A Python-first, developer-friendly CLI/TUI that lets engineers work with **Jira tickets** and **Confluence documentation** directly from the terminal — no context switching required.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

- 🎯 **Jira Integration**: List, search, view, comment, and transition issues directly from CLI
- 📝 **Confluence Integration**: Browse page trees, pull pages to markdown, push updates
- 🖥️ **Terminal UI**: Neovim-like split view with ticket/doc trees and detail panes
- 🌐 **Local Web Dashboard**: Configuration management and API testing
- 🤖 **LLM Assist**: AI-powered ticket update suggestions from commit history
- ⚡ **Fast & Scriptable**: Caching, rate limiting, and composable commands
- 🔒 **Secure**: Credentials stored in system keyring with encrypted fallback

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/your-org/gitdocs.git
cd gitdocs
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"

# Or with LLM support
pip install -e ".[llm]"
```

### Setup

```bash
# Initialize gitdocs in your repository
cd /path/to/your/repo
gitdocs init

# Follow the interactive prompts to configure:
# - Jira URL, email, and project
# - Confluence URL, email, and space
# - API tokens (stored securely)

# Verify configuration
gitdocs config --test
```

## Usage

### CLI Commands

```bash
# Tickets
gitdocs tickets ls                    # List issues
gitdocs tickets ls --mine             # Issues assigned to me
gitdocs tickets ls --sprint current   # Current sprint issues
gitdocs tickets ls --jql "project = PROJ AND status = 'In Progress'"

gitdocs tickets show PROJ-123         # View issue details
gitdocs tickets show PROJ-123 -c      # Include comments
gitdocs tickets show PROJ-123 -t      # Show available transitions

gitdocs tickets comment PROJ-123 -m "Fixed in commit abc123"
gitdocs tickets transition PROJ-123 --to "Done"

# Documentation
gitdocs docs spaces                   # List available spaces
gitdocs docs tree --space DOCS        # Browse page tree
gitdocs docs show 12345               # View page by ID
gitdocs docs show "Page Title" -s DOCS

gitdocs docs pull 12345               # Pull page to markdown
gitdocs docs pull 12345 -o guide.md   # Specify output file
gitdocs docs push guide.md --dry-run  # Preview changes
gitdocs docs push guide.md            # Push updates

# LLM-assisted sync
gitdocs sync suggest                  # Analyze commits, suggest updates
gitdocs sync suggest --commits 20     # Analyze more commits
gitdocs sync apply PROJ-123           # Apply suggestion (dry-run default)
gitdocs sync apply PROJ-123 --no-dry-run  # Actually post

# Configuration
gitdocs config --show                 # Display current config
gitdocs config --test                 # Test API connections
gitdocs auth status                   # Check credential status
gitdocs auth login jira               # Store Jira token
gitdocs auth login openai             # Store OpenAI key for LLM
```

### Interactive TUI

Launch the terminal UI for a visual, keyboard-driven experience:

```bash
gitdocs tui
```

**Keybindings:**
- `t` - Focus tickets tab
- `d` - Focus docs tab
- `j/k` - Navigate up/down (vim-style)
- `Enter` - Select item
- `/` - Search
- `r` - Refresh
- `?` - Help
- `q` - Quit

### Web Dashboard

Start the local configuration server:

```bash
gitdocs serve
gitdocs serve --port 9000 --no-open
```

Access at `http://localhost:8765` for:
- Configuration management
- API connection testing
- REST API endpoints for integration

## Configuration

### Repository Config (`.gitdocs.yml`)

```yaml
jira:
  base_url: https://company.atlassian.net
  email: your-email@company.com
  project_key: PROJ
  default_filters:
    - assignee = currentUser()

confluence:
  base_url: https://company.atlassian.net
  email: your-email@company.com
  space_key: DOCS

branch_patterns:
  feature: "feature/{ticket_key}-{slug}"

commit_patterns:
  - '\b([A-Z]+-\d+)\b'
```

### User Config (`~/.config/gitdocs/config.yml`)

```yaml
default_editor: vim
theme: dark

llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.3
  confidence_threshold: 0.7

cache:
  enabled: true
  ttl_seconds: 300
  max_size_mb: 100

audit_log: true
dry_run_by_default: true
```

### Environment Variables

```bash
# Override credentials (useful for CI)
export GITDOCS_JIRA_TOKEN="your-token"
export GITDOCS_CONFLUENCE_TOKEN="your-token"
export GITDOCS_OPENAI_KEY="sk-..."
```

## API Tokens

Create Atlassian API tokens at:
https://id.atlassian.com/manage-profile/security/api-tokens

For OpenAI (optional LLM features):
https://platform.openai.com/api-keys

## Architecture

```
gitdocs/
├── cli/          # Typer CLI commands
├── core/         # Config, paths, secrets, errors
├── atlassian/    # Jira & Confluence API clients
├── git/          # Git repository operations
├── store/        # Caching and commit-ticket mappings
├── llm/          # LLM integration for suggestions
├── tui/          # Textual TUI components
└── web/          # FastAPI local server
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=gitdocs --cov-report=html

# Type checking
mypy gitdocs

# Linting
ruff check gitdocs
ruff format gitdocs
```

## Safety Features

- **Dry-run by default**: Write operations require `--no-dry-run` or explicit confirmation
- **Audit logging**: All API writes are logged to `~/.config/gitdocs/logs/`
- **Confidence thresholds**: LLM suggestions require minimum confidence
- **Rate limiting**: Built-in backoff for API calls
- **Caching**: Configurable TTL to reduce API load

## REST API

When running `gitdocs serve`, access the API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Current configuration |
| `/api/config/test` | POST | Test API connections |
| `/api/tickets` | GET | List Jira tickets |
| `/api/tickets/{key}` | GET | Get ticket details |
| `/api/docs` | GET | List Confluence pages |
| `/api/docs/{id}` | GET | Get page content |
| `/api/spaces` | GET | List Confluence spaces |

Interactive API docs at `/docs` (Swagger UI).

## Roadmap

- [ ] PR/MR integration (GitHub, GitLab)
- [ ] Bulk operations
- [ ] Custom JQL presets
- [ ] Page templates
- [ ] Webhook support
- [ ] Team dashboards

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `pytest` and `ruff check`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with ❤️ for developers who live in the terminal.
