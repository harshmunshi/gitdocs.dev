"""LLM integration module for AI-assisted suggestions."""

from gitdocs.llm.client import LLMClient, TicketSuggestion, create_llm_client

__all__ = ["LLMClient", "create_llm_client", "TicketSuggestion"]
