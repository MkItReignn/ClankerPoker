import secrets
from dataclasses import dataclass
from pathlib import Path

from src.application.poker.orchestration.poker_orchestrator import (
    PokerActionProvider,
)
from src.application.poker.parser.parser import PokerResponseParser
from src.application.poker.prompt import PokerPromptFormatter
from src.application.poker.records.models import GameRecord
from src.application.services.llm_action_provider import LlmActionProvider
from src.config.llm.config import OpenRouterConfig
from src.config.poker.action_provider import ActionProviderConfig
from src.config.poker.bot_config import BotPokerGameConfig
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.config.poker.prompt import PokerPromptConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.llm_model import LlmModel
from src.domain.utils.game_id import generate_game_id
from src.infrastructure.llm.open_router.client import OpenRouterClient
from src.infrastructure.persistence import JsonGameRecordRepository


@dataclass(frozen=True, slots=True)
class GameDependencies:
    action_provider: PokerActionProvider
    poker_config: PokerGameConfig


@dataclass(frozen=True, slots=True)
class ReplayDependencies:
    action_provider: PokerActionProvider
    poker_config: PokerGameConfig
    tournament_config: TournamentConfig
    seed: int
    game_id: str


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Unified runtime configuration for all game modes."""

    action_provider: PokerActionProvider
    poker_config: PokerGameConfig
    tournament_config: TournamentConfig
    seed: int
    game_id: str
    repository: JsonGameRecordRepository | None


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
            llm_model=LlmModel.NONE,
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


def create_replay_dependencies(record_path: Path) -> ReplayDependencies:
    from src.application.poker.records.models import GameRecord
    from src.application.replay import RecordLoader, ReplayActionProvider

    record: GameRecord = RecordLoader.load(record_path)

    poker_player_configs: dict[str, PokerPlayerConfig] = {
        player_id: PokerPlayerConfig(
            player_id=player_id,
            name=player_record.player_name,
            llm_model=player_record.llm_model,
            personality=player_record.player_config.personality,
            addon_prompt=player_record.player_config.addon_prompt,
        )
        for player_id, player_record in record.player_records.items()
    }

    poker_config: PokerGameConfig = PokerGameConfig(
        player_configs=poker_player_configs
    )

    tournament_config: TournamentConfig = TournamentConfig(
        buy_in_amount=record.metadata.buy_in_amount,
        starting_chip_stack=record.metadata.starting_chip_stack,
        payout_structure=record.metadata.payout_structure,
        blind_schedule=record.metadata.blind_schedule,
    )

    action_provider: ReplayActionProvider = ReplayActionProvider(record)

    return ReplayDependencies(
        action_provider=action_provider,
        poker_config=poker_config,
        tournament_config=tournament_config,
        seed=record.metadata.seed,
        game_id=record.game_id,
    )


class RuntimeConfigFactory:
    """Creates RuntimeConfig for different game modes."""

    @staticmethod
    def for_bot(seed: int | None = None) -> RuntimeConfig:
        from src.config.tournament import TournamentConfigLoader

        effective_seed: int = (
            seed if seed is not None else secrets.randbits(64)
        )
        deps: GameDependencies = create_bot_dependencies(seed=effective_seed)

        return RuntimeConfig(
            action_provider=deps.action_provider,
            poker_config=deps.poker_config,
            tournament_config=TournamentConfigLoader().load(),
            seed=effective_seed,
            game_id=generate_game_id(),
            repository=JsonGameRecordRepository(),
        )

    @staticmethod
    def for_llm(seed: int | None = None) -> RuntimeConfig:
        from src.config.tournament import TournamentConfigLoader

        effective_seed: int = (
            seed if seed is not None else secrets.randbits(64)
        )
        deps: GameDependencies = create_llm_dependencies()

        return RuntimeConfig(
            action_provider=deps.action_provider,
            poker_config=deps.poker_config,
            tournament_config=TournamentConfigLoader().load(),
            seed=effective_seed,
            game_id=generate_game_id(),
            repository=JsonGameRecordRepository(),
        )

    @staticmethod
    def for_replay(record_path: Path) -> RuntimeConfig:
        deps: ReplayDependencies = create_replay_dependencies(record_path)

        return RuntimeConfig(
            action_provider=deps.action_provider,
            poker_config=deps.poker_config,
            tournament_config=deps.tournament_config,
            seed=deps.seed,
            game_id=deps.game_id,
            repository=None,
        )
