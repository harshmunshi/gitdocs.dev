"""Commit to ticket mapping and tracking."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default pattern matches PROJ-123 style ticket keys
DEFAULT_TICKET_PATTERN = r"\b([A-Z][A-Z0-9]+-\d+)\b"


@dataclass
class TicketCommitMapping:
    """Tracks which commits are associated with which tickets."""
    
    ticket_key: str
    commit_sha: str
    commit_message: str
    mapped_at: datetime = field(default_factory=datetime.now)
    synced: bool = False
    synced_at: Optional[datetime] = None


@dataclass
class MappingStore:
    """Persistent store for commit-ticket mappings."""
    
    mappings: dict[str, list[TicketCommitMapping]] = field(default_factory=dict)
    
    def add_mapping(self, mapping: TicketCommitMapping) -> None:
        """Add a new mapping."""
        if mapping.ticket_key not in self.mappings:
            self.mappings[mapping.ticket_key] = []
        
        # Check for duplicates
        for existing in self.mappings[mapping.ticket_key]:
            if existing.commit_sha == mapping.commit_sha:
                return  # Already exists
        
        self.mappings[mapping.ticket_key].append(mapping)
    
    def get_mappings_for_ticket(self, ticket_key: str) -> list[TicketCommitMapping]:
        """Get all mappings for a ticket."""
        return self.mappings.get(ticket_key, [])
    
    def get_unsynced_mappings(self) -> list[TicketCommitMapping]:
        """Get all unsynced mappings."""
        unsynced = []
        for mappings in self.mappings.values():
            for m in mappings:
                if not m.synced:
                    unsynced.append(m)
        return unsynced
    
    def mark_synced(self, ticket_key: str, commit_sha: str) -> None:
        """Mark a mapping as synced."""
        if ticket_key in self.mappings:
            for m in self.mappings[ticket_key]:
                if m.commit_sha == commit_sha:
                    m.synced = True
                    m.synced_at = datetime.now()
                    break
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            ticket: [
                {
                    "ticket_key": m.ticket_key,
                    "commit_sha": m.commit_sha,
                    "commit_message": m.commit_message,
                    "mapped_at": m.mapped_at.isoformat(),
                    "synced": m.synced,
                    "synced_at": m.synced_at.isoformat() if m.synced_at else None,
                }
                for m in mappings
            ]
            for ticket, mappings in self.mappings.items()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MappingStore":
        """Create from dictionary."""
        store = cls()
        for ticket, mappings in data.items():
            for m in mappings:
                store.add_mapping(TicketCommitMapping(
                    ticket_key=m["ticket_key"],
                    commit_sha=m["commit_sha"],
                    commit_message=m["commit_message"],
                    mapped_at=datetime.fromisoformat(m["mapped_at"]),
                    synced=m.get("synced", False),
                    synced_at=datetime.fromisoformat(m["synced_at"]) if m.get("synced_at") else None,
                ))
        return store


def extract_ticket_keys(
    text: str,
    patterns: Optional[list[str]] = None,
) -> list[str]:
    """
    Extract ticket keys from text (e.g., commit message).
    
    Args:
        text: Text to search
        patterns: Regex patterns to use (defaults to PROJ-123 style)
        
    Returns:
        List of unique ticket keys found
    """
    if patterns is None:
        patterns = [DEFAULT_TICKET_PATTERN]
    
    keys: set[str] = set()
    
    for pattern in patterns:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normalize to uppercase
                if isinstance(match, tuple):
                    key = match[0].upper()
                else:
                    key = match.upper()
                keys.add(key)
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
    
    return sorted(keys)


def load_mapping_store(path: Path) -> MappingStore:
    """Load mapping store from file."""
    if not path.exists():
        return MappingStore()
    
    try:
        data = json.loads(path.read_text())
        return MappingStore.from_dict(data)
    except Exception as e:
        logger.warning(f"Failed to load mapping store: {e}")
        return MappingStore()


def save_mapping_store(store: MappingStore, path: Path) -> None:
    """Save mapping store to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store.to_dict(), indent=2))


def find_related_tickets(
    commit_messages: list[str],
    patterns: Optional[list[str]] = None,
) -> dict[str, list[int]]:
    """
    Find tickets related to a list of commits.
    
    Args:
        commit_messages: List of commit messages
        patterns: Regex patterns for ticket extraction
        
    Returns:
        Dict mapping ticket keys to list of commit indices
    """
    ticket_commits: dict[str, list[int]] = {}
    
    for i, message in enumerate(commit_messages):
        keys = extract_ticket_keys(message, patterns)
        for key in keys:
            if key not in ticket_commits:
                ticket_commits[key] = []
            ticket_commits[key].append(i)
    
    return ticket_commits


def suggest_ticket_from_branch(
    branch_name: str,
    patterns: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Extract ticket key from branch name.
    
    Common patterns:
    - feature/PROJ-123-description
    - PROJ-123-fix-bug
    - bugfix/PROJ-123
    
    Args:
        branch_name: Git branch name
        patterns: Regex patterns for ticket extraction
        
    Returns:
        Ticket key if found, None otherwise
    """
    keys = extract_ticket_keys(branch_name, patterns)
    return keys[0] if keys else None

