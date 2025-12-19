"""Diff utilities for git integration."""

import re
from dataclasses import dataclass


@dataclass
class FileDiff:
    """Represents changes to a single file."""

    path: str
    old_path: str | None  # For renames
    status: str  # A, M, D, R (added, modified, deleted, renamed)
    additions: int
    deletions: int
    hunks: list["DiffHunk"]


@dataclass
class DiffHunk:
    """Represents a single hunk in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[str]


def parse_unified_diff(diff_text: str) -> list[FileDiff]:
    """
    Parse unified diff output into structured format.

    Args:
        diff_text: Raw diff output from git

    Returns:
        List of FileDiff instances
    """
    file_diffs: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_hunk: DiffHunk | None = None

    lines = diff_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # New file header
        if line.startswith("diff --git"):
            if current_file:
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                file_diffs.append(current_file)

            # Extract file paths
            match = re.match(r"diff --git a/(.*) b/(.*)", line)
            if match:
                current_file = FileDiff(
                    path=match.group(2),
                    old_path=match.group(1) if match.group(1) != match.group(2) else None,
                    status="M",  # Default to modified
                    additions=0,
                    deletions=0,
                    hunks=[],
                )
            current_hunk = None

        # File status indicators
        elif line.startswith("new file"):
            if current_file:
                current_file.status = "A"
        elif line.startswith("deleted file"):
            if current_file:
                current_file.status = "D"
        elif line.startswith("rename from"):
            if current_file:
                current_file.status = "R"

        # Hunk header
        elif line.startswith("@@"):
            if current_file and current_hunk:
                current_file.hunks.append(current_hunk)

            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", line)
            if match:
                current_hunk = DiffHunk(
                    old_start=int(match.group(1)),
                    old_count=int(match.group(2) or 1),
                    new_start=int(match.group(3)),
                    new_count=int(match.group(4) or 1),
                    header=match.group(5).strip(),
                    lines=[],
                )

        # Content lines
        elif current_hunk is not None:
            if line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    current_file.additions += 1
                current_hunk.lines.append(line)
            elif line.startswith("-") and not line.startswith("---"):
                if current_file:
                    current_file.deletions += 1
                current_hunk.lines.append(line)
            elif line.startswith(" ") or line == "":
                current_hunk.lines.append(line)

        i += 1

    # Add last file
    if current_file:
        if current_hunk:
            current_file.hunks.append(current_hunk)
        file_diffs.append(current_file)

    return file_diffs


def summarize_diff(file_diffs: list[FileDiff], max_files: int = 10) -> str:
    """
    Create a human-readable summary of changes.

    Args:
        file_diffs: List of FileDiff instances
        max_files: Maximum files to list individually

    Returns:
        Summary string
    """
    if not file_diffs:
        return "No changes"

    total_additions = sum(f.additions for f in file_diffs)
    total_deletions = sum(f.deletions for f in file_diffs)

    lines = [
        f"**{len(file_diffs)} files changed** (+{total_additions}/-{total_deletions})",
        "",
    ]

    # Group by status
    added = [f for f in file_diffs if f.status == "A"]
    modified = [f for f in file_diffs if f.status == "M"]
    deleted = [f for f in file_diffs if f.status == "D"]
    renamed = [f for f in file_diffs if f.status == "R"]

    if added:
        lines.append(f"Added ({len(added)}):")
        for f in added[:max_files]:
            lines.append(f"  + {f.path}")
        if len(added) > max_files:
            lines.append(f"  ... and {len(added) - max_files} more")

    if modified:
        lines.append(f"Modified ({len(modified)}):")
        for f in sorted(modified, key=lambda x: x.additions + x.deletions, reverse=True)[
            :max_files
        ]:
            lines.append(f"  ~ {f.path} (+{f.additions}/-{f.deletions})")
        if len(modified) > max_files:
            lines.append(f"  ... and {len(modified) - max_files} more")

    if deleted:
        lines.append(f"Deleted ({len(deleted)}):")
        for f in deleted[:max_files]:
            lines.append(f"  - {f.path}")
        if len(deleted) > max_files:
            lines.append(f"  ... and {len(deleted) - max_files} more")

    if renamed:
        lines.append(f"Renamed ({len(renamed)}):")
        for f in renamed[:max_files]:
            lines.append(f"  {f.old_path} → {f.path}")

    return "\n".join(lines)


def extract_code_context(hunk: DiffHunk, context_lines: int = 3) -> str:
    """
    Extract meaningful code context from a diff hunk.

    Args:
        hunk: DiffHunk instance
        context_lines: Number of context lines to include

    Returns:
        Code context string
    """
    relevant_lines = []

    for line in hunk.lines:
        if line.startswith("+") or line.startswith("-"):
            relevant_lines.append(line)
        elif relevant_lines:
            # Include context around changes
            if len(relevant_lines) < context_lines * 2:
                relevant_lines.append(line)

    return "\n".join(relevant_lines[:50])  # Limit output
