"""Tests for git integration."""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime

from gitdocs.git.repo import GitRepo, Commit, DiffStat
from gitdocs.git.diff import parse_unified_diff, summarize_diff, FileDiff
from gitdocs.store.mappings import (
    extract_ticket_keys,
    suggest_ticket_from_branch,
    find_related_tickets,
)


class TestCommit:
    """Tests for Commit model."""
    
    def test_short_sha(self):
        """Test short SHA property."""
        commit = Commit(
            sha="abc123def456",
            message="Test commit",
            author_name="Test",
            author_email="test@test.com",
            date=datetime.now(),
        )
        
        assert commit.short_sha == "abc123d"
    
    def test_subject(self):
        """Test subject property."""
        commit = Commit(
            sha="abc123",
            message="First line\n\nMore details here",
            author_name="Test",
            author_email="test@test.com",
            date=datetime.now(),
        )
        
        assert commit.subject == "First line"


class TestExtractTicketKeys:
    """Tests for ticket key extraction."""
    
    def test_basic_extraction(self):
        """Test basic ticket key extraction."""
        text = "Fixed bug in PROJ-123"
        keys = extract_ticket_keys(text)
        
        assert keys == ["PROJ-123"]
    
    def test_multiple_keys(self):
        """Test extracting multiple keys."""
        text = "PROJ-123: Fixed bug related to ABC-456"
        keys = extract_ticket_keys(text)
        
        assert "PROJ-123" in keys
        assert "ABC-456" in keys
    
    def test_case_insensitive(self):
        """Test case insensitive extraction."""
        text = "proj-123 and Proj-456"
        keys = extract_ticket_keys(text)
        
        assert "PROJ-123" in keys
        assert "PROJ-456" in keys
    
    def test_no_false_positives(self):
        """Test that random text doesn't match."""
        text = "This is just a regular commit message"
        keys = extract_ticket_keys(text)
        
        assert keys == []
    
    def test_custom_patterns(self):
        """Test custom patterns."""
        text = "Fixed bug #123"
        patterns = [r"#(\d+)"]
        keys = extract_ticket_keys(text, patterns)
        
        # Custom pattern returns the captured group
        assert "123" in keys


class TestSuggestTicketFromBranch:
    """Tests for branch name ticket extraction."""
    
    def test_feature_branch(self):
        """Test feature branch pattern."""
        branch = "feature/PROJ-123-add-login"
        key = suggest_ticket_from_branch(branch)
        
        assert key == "PROJ-123"
    
    def test_ticket_prefix_branch(self):
        """Test ticket as prefix."""
        branch = "PROJ-456-fix-bug"
        key = suggest_ticket_from_branch(branch)
        
        assert key == "PROJ-456"
    
    def test_no_ticket(self):
        """Test branch without ticket."""
        branch = "main"
        key = suggest_ticket_from_branch(branch)
        
        assert key is None


class TestFindRelatedTickets:
    """Tests for finding tickets in commits."""
    
    def test_group_by_ticket(self):
        """Test grouping commits by ticket."""
        commits = [
            "PROJ-1: First commit",
            "PROJ-1: Second commit",
            "PROJ-2: Different ticket",
        ]
        
        result = find_related_tickets(commits)
        
        assert "PROJ-1" in result
        assert "PROJ-2" in result
        assert len(result["PROJ-1"]) == 2
        assert len(result["PROJ-2"]) == 1


class TestDiffParsing:
    """Tests for diff parsing."""
    
    def test_parse_simple_diff(self):
        """Test parsing a simple diff."""
        diff = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line 1
+new line
 line 2
 line 3
"""
        
        result = parse_unified_diff(diff)
        
        assert len(result) == 1
        assert result[0].path == "file.py"
        assert result[0].additions == 1
        assert result[0].deletions == 0
    
    def test_parse_new_file(self):
        """Test parsing diff for new file."""
        diff = """diff --git a/new.py b/new.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/new.py
@@ -0,0 +1,3 @@
+line 1
+line 2
+line 3
"""
        
        result = parse_unified_diff(diff)
        
        assert len(result) == 1
        assert result[0].status == "A"
        assert result[0].additions == 3
    
    def test_summarize_diff(self):
        """Test diff summary generation."""
        diffs = [
            FileDiff(path="a.py", old_path=None, status="M", additions=10, deletions=5, hunks=[]),
            FileDiff(path="b.py", old_path=None, status="A", additions=20, deletions=0, hunks=[]),
        ]
        
        summary = summarize_diff(diffs)
        
        assert "2 files changed" in summary
        assert "+30/-5" in summary
        assert "a.py" in summary
        assert "b.py" in summary

