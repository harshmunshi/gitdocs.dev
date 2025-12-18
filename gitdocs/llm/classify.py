"""Commit classification and ticket suggestion logic."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from gitdocs.llm.client import LLMClient, TicketSuggestion
from gitdocs.store.mappings import extract_ticket_keys

logger = logging.getLogger(__name__)


@dataclass
class CommitClassification:
    """Classification result for a commit."""
    
    commit_sha: str
    message: str
    type: str  # feature, bugfix, refactor, docs, chore, test
    scope: str
    ticket_keys: list[str]
    is_breaking: bool
    confidence: float


def classify_commit_message(message: str) -> dict:
    """
    Classify a commit based on conventional commit patterns.
    
    Args:
        message: Commit message
        
    Returns:
        Classification dict
    """
    # Conventional commit pattern: type(scope): description
    pattern = r"^(\w+)(?:\(([^)]+)\))?:\s*(.+)"
    match = re.match(pattern, message.split("\n")[0])
    
    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2) or ""
        description = match.group(3)
        
        # Normalize type
        type_mapping = {
            "feat": "feature",
            "fix": "bugfix",
            "bug": "bugfix",
            "docs": "docs",
            "doc": "docs",
            "style": "chore",
            "refactor": "refactor",
            "perf": "refactor",
            "test": "test",
            "tests": "test",
            "chore": "chore",
            "ci": "chore",
            "build": "chore",
        }
        
        normalized_type = type_mapping.get(commit_type, "chore")
        is_breaking = "!" in message[:50] or "BREAKING" in message.upper()
        
        return {
            "type": normalized_type,
            "scope": scope,
            "description": description,
            "is_breaking": is_breaking,
            "confidence": 0.9,
        }
    
    # Fallback: try to infer from keywords
    message_lower = message.lower()
    
    if any(w in message_lower for w in ["fix", "bug", "issue", "error", "crash"]):
        inferred_type = "bugfix"
    elif any(w in message_lower for w in ["add", "implement", "feature", "new"]):
        inferred_type = "feature"
    elif any(w in message_lower for w in ["refactor", "clean", "improve", "optimize"]):
        inferred_type = "refactor"
    elif any(w in message_lower for w in ["doc", "readme", "comment"]):
        inferred_type = "docs"
    elif any(w in message_lower for w in ["test", "spec"]):
        inferred_type = "test"
    else:
        inferred_type = "chore"
    
    return {
        "type": inferred_type,
        "scope": "",
        "description": message.split("\n")[0],
        "is_breaking": "BREAKING" in message.upper(),
        "confidence": 0.5,
    }


def analyze_commits_for_ticket(
    commits: list[dict],
    ticket_key: str,
    llm_client: Optional[LLMClient] = None,
) -> Optional[TicketSuggestion]:
    """
    Analyze commits related to a ticket and suggest an update.
    
    Args:
        commits: List of commit dicts with 'sha', 'message', 'diff' keys
        ticket_key: Target ticket key
        llm_client: Optional LLM client for AI suggestions
        
    Returns:
        TicketSuggestion if analysis successful
    """
    if not commits:
        return None
    
    # Build commit summary
    commit_lines = []
    total_files = set()
    
    for commit in commits:
        sha = commit.get("sha", "")[:7]
        msg = commit.get("message", "").split("\n")[0]
        commit_lines.append(f"- {sha}: {msg}")
        
        # Extract changed files if available
        if files := commit.get("files"):
            total_files.update(files)
    
    commits_summary = "\n".join(commit_lines)
    
    # Build diff summary
    diff_summary = f"Files changed: {', '.join(list(total_files)[:10])}"
    if len(total_files) > 10:
        diff_summary += f" (and {len(total_files) - 10} more)"
    
    # Try LLM suggestion
    if llm_client:
        suggestion = llm_client.suggest_ticket_update(
            ticket_key=ticket_key,
            commits=commits_summary,
            diff_summary=diff_summary,
        )
        if suggestion:
            return suggestion
    
    # Fallback: generate basic summary
    classifications = [classify_commit_message(c.get("message", "")) for c in commits]
    
    # Group by type
    by_type: dict[str, list[str]] = {}
    for commit, classification in zip(commits, classifications):
        t = classification["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(commit.get("message", "").split("\n")[0])
    
    # Build comment
    comment_parts = [f"Updated via {len(commits)} commit(s):"]
    
    for commit_type, messages in by_type.items():
        comment_parts.append(f"\n**{commit_type.title()}:**")
        for msg in messages[:5]:
            comment_parts.append(f"- {msg[:80]}")
        if len(messages) > 5:
            comment_parts.append(f"- ... and {len(messages) - 5} more")
    
    return TicketSuggestion(
        ticket_key=ticket_key,
        comment="\n".join(comment_parts),
        confidence=0.5,  # Lower confidence for non-LLM suggestions
        reasoning="Generated from commit messages without LLM",
    )


def suggest_tickets_for_commits(
    commits: list[dict],
    patterns: Optional[list[str]] = None,
) -> dict[str, list[dict]]:
    """
    Analyze commits and suggest which tickets they relate to.
    
    Args:
        commits: List of commit dicts
        patterns: Regex patterns for ticket extraction
        
    Returns:
        Dict mapping ticket keys to related commits
    """
    ticket_commits: dict[str, list[dict]] = {}
    
    for commit in commits:
        message = commit.get("message", "")
        keys = extract_ticket_keys(message, patterns)
        
        for key in keys:
            if key not in ticket_commits:
                ticket_commits[key] = []
            ticket_commits[key].append(commit)
    
    return ticket_commits

