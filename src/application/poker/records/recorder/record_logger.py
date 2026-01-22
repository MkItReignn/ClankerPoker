"""Record-based logger for automatic game event logging."""

from __future__ import annotations

from src.application.poker.records.models import (GameRecord, HandOutcome,
                                                  HandRecord, PlayerOutcome,
                                                  RoundRecord, TurnRecord)
from src.domain.models.player import HandParticipationStatus
from src.logger.factories import get_generic_logger


class RecordLogger:
    """Logs game events automatically from record updates.

    Extracts structured log messages from record objects without
    requiring separate logging calls throughout the codebase.
    """

    def __init__(self) -> None:
        self._logger = get_generic_logger(__name__.removeprefix("src."))

    def log_game_started(self, record: GameRecord) -> None:
        """Log tournament start with all players."""
        players_info = [
            {
                "id": pid,
                "name": player_record.player_name,
                "seat": player_record.seat.value,
                "chips": player_record.chips.value,
                "model": player_record.model_id.value,
            }
            for pid, player_record in record.player_records.items()
        ]

        self._logger.info(
            "Tournament started",
            game_id=record.game_id,
            players=players_info,
            player_count=len(players_info),
            seed=record.metadata.seed,
            starting_chips=record.metadata.starting_chip_stack.value,
        )

    def log_hand_started(self, hand: HandRecord) -> None:
        """Log hand start with blind level and player details."""
        sorted_records = sorted(hand.player_records.values(), key=lambda s: s.seat.value)
        players_info = [
            {
                "name": player_record.player_name,
                "model": player_record.model_id.value,
                "seat": player_record.seat.value,
                "position": player_record.position.value if player_record.position else None,
                "hole_cards": (
                    f"{player_record.hole_cards.card1} {player_record.hole_cards.card2}"
                    if player_record.hole_cards
                    else None
                ),
                "stack": player_record.chips.value,
            }
            for player_record in sorted_records
        ]

        self._logger.info(
            "Hand started",
            hand=hand.hand_number,
            blind_level=hand.blinds.level,
            blinds=f"{hand.blinds.small_blind.value}/{hand.blinds.big_blind.value}",
            button_seat=hand.button_seat.value,
            players=players_info,
        )

    def log_round_advanced(self, hand: HandRecord, round_record: RoundRecord) -> None:
        phase = round_record.phase.value.upper()
        board = " ".join(str(card) for card in round_record.community_cards)

        self._logger.info(
            f"*** {phase} ***",
            hand=hand.hand_number,
            board=board,
        )

    def log_betting_round_ended(self, hand: HandRecord, round_record: RoundRecord) -> None:
        action_counts: dict[str, int] = {}
        for turn in round_record.turns:
            action_type = turn.action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        folded = [
            ps.player_name
            for ps in round_record.player_records.values()
            if ps.participation_status == HandParticipationStatus.FOLDED
        ]
        all_in = [ps.player_name for ps in round_record.player_records.values() if ps.is_all_in]

        self._logger.info(
            "Betting round ended",
            hand=hand.hand_number,
            phase=round_record.phase.value,
            actions=action_counts,
            folded=folded if folded else None,
            all_in=all_in if all_in else None,
        )

    def log_action_taken(self, turn: TurnRecord, hand_number: int) -> None:
        amount = turn.action.amount.value if turn.action.amount else 0

        self._logger.info(
            "Action",
            hand=hand_number,
            player=turn.action.player_name,
            action=turn.action.action_type.value,
            amount=amount,
        )

    def log_hand_completed(self, hand: HandRecord, outcome: HandOutcome) -> None:
        """Log hand completion with showdown details."""
        winners_info: list[str] = []
        if outcome.winner_ids and outcome.player_outcomes:
            winner_map = {po.player_id: po for po in outcome.player_outcomes}
            for winner_id in outcome.winner_ids:
                if winner_id in winner_map:
                    po = winner_map[winner_id]
                    winners_info.append(f"{po.player_name}: {po.chips_won.value}")

        players_remaining = sum(1 for po in outcome.player_outcomes if not po.was_eliminated)

        showdown_info: list[dict[str, str]] = []
        if outcome.was_showdown and outcome.showdown_results:
            for sr in outcome.showdown_results:
                showdown_info.append(
                    {
                        "player": sr.player_name,
                        "hole_cards": f"{sr.hole_cards.card1} {sr.hole_cards.card2}",
                        "hand": str(sr.hand_evaluation),
                    }
                )

        self._logger.info(
            "Hand completed",
            hand=hand.hand_number,
            winners=winners_info,
            pot=outcome.pot_amount.value,
            was_showdown=outcome.was_showdown,
            showdown=showdown_info if showdown_info else None,
            players_remaining=players_remaining,
        )

    def log_player_standings(self, hand: HandRecord, outcome: HandOutcome) -> None:
        """Log player standings after hand."""
        standings_info = [
            f"{po.player_name}: {po.final_stack.value} ({'eliminated' if po.was_eliminated else 'active'})"
            for po in sorted(
                outcome.player_outcomes, key=lambda p: p.final_stack.value, reverse=True
            )
        ]

        self._logger.info(
            "Standings",
            hand=hand.hand_number,
            standings=standings_info,
        )

    def log_player_eliminated(
        self,
        hand_number: int,
        player_id: str,
        player_name: str,
        eliminated_by: str | None,
        position: int,
    ) -> None:
        """Log player elimination."""
        self._logger.warning(
            "Player eliminated",
            hand=hand_number,
            player=player_name,
            eliminated_by=eliminated_by,
            position=position,
        )

    def _get_eliminated_by_name(self, outcome: HandOutcome, game_record: GameRecord) -> str | None:
        """Determine who eliminated the players, if there's a single winner."""
        if len(outcome.winner_ids) != 1:
            return None

        eliminated_by_id = outcome.winner_ids[0]
        if eliminated_by_id in game_record.player_records:
            return game_record.player_records[eliminated_by_id].player_name
        return None

    def _get_starting_chips(self, player_id: str, hand: HandRecord) -> int:
        """Get starting chips for a player from hand record."""
        if player_id in hand.player_records:
            return hand.player_records[player_id].starting_chips.value
        return 0

    def _sort_eliminated_by_starting_chips(
        self, eliminated_players: list[PlayerOutcome], hand: HandRecord
    ) -> list[PlayerOutcome]:
        """Sort eliminated players by starting chips (descending)."""
        return sorted(
            eliminated_players,
            key=lambda po: self._get_starting_chips(po.player_id, hand),
            reverse=True,
        )

    def _assign_elimination_positions(
        self,
        sorted_eliminated: list[PlayerOutcome],
        active_count: int,
        hand: HandRecord,
    ) -> list[int]:
        """Assign positions to eliminated players with tiebreaker logic.

        Returns list of positions corresponding to sorted_eliminated order.
        """
        current_position = active_count - len(sorted_eliminated) + 1
        prev_stack: int | None = None
        prev_position: int = current_position
        positions: list[int] = []

        for po in sorted_eliminated:
            stack_value = self._get_starting_chips(po.player_id, hand)

            if prev_stack is not None and stack_value == prev_stack:
                position = prev_position
            else:
                position = current_position
                prev_position = position
                current_position += 1

            prev_stack = stack_value
            positions.append(position)

        return positions

    def log_hand_completed_with_eliminations(self, game_record: GameRecord) -> None:
        """Log hand completion with all related events (completion, standings, eliminations).

        Computes derived information (eliminated_by, position) from record objects
        and logs all hand completion events.

        Args:
            game_record: Game record containing completed hands.
        """
        if not game_record.completed_hands:
            return

        hand = game_record.completed_hands[-1]
        if hand.outcome is None:
            return

        outcome: HandOutcome = hand.outcome

        self.log_hand_completed(hand, outcome)
        self.log_player_standings(hand, outcome)

        eliminated_players: list[PlayerOutcome] = [
            po for po in outcome.player_outcomes if po.was_eliminated
        ]
        if not eliminated_players:
            return

        active_count: int = sum(1 for p in outcome.player_outcomes if not p.was_eliminated)

        eliminated_by_name: str | None = self._get_eliminated_by_name(outcome, game_record)
        sorted_eliminated: list[PlayerOutcome] = self._sort_eliminated_by_starting_chips(
            eliminated_players, hand
        )
        positions: list[int] = self._assign_elimination_positions(
            sorted_eliminated, active_count, hand
        )

        for po, position in zip(sorted_eliminated, positions, strict=False):
            self.log_player_eliminated(
                hand.hand_number,
                po.player_id,
                po.player_name,
                eliminated_by_name,
                position,
            )

    def log_game_ended(self, record: GameRecord, total_hands: int, total_actions: int) -> None:
        """Log tournament completion."""
        winner_name = None
        if record.player_records:
            active_players = [
                player_record
                for player_record in record.player_records.values()
                if not player_record.is_eliminated
            ]
            if len(active_players) == 1:
                winner_name = active_players[0].player_name

        self._logger.info(
            "Tournament completed",
            game_id=record.game_id,
            winner=winner_name,
            hands_played=total_hands,
            total_actions=total_actions,
        )
