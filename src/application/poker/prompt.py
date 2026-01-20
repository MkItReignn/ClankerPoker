"""Poker-specific prompt formatting for LLM consumption."""

from __future__ import annotations

from src.application.poker.context import (OpponentCurrentState,
                                           PokerDecisionContext)
from src.application.protocols.player import PlayerConfig
from src.config.poker.prompt import PokerPromptConfig
from src.domain.models.available_action import (AvailableActions,
                                                AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableCheckAction,
                                                AvailableFoldAction,
                                                AvailableRaiseAction)


class PokerPromptFormatter:
    """Formats poker decision context into LLM prompts.

    Produces a dense, structured format optimized for LLM comprehension.
    """

    def __init__(self, prompt_config: PokerPromptConfig) -> None:
        self._prompt_config: PokerPromptConfig = prompt_config

    @staticmethod
    def _format_cards(cards: tuple) -> str:
        """Format multiple cards."""
        if not cards:
            return "-"
        return " ".join(str(c) for c in cards)

    @staticmethod
    def _format_opponent_status(opponent: OpponentCurrentState) -> str:
        """Format opponent status indicator."""
        if opponent.is_folded:
            return "F"
        if opponent.is_all_in:
            return "AI"
        return "A"  # Active

    @staticmethod
    def _format_available_action(action: AvailableActions) -> str:
        """Format a single available action."""
        match action:
            case AvailableFoldAction():
                return "fold"
            case AvailableCheckAction():
                return "check"
            case AvailableCallAction():
                return f"call:{action.call_amount.value}"
            case AvailableBetAction():
                return f"bet:{action.min_bet_amount.value}-{action.max_bet_amount.value}"
            case AvailableRaiseAction():
                return f"raise:{action.min_raise_amount.value}-{action.max_raise_amount.value}"
            case AvailableAllInAction():
                return f"all_in:{action.all_in_amount.value}"
            case _:
                return str(action.action_type.value)

    def _format_prompt(
        self,
        context: PokerDecisionContext,
        available_actions: list[AvailableActions],
    ) -> str:
        """Format context and available actions into an LLM prompt.

        Args:
            context: The poker decision context.
            available_actions: List of legal actions.

        Returns:
            Formatted prompt string.
        """
        lines: list[str] = []

        # Header with hand info
        lines.append(
            f"=== HAND #{context.hand_state.hand_number} | PHASE: {context.hand_state.phase.value.upper()} ==="
        )
        lines.append("")

        # Your state
        hole_cards = self._format_cards(
            (context.acting_player.hole_cards.card1, context.acting_player.hole_cards.card2)
        )
        position = (
            context.acting_player.position.to_short_string()
            if context.acting_player.position is not None
            else "?"
        )
        lines.append(
            f"YOU: {hole_cards} | POS: {position} | STACK: {context.acting_player.stack.value}"
        )
        lines.append(f"     Stack in BB: {context.stack_in_bb:.1f}")
        lines.append("")

        # Board state
        board = (
            self._format_cards(context.hand_state.community_cards)
            if context.hand_state.community_cards
            else "-"
        )
        lines.append(f"BOARD: {board}")
        lines.append(
            f"POT: {context.hand_state.pot_total.value} | CALL: {context.hand_state.current_bet.value} | BB: {context.hand_state.blinds.big_blind.value}"
        )

        # Pot odds if applicable
        if context.pot_odds is not None:
            lines.append(f"POT ODDS: {context.pot_odds:.1f}:1")

        # Heads-up indicator
        if context.is_heads_up:
            lines.append("HEADS-UP: Yes")
        lines.append("")

        # Opponents
        if context.opponents:
            lines.append("OPPONENTS:")
            for opp in context.opponents:
                pos = opp.position.to_short_string() if opp.position is not None else "?"
                status = self._format_opponent_status(opp)
                invested = (
                    f"invested:{opp.invested_this_hand.value}"
                    if opp.invested_this_hand.value > 0
                    else ""
                )
                lines.append(
                    f"  {opp.name} ({pos}): {opp.stack.value} chips [{status}] {invested}".strip()
                )
            lines.append("")

        # Actions this hand
        if context.current_hand_history.text:
            lines.append(context.current_hand_history.text)
            lines.append("")

        # Previous hands
        if context.previous_hand_history.text:
            lines.append(context.previous_hand_history.text)
            lines.append("")

        # Available actions
        actions_str = " | ".join(self._format_available_action(a) for a in available_actions)
        lines.append(f"AVAILABLE: {actions_str}")
        lines.append("")

        # Add response guidelines and format from config
        user_components = self._prompt_config.user_prompt
        lines.append(user_components.response_guidelines.thought_process_guidelines)
        lines.append("")
        lines.append(user_components.response_guidelines.action_guidelines)
        lines.append("")
        lines.append(user_components.response_format)

        return "\n".join(lines)

    def _format_system_prompt(
        self, player_name: str, personality: str | None = None, addon_prompt: str | None = None
    ) -> str:
        """Format a system prompt for the poker player.

        Composes system prompt from structured components:
        - Identity (elite player expertise and mission)
        - Context format guide (complete field documentation)
        - History notation (action shorthand reference)
        - Decision framework (9-category systematic thinking)
        - Personality section (if provided)
        - Addon section (if provided)

        Args:
            player_name: The player's display name.
            personality: Optional personality description.
            addon_prompt: Optional additional prompt text.

        Returns:
            System prompt string composed from components.
        """
        components = self._prompt_config.system_prompt

        # Compose all sections
        parts: list[str] = [
            components.identity.format(player_name=player_name),
            components.context_format_guide,
            components.history_notation,
            components.decision_framework,
        ]

        # Add personality if provided
        if personality:
            parts.append(components.personality_section.format(personality=personality))

        # Add addon prompt if provided
        if addon_prompt:
            parts.append(components.addon_section.format(addon_prompt=addon_prompt))

        return "\n\n".join(parts)

    def format_prompts(
        self,
        context: PokerDecisionContext,
        available_actions: list[AvailableActions],
        player_config: PlayerConfig,
    ) -> tuple[str, str]:
        """Format both system and user prompts for LLM consumption.

        Args:
            context: The poker decision context.
            available_actions: List of legal actions.
            player_config: Player configuration containing name, personality, and addon_prompt.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        # Generate core system prompt from config
        system_prompt = self._format_system_prompt(
            player_name=player_config.name,
            personality=player_config.personality,
            addon_prompt=player_config.addon_prompt,
        )

        # Generate user prompt from game context
        user_prompt = self._format_prompt(context, available_actions)

        return (system_prompt, user_prompt)
