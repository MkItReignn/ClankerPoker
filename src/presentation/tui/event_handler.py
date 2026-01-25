from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.poker.events import EventType, PublishedEvent
from src.presentation.tui.formatters import HandDescriptionFormatter

if TYPE_CHECKING:
    from src.presentation.tui.widgets.action_log import ActionLog
    from src.presentation.tui.widgets.header_bar import HeaderBar
    from src.presentation.tui.widgets.narration_panel import NarrationPanel
    from src.presentation.tui.widgets.poker_table import PokerTableArea


def _get_hand_description(
    player_id: str, showdown: list[dict[str, Any]] | None
) -> str | None:
    if not showdown:
        return None
    for sr in showdown:
        if sr.get("player_id") == player_id:
            hand_eval = sr.get("hand_evaluation", {})
            return HandDescriptionFormatter.format(hand_eval)
    return None


class EventHandler:
    """Maps game events to TUI widget updates."""

    def __init__(
        self,
        header: HeaderBar,
        table: PokerTableArea,
        action_log: ActionLog,
        narration: NarrationPanel,
    ) -> None:
        self._header = header
        self._table = table
        self._action_log = action_log
        self._narration = narration
        self._current_phase: str = "pre_flop"
        self._sb_seat: int | None = None
        self._bb_seat: int | None = None

    async def handle_event(self, event: PublishedEvent) -> None:
        game_state = event.game_state
        details = event.details

        if event.event_type == EventType.HAND_STARTED:
            self._sb_seat = details.get("sb_seat")
            self._bb_seat = details.get("bb_seat")

        game_state["sb_seat"] = self._sb_seat
        game_state["bb_seat"] = self._bb_seat

        self._header.update_from_game_state(game_state)
        self._table.update_from_game_state(game_state)

        handler_map = {
            EventType.GAME_STARTED: self._handle_game_started,
            EventType.GAME_COMPLETED: self._handle_game_completed,
            EventType.HAND_STARTED: self._handle_hand_started,
            EventType.HAND_COMPLETED: self._handle_hand_completed,
            EventType.ROUND_STARTED: self._handle_round_started,
            EventType.ROUND_COMPLETED: self._handle_round_completed,
            EventType.BLINDS_POSTED: self._handle_blinds_posted,
            EventType.ACTION_APPLIED: self._handle_action_applied,
            EventType.HOLE_CARDS_DEALT: self._handle_hole_cards_dealt,
            EventType.PLAYER_TO_ACT: self._handle_player_to_act,
        }

        handler = handler_map.get(event.event_type)
        if handler:
            handler(details, game_state)

    def _handle_game_started(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        player_count = details.get("player_count", 0)
        starting_chips = details.get("starting_chips", 0)
        self._action_log.add_entry(
            f"Tournament started: {player_count} players, {starting_chips:,} starting chips"
        )

    def _handle_game_completed(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        winner_id = details.get("winner_id")
        winner_name = details.get("winner_name", "Unknown")
        total_hands = details.get("total_hands", 0)
        final_standings = details.get("final_standings")
        self._action_log.add_game_complete(
            winner_name, total_hands, final_standings, winner_id
        )

    def _handle_hand_started(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        hand_number = details.get("hand_number", 1)
        button_seat = details.get("button_seat", 0)

        self._current_phase = ""
        self._table.clear_winner()
        self._action_log.add_hand_started(hand_number, button_seat)
        self._narration.add_hand_started(hand_number)

    def _handle_hand_completed(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        winners = details.get("winners", [])
        eliminated = details.get("eliminated", [])
        showdown = details.get("showdown")
        pot_amount = details.get("pot_amount", 0)
        hand_number = game_state.get("hand_state", {}).get("hand_number", 1)

        self._display_showdown(showdown, winners)
        self._display_winners(winners, showdown)
        self._display_eliminations(eliminated)
        self._display_hand_summary(winners, showdown, hand_number, pot_amount)
        self._narration.add_hand_completed(hand_number)

    def _display_showdown(
        self,
        showdown: list[dict[str, Any]] | None,
        winners: list[dict[str, Any]],
    ) -> None:
        if not showdown:
            return

        winner_ids = {w.get("player_id") for w in winners}

        for player_result in showdown:
            player_id = player_result.get("player_id")
            player_name = player_result.get("player_name", "Unknown")
            hole_cards = player_result.get("hole_cards", [])
            hand_eval = player_result.get("hand_evaluation", {})
            hand_description = HandDescriptionFormatter.format(hand_eval)
            is_winner = player_id in winner_ids

            self._action_log.add_showdown_result(
                player_name, hole_cards, hand_description, is_winner, player_id
            )

    def _display_winners(
        self,
        winners: list[dict[str, Any]],
        showdown: list[dict[str, Any]] | None,
    ) -> None:
        for winner in winners:
            winner_id = winner.get("player_id", "")
            winner_name = winner.get("player_name", "Unknown")
            amount = winner.get("amount", 0)

            self._table.set_winner(winner_id)
            hand_description = _get_hand_description(winner_id, showdown)
            self._action_log.add_winner(
                winner_name, amount, hand_description, winner_id
            )

    def _display_eliminations(self, eliminated: list[dict[str, Any]]) -> None:
        for elim in eliminated:
            elim_id = elim.get("player_id")
            elim_name = elim.get("player_name", "Unknown")
            position = elim.get("finish_position", 0)
            self._action_log.add_elimination(elim_name, position, elim_id)

    def _display_hand_summary(
        self,
        winners: list[dict[str, Any]],
        showdown: list[dict[str, Any]] | None,
        hand_number: int,
        pot_amount: int,
    ) -> None:
        if not winners:
            return

        winner = winners[0]
        winner_id = winner.get("player_id", "")
        winner_name = winner.get("player_name", "Unknown")
        amount = winner.get("amount", pot_amount)
        hand_description = _get_hand_description(winner_id, showdown)

        self._action_log.add_hand_complete(
            hand_number, winner_name, amount, hand_description, winner_id
        )

    def _handle_round_started(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        phase = details.get("phase", "pre_flop")
        new_cards = details.get("new_cards", [])

        if phase != self._current_phase:
            self._current_phase = phase

            community_cards = game_state.get("hand_state", {}).get(
                "community_cards", []
            )
            self._action_log.add_phase_separator(
                phase, community_cards if new_cards else None
            )
            self._narration.add_phase_header(
                phase, community_cards if new_cards else None
            )

    def _handle_round_completed(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        pass

    def _handle_blinds_posted(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        sb = details.get("small_blind", {})
        bb = details.get("big_blind", {})

        sb_player_id = sb.get("player_id")
        sb_name = sb.get("player_name", "Unknown")
        sb_amount = sb.get("amount", 0)
        bb_player_id = bb.get("player_id")
        bb_name = bb.get("player_name", "Unknown")
        bb_amount = bb.get("amount", 0)

        self._action_log.add_blinds_posted(
            sb_name, sb_amount, bb_name, bb_amount, sb_player_id, bb_player_id
        )

    def _handle_action_applied(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        player_id = details.get("player_id")
        player_name = details.get("player_name", "Unknown")
        action_type = details.get("action_type", "")
        amount = details.get("amount")
        narration = details.get("narration")

        self._action_log.add_action(
            player_name, action_type, amount, player_id
        )

        if narration:
            thought_process = narration.get("thought_process", "")
            if thought_process:
                self._narration.add_thought_process(
                    player_name, thought_process, player_id
                )

    def _handle_hole_cards_dealt(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        pass

    def _handle_player_to_act(
        self, details: dict[str, Any], game_state: dict[str, Any]
    ) -> None:
        player_id = details.get("player_id")
        player_name = details.get("player_name", "Unknown")
        self._action_log.add_thinking(player_name, player_id)
        self._narration.add_thinking(player_name, player_id)
