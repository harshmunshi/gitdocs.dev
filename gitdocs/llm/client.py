"""LLM client interface and implementations."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from gitdocs.core.config import LLMConfig
from gitdocs.core.errors import LLMError

logger = logging.getLogger(__name__)


@dataclass
class TicketSuggestion:
    """Suggested ticket update."""

    ticket_key: str
    comment: str
    confidence: float
    reasoning: str | None = None


@dataclass
class DocSuggestion:
    """Suggested documentation update."""

    page_title: str
    summary: str
    suggested_changes: str
    confidence: float


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def suggest_ticket_update(
        self,
        ticket_key: str,
        commits: str,
        diff_summary: str,
        ticket_context: str | None = None,
    ) -> TicketSuggestion | None:
        """
        Generate a suggested Jira comment based on commits.

        Args:
            ticket_key: The ticket being updated
            commits: Summary of related commits
            diff_summary: Summary of code changes
            ticket_context: Optional existing ticket description/comments

        Returns:
            TicketSuggestion if confident enough, None otherwise
        """
        pass

    @abstractmethod
    def suggest_doc_update(
        self,
        page_content: str,
        code_changes: str,
    ) -> DocSuggestion | None:
        """
        Suggest documentation updates based on code changes.

        Args:
            page_content: Current documentation content
            code_changes: Summary of related code changes

        Returns:
            DocSuggestion if relevant updates found
        """
        pass

    @abstractmethod
    def classify_commit(
        self,
        message: str,
        diff: str,
    ) -> dict:
        """
        Classify a commit for ticket matching.

        Args:
            message: Commit message
            diff: Commit diff

        Returns:
            Classification dict with type, scope, etc.
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI-based LLM client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        confidence_threshold: float = 0.7,
        max_tokens: int = 1000,
    ) -> None:
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use
            temperature: Generation temperature
            confidence_threshold: Minimum confidence for suggestions
            max_tokens: Maximum tokens for generation
        """
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
        except ImportError:
            raise LLMError("OpenAI package not installed. Run: pip install openai")

        self.model = model
        self.temperature = temperature
        self.confidence_threshold = confidence_threshold
        self.max_tokens = max_tokens

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Make a chat completion request."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"OpenAI API error: {e}")

    def suggest_ticket_update(
        self,
        ticket_key: str,
        commits: str,
        diff_summary: str,
        ticket_context: str | None = None,
    ) -> TicketSuggestion | None:
        """Generate ticket update suggestion."""
        system_prompt = """You are a developer assistant that helps write Jira ticket comments.
Your goal is to summarize code changes in a clear, professional way for the ticket.

Guidelines:
- Be concise but informative
- Focus on what was changed and why
- Use technical language appropriate for developers
- Don't include commit hashes unless specifically relevant
- Format as plain text suitable for a Jira comment

Respond with ONLY the comment text, no extra formatting or explanation.
If the commits don't seem related to meaningful work, respond with "NO_SUGGESTION".
"""

        user_prompt = f"""Ticket: {ticket_key}

Related commits:
{commits}

Code changes summary:
{diff_summary or 'Not provided'}

{f'Ticket context: {ticket_context}' if ticket_context else ''}

Write a brief Jira comment summarizing what was done:"""

        try:
            response = self._chat(system_prompt, user_prompt)

            if "NO_SUGGESTION" in response:
                return None

            # Basic confidence estimation based on response quality
            confidence = 0.8 if len(response) > 50 else 0.6

            if confidence < self.confidence_threshold:
                return None

            return TicketSuggestion(
                ticket_key=ticket_key,
                comment=response.strip(),
                confidence=confidence,
            )
        except LLMError:
            return None

    def suggest_doc_update(
        self,
        page_content: str,
        code_changes: str,
    ) -> DocSuggestion | None:
        """Suggest documentation updates."""
        system_prompt = """You are a technical writer assistant.
Analyze if documentation needs updates based on code changes.

Respond in this format:
TITLE: [page section that needs update]
SUMMARY: [brief description of needed changes]
CHANGES: [specific suggested edits]
CONFIDENCE: [0.0-1.0]

If no updates needed, respond with "NO_UPDATES_NEEDED"."""

        user_prompt = f"""Current documentation:
{page_content[:2000]}

Recent code changes:
{code_changes}

Analyze if documentation updates are needed:"""

        try:
            response = self._chat(system_prompt, user_prompt)

            if "NO_UPDATES_NEEDED" in response:
                return None

            # Parse response
            lines = response.strip().split("\n")
            title = ""
            summary = ""
            changes = ""
            confidence = 0.5

            for line in lines:
                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("CHANGES:"):
                    changes = line.replace("CHANGES:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                    except ValueError:
                        pass

            if confidence < self.confidence_threshold:
                return None

            return DocSuggestion(
                page_title=title,
                summary=summary,
                suggested_changes=changes,
                confidence=confidence,
            )
        except LLMError:
            return None

    def classify_commit(
        self,
        message: str,
        diff: str,
    ) -> dict:
        """Classify a commit."""
        system_prompt = """Classify this git commit.

Respond with JSON:
{
  "type": "feature|bugfix|refactor|docs|chore|test",
  "scope": "component or area affected",
  "breaking": true|false,
  "summary": "one-line summary"
}"""

        user_prompt = f"""Commit message: {message}

Diff preview:
{diff[:1000]}"""

        try:
            import json

            response = self._chat(system_prompt, user_prompt)
            return json.loads(response)
        except Exception:
            return {
                "type": "unknown",
                "scope": "",
                "breaking": False,
                "summary": message.split("\n")[0],
            }


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and when no LLM is configured."""

    def suggest_ticket_update(
        self,
        ticket_key: str,
        commits: str,
        diff_summary: str,
        ticket_context: str | None = None,
    ) -> TicketSuggestion | None:
        """Return None (no suggestions without real LLM)."""
        return None

    def suggest_doc_update(
        self,
        page_content: str,
        code_changes: str,
    ) -> DocSuggestion | None:
        """Return None."""
        return None

    def classify_commit(
        self,
        message: str,
        diff: str,
    ) -> dict:
        """Return basic classification."""
        return {
            "type": "unknown",
            "scope": "",
            "breaking": False,
            "summary": message.split("\n")[0] if message else "",
        }


def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    Create an LLM client based on configuration.

    Args:
        config: LLM configuration

    Returns:
        Configured LLM client
    """
    from gitdocs.core.secrets import get_openai_api_key

    if config.provider == "openai":
        api_key = get_openai_api_key()
        if not api_key:
            logger.warning("OpenAI API key not configured, using mock client")
            return MockLLMClient()

        return OpenAIClient(
            api_key=api_key,
            model=config.model,
            temperature=config.temperature,
            confidence_threshold=config.confidence_threshold,
            max_tokens=config.max_tokens,
        )

    logger.warning(f"Unknown LLM provider '{config.provider}', using mock client")
    return MockLLMClient()
