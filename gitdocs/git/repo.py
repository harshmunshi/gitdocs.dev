"""Git repository interface."""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gitdocs.core.errors import GitDocsError

logger = logging.getLogger(__name__)


@dataclass
class Commit:
    """Represents a git commit."""

    sha: str
    message: str
    author_name: str
    author_email: str
    date: datetime

    @property
    def short_sha(self) -> str:
        """Return abbreviated SHA."""
        return self.sha[:7]

    @property
    def subject(self) -> str:
        """Return first line of commit message."""
        return self.message.split("\n")[0]


@dataclass
class DiffStat:
    """Diff statistics."""

    files_changed: int
    insertions: int
    deletions: int
    files: list[str]


class GitRepo:
    """Interface for git repository operations."""

    def __init__(self, repo_path: Path) -> None:
        """
        Initialize git repository interface.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    def _run_git(
        self,
        args: list[str],
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a git command.

        Args:
            args: Git command arguments (without 'git')
            capture_output: Capture stdout/stderr
            check: Raise on non-zero exit

        Returns:
            CompletedProcess instance
        """
        cmd = ["git"] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=check,
            )
            return result
        except subprocess.CalledProcessError as e:
            raise GitDocsError(f"Git command failed: {e.stderr or e.stdout}")

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run_git(["branch", "--show-current"])
        return result.stdout.strip()

    def get_head_sha(self) -> str:
        """Get the HEAD commit SHA."""
        result = self._run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def get_recent_commits(
        self,
        count: int = 10,
        branch: str | None = None,
        since: str | None = None,
    ) -> list[Commit]:
        """
        Get recent commits.

        Args:
            count: Maximum number of commits to return
            branch: Branch to get commits from (default: current)
            since: Only commits since this date (e.g., '2024-01-01')

        Returns:
            List of Commit instances
        """
        args = [
            "log",
            f"-{count}",
            "--format=%H%x00%s%n%b%x00%an%x00%ae%x00%aI",
            "--no-merges",
        ]

        if since:
            args.append(f"--since={since}")

        if branch:
            args.append(branch)

        result = self._run_git(args)

        commits = []
        for entry in result.stdout.strip().split("\n\n"):
            if not entry.strip():
                continue

            try:
                parts = entry.split("\x00")
                if len(parts) >= 5:
                    sha = parts[0]
                    message = parts[1]
                    author_name = parts[2]
                    author_email = parts[3]
                    date_str = parts[4].strip()

                    # Parse ISO date
                    date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                    commits.append(
                        Commit(
                            sha=sha,
                            message=message,
                            author_name=author_name,
                            author_email=author_email,
                            date=date,
                        )
                    )
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse commit: {e}")
                continue

        return commits

    def get_commit(self, sha: str) -> Commit:
        """
        Get a specific commit by SHA.

        Args:
            sha: Commit SHA (full or abbreviated)

        Returns:
            Commit instance
        """
        result = self._run_git(
            [
                "log",
                "-1",
                "--format=%H%x00%s%n%b%x00%an%x00%ae%x00%aI",
                sha,
            ]
        )

        parts = result.stdout.strip().split("\x00")
        if len(parts) < 5:
            raise GitDocsError(f"Commit not found: {sha}")

        date = datetime.fromisoformat(parts[4].strip().replace("Z", "+00:00"))

        return Commit(
            sha=parts[0],
            message=parts[1],
            author_name=parts[2],
            author_email=parts[3],
            date=date,
        )

    def get_changed_files(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
    ) -> list[str]:
        """
        Get list of changed files between two refs.

        Args:
            ref1: First ref (default: HEAD~1)
            ref2: Second ref (default: HEAD)

        Returns:
            List of changed file paths
        """
        result = self._run_git(
            [
                "diff",
                "--name-only",
                ref1,
                ref2,
            ]
        )

        return [f for f in result.stdout.strip().split("\n") if f]

    def get_diff(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
        file_path: str | None = None,
    ) -> str:
        """
        Get diff between two refs.

        Args:
            ref1: First ref
            ref2: Second ref
            file_path: Optional specific file to diff

        Returns:
            Diff output as string
        """
        args = ["diff", ref1, ref2]
        if file_path:
            args.extend(["--", file_path])

        result = self._run_git(args)
        return result.stdout

    def get_diff_stat(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
    ) -> DiffStat:
        """
        Get diff statistics between two refs.

        Args:
            ref1: First ref
            ref2: Second ref

        Returns:
            DiffStat instance
        """
        # Get file list
        files = self.get_changed_files(ref1, ref2)

        # Get stat summary
        result = self._run_git(
            [
                "diff",
                "--shortstat",
                ref1,
                ref2,
            ]
        )

        stat_line = result.stdout.strip()

        # Parse "X files changed, Y insertions(+), Z deletions(-)"
        files_changed = 0
        insertions = 0
        deletions = 0

        if stat_line:
            import re

            if match := re.search(r"(\d+) files? changed", stat_line):
                files_changed = int(match.group(1))
            if match := re.search(r"(\d+) insertions?", stat_line):
                insertions = int(match.group(1))
            if match := re.search(r"(\d+) deletions?", stat_line):
                deletions = int(match.group(1))

        return DiffStat(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            files=files,
        )

    def get_diff_summary(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
        max_lines: int = 100,
    ) -> str:
        """
        Get a summary of changes for LLM consumption.

        Args:
            ref1: First ref
            ref2: Second ref
            max_lines: Maximum lines to include

        Returns:
            Summary string
        """
        stat = self.get_diff_stat(ref1, ref2)

        lines = [
            f"Changes: {stat.files_changed} files, +{stat.insertions}/-{stat.deletions}",
            f"Files: {', '.join(stat.files[:10])}",
        ]

        if len(stat.files) > 10:
            lines.append(f"  ... and {len(stat.files) - 10} more files")

        return "\n".join(lines)

    def get_branches(self, remote: bool = False) -> list[str]:
        """
        Get list of branches.

        Args:
            remote: Include remote branches

        Returns:
            List of branch names
        """
        args = ["branch", "--format=%(refname:short)"]
        if remote:
            args.append("-a")

        result = self._run_git(args)
        return [b for b in result.stdout.strip().split("\n") if b]

    def get_remotes(self) -> list[str]:
        """Get list of configured remotes."""
        result = self._run_git(["remote"])
        return [r for r in result.stdout.strip().split("\n") if r]

    def get_remote_url(self, remote: str = "origin") -> str | None:
        """Get URL of a remote."""
        try:
            result = self._run_git(["remote", "get-url", remote])
            return result.stdout.strip()
        except GitDocsError:
            return None

    def is_dirty(self) -> bool:
        """Check if working tree has uncommitted changes."""
        result = self._run_git(["status", "--porcelain"], check=False)
        return bool(result.stdout.strip())

    def get_uncommitted_changes(self) -> list[str]:
        """Get list of uncommitted file changes."""
        result = self._run_git(["status", "--porcelain"])
        return [line[3:] for line in result.stdout.strip().split("\n") if line]
