"""Bot action provider for poker games."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Self

from src.application.poker.providers.bot_random_action_selector import \
    BotRandomActionSelector
from src.application.protocols.player import ActionResponse, PlayerConfig
from src.config.poker.bot_config import BotPokerGameConfig
from src.config.poker.bot_personality import BotPersonality
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.narration import Narration, NarrationText

if TYPE_CHECKING:
    from src.application.poker.context import PokerDecisionContext


@dataclass(frozen=True, slots=True)
class BotPlayerConfig:
    """Configuration for a bot player's behavior.

    Pairs an action selector with an optional narration template.
    The template can use {action} placeholder for the action text.
    """

    DEFAULT_NARRATION_TEMPLATE: ClassVar[str] = "I have chosen to {action}."

    selector: BotRandomActionSelector
    narration_template: str | None = None

    def create_narration(self, action: Action) -> Narration | None:
        """Create a narration for the given action.

        Args:
            action: The action taken.

        Returns:
            Narration if template is set, None otherwise.
        """
        if self.narration_template is None:
            return None

        action_text = self._format_action(action)
        text = self.narration_template.format(action=action_text)
        return Narration(thought_process=NarrationText(text))

    def _format_action(self, action: Action) -> str:
        """Format an action for display in narration."""
        action_name = action.action_type.value.replace("_", " ")
        if action.amount is not None:
            return f"{action_name} {action.amount.value}"
        return action_name


class BotActionProvider:
    """Action provider that uses weighted random selection.

    Implements AsyncActionProvider protocol for bot players.
    Uses BotRandomActionSelector to choose actions with configurable
    playing styles (aggressive, passive, tight, loose).
    """

    def __init__(
        self,
        default_config: BotPlayerConfig | None = None,
        player_configs: dict[str, BotPlayerConfig] | None = None,
    ) -> None:
        """Initialize the bot action provider.

        Args:
            default_config: Default bot config for all players.
            player_configs: Optional per-player configs.
        """
        self._default_config = default_config or BotPlayerConfig(selector=BotRandomActionSelector())
        self._player_configs = player_configs or {}

    async def get_action(
        self,
        context: PokerDecisionContext,
        available_actions: list[AvailableActions],
        config: PlayerConfig,
    ) -> ActionResponse[Action, Narration]:
        """Get an action for the current game state.

        Args:
            context: Decision context with game state.
            available_actions: Available actions for the player.
            config: Player configuration.

        Returns:
            ActionResponse with chosen action.
        """
        # Get config for this player (or default)
        bot_config = self._player_configs.get(config.player_id, self._default_config)

        # Select action
        action = bot_config.selector.select_action(available_actions)

        # Create narration if template is set
        narration = bot_config.create_narration(action)

        return ActionResponse(
            action=action,
            narration=narration,
        )

    @classmethod
    def aggressive(
        cls, seed: int | None = None, narration_template: str | None = None
    ) -> BotActionProvider:
        """Create an aggressive bot provider."""
        return cls(
            default_config=BotPlayerConfig(
                selector=BotRandomActionSelector.aggressive(seed),
                narration_template=narration_template,
            )
        )

    @classmethod
    def passive(
        cls, seed: int | None = None, narration_template: str | None = None
    ) -> BotActionProvider:
        """Create a passive bot provider."""
        return cls(
            default_config=BotPlayerConfig(
                selector=BotRandomActionSelector.passive(seed),
                narration_template=narration_template,
            )
        )

    @classmethod
    def tight(
        cls, seed: int | None = None, narration_template: str | None = None
    ) -> BotActionProvider:
        """Create a tight bot provider."""
        return cls(
            default_config=BotPlayerConfig(
                selector=BotRandomActionSelector.tight(seed),
                narration_template=narration_template,
            )
        )

    @classmethod
    def loose(
        cls, seed: int | None = None, narration_template: str | None = None
    ) -> BotActionProvider:
        """Create a loose bot provider."""
        return cls(
            default_config=BotPlayerConfig(
                selector=BotRandomActionSelector.loose(seed),
                narration_template=narration_template,
            )
        )

    @classmethod
    def with_player_configs(
        cls,
        player_configs: dict[str, BotPlayerConfig],
        default: BotPlayerConfig | None = None,
    ) -> BotActionProvider:
        """Create a provider with different configs per player.

        Args:
            player_configs: Map of player_id to BotPlayerConfig.
            default: Default config for players not in map.

        Returns:
            BotActionProvider with per-player configs.
        """
        return cls(
            default_config=default,
            player_configs=player_configs,
        )

    @classmethod
    def with_seed(cls, seed: int, narration_template: str | None = None) -> BotActionProvider:
        """Create a provider with a fixed random seed.

        Useful for reproducible games/testing.

        Args:
            seed: Random seed for action selection.
            narration_template: Optional narration template.

        Returns:
            BotActionProvider with seeded selector.
        """
        return cls(
            default_config=BotPlayerConfig(
                selector=BotRandomActionSelector(seed=seed),
                narration_template=narration_template,
            )
        )

    @classmethod
    def from_bot_config(
        cls,
        bot_config: BotPokerGameConfig,
        seed: int | None = None,
    ) -> BotActionProvider:
        """Create a provider from bot game configuration.

        Maps each player's personality to the appropriate selector.

        Args:
            bot_config: Bot game configuration with player personalities.
            seed: Optional random seed for reproducibility.

        Returns:
            BotActionProvider with per-player configs based on personalities.
        """
        personality_to_selector = {
            BotPersonality.AGGRESSIVE: BotRandomActionSelector.aggressive,
            BotPersonality.PASSIVE: BotRandomActionSelector.passive,
            BotPersonality.TIGHT: BotRandomActionSelector.tight,
            BotPersonality.LOOSE: BotRandomActionSelector.loose,
            BotPersonality.DEFAULT: BotRandomActionSelector,
        }

        player_configs: dict[str, BotPlayerConfig] = {}
        for player_id, player_cfg in bot_config.player_configs.items():
            selector_factory = personality_to_selector[player_cfg.personality]
            selector = selector_factory(seed=seed)
            player_configs[player_id] = BotPlayerConfig(selector=selector)

        return cls.with_player_configs(player_configs)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass
