from __future__ import annotations

from src.application.poker.parser.parser import PokerResponseParser
from src.application.poker.prompt import PokerPromptFormatter
from src.application.services.llm_action_provider import LlmActionProvider
from src.config.poker.action_provider import ActionProviderConfig
from src.config.poker.prompt import PokerPromptConfig
from src.infrastructure.llm.open_router.client import OpenRouterClient


def create_poker_llm_action_provider(
    client: OpenRouterClient,
    prompt_config: PokerPromptConfig,
    provider_config: ActionProviderConfig,
) -> LlmActionProvider:
    formatter: PokerPromptFormatter = PokerPromptFormatter(prompt_config)
    parser: PokerResponseParser = PokerResponseParser()

    return LlmActionProvider(
        llm_client=client,
        prompt_formatter=formatter.format_prompts,
        response_parser=parser.parse_response,
        fallback_selector=parser.get_fallback_action,
        config=provider_config,
        prompt_config=prompt_config,
    )
