"""Game-agnostic protocols for LLM game players."""

from src.application.protocols.context import ContextBuilder, PromptFormatter
from src.application.protocols.history import GameHistoryRepository
from src.application.protocols.llm import LlmClient, LlmRequest, LlmResponse
from src.application.protocols.player import (ActionResponse,
                                              AsyncActionProvider,
                                              PlayerConfig)
from src.application.protocols.response import ParseResult, ResponseParser

__all__ = [
    # Player protocols
    "ActionResponse",
    "AsyncActionProvider",
    "PlayerConfig",
    # Context protocols
    "ContextBuilder",
    "PromptFormatter",
    # Response protocols
    "ParseResult",
    "ResponseParser",
    # LLM protocols
    "LlmClient",
    "LlmRequest",
    "LlmResponse",
    # History protocols
    "GameHistoryRepository",
]
