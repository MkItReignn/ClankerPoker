from dataclasses import dataclass

from src.application.poker.orchestration.poker_orchestrator import (
    PokerActionProvider,
)
from src.application.poker.parser.parser import PokerResponseParser
from src.application.poker.prompt import PokerPromptFormatter
from src.application.services.llm_action_provider import LlmActionProvider
from src.config.llm.config import OpenRouterConfig
from src.config.poker.action_provider import ActionProviderConfig
from src.config.poker.bot_config import BotPokerGameConfig
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.poker.prompt import PokerPromptConfig
from src.domain.models.llm_model import LlmModel
from src.infrastructure.llm.open_router.client import OpenRouterClient


@dataclass(frozen=True, slots=True)
class GameDependencies:
    action_provider: PokerActionProvider
    poker_config: PokerGameConfig


def create_bot_dependencies(seed: int | None = None) -> GameDependencies:
    from src.application.poker.providers.bot_action_provider import (
        BotActionProvider,
    )
    from src.config.poker.bot_config_loader import BotPokerGameConfigLoader

    bot_config: BotPokerGameConfig = BotPokerGameConfigLoader().load()
    action_provider: BotActionProvider = BotActionProvider.from_bot_config(
        bot_config, seed=seed
    )

    poker_player_configs: dict[str, PokerPlayerConfig] = {
        player_id: PokerPlayerConfig(
            player_id=player_id,
            name=bot_cfg.name,
            model_id=LlmModel.NONE,
        )
        for player_id, bot_cfg in bot_config.player_configs.items()
    }
    poker_config: PokerGameConfig = PokerGameConfig(
        player_configs=poker_player_configs
    )

    return GameDependencies(
        action_provider=action_provider,
        poker_config=poker_config,
    )


def create_llm_dependencies() -> GameDependencies:
    from src.config.llm.config_loader import OpenRouterConfigLoader
    from src.config.poker.action_provider import ActionProviderConfigLoader
    from src.config.poker.config_loader import PokerGameConfigLoader
    from src.config.poker.prompt import PokerPromptConfigLoader

    openrouter_config: OpenRouterConfig = OpenRouterConfigLoader().load()
    prompt_config: PokerPromptConfig = PokerPromptConfigLoader().load()
    poker_config: PokerGameConfig = PokerGameConfigLoader().load()
    provider_config: ActionProviderConfig = ActionProviderConfigLoader().load()

    client: OpenRouterClient = OpenRouterClient(openrouter_config)
    formatter: PokerPromptFormatter = PokerPromptFormatter(prompt_config)
    parser: PokerResponseParser = PokerResponseParser()

    action_provider: LlmActionProvider = LlmActionProvider(
        llm_client=client,
        prompt_formatter=formatter.format_prompts,
        response_parser=parser.parse_response,
        fallback_selector=parser.get_fallback_action,
        config=provider_config,
        prompt_config=prompt_config,
    )

    return GameDependencies(
        action_provider=action_provider,
        poker_config=poker_config,
    )
