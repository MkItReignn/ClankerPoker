from src.application.poker.records.models import (
    GameRecord,
    HandRecord,
    RoundRecord,
    TurnRecord,
)
from src.application.poker.state_observers.details import (
    EliminatedInfo,
    HandOutcomeDetails,
)
from src.domain.models.player import HandParticipationStatus
from src.logger.factories import get_generic_logger


class RecordLogger:
    def __init__(self) -> None:
        self._logger = get_generic_logger(__name__.removeprefix("src."))

    def log_game_started(self, record: GameRecord) -> None:
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
        sorted_records = sorted(
            hand.player_records.values(), key=lambda s: s.seat.value
        )
        players_info = [
            {
                "name": player_record.player_name,
                "model": player_record.model_id.value,
                "seat": player_record.seat.value,
                "position": (
                    player_record.position.value
                    if player_record.position
                    else None
                ),
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

    def log_round_advanced(
        self, hand: HandRecord, round_record: RoundRecord
    ) -> None:
        phase = round_record.phase.value.upper()
        board = " ".join(str(card) for card in round_record.community_cards)

        self._logger.info(
            f"*** {phase} ***",
            hand=hand.hand_number,
            board=board,
        )

    def log_betting_round_ended(
        self, hand: HandRecord, round_record: RoundRecord
    ) -> None:
        action_counts: dict[str, int] = {}
        for turn in round_record.turns:
            action_type = turn.action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        folded = [
            ps.player_name
            for ps in round_record.player_records.values()
            if ps.participation_status == HandParticipationStatus.FOLDED
        ]
        all_in = [
            ps.player_name
            for ps in round_record.player_records.values()
            if ps.is_all_in
        ]

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

    def log_hand_completed(
        self, hand: HandRecord, outcome: HandOutcomeDetails
    ) -> None:
        winners_info: list[str] = []
        player_map = {po.player_id: po for po in outcome.player_outcomes}
        for winner in outcome.winners:
            if winner.player_id in player_map:
                po = player_map[winner.player_id]
                winners_info.append(f"{po.player_name}: {po.chips_won.value}")

        eliminated_ids = {e.player_id for e in outcome.eliminated}
        players_remaining = sum(
            1
            for po in outcome.player_outcomes
            if po.player_id not in eliminated_ids
        )

        showdown_info: list[dict[str, str]] = []
        was_showdown = outcome.showdown is not None
        if was_showdown and outcome.showdown:
            for sr in outcome.showdown:
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
            was_showdown=was_showdown,
            showdown=showdown_info if showdown_info else None,
            players_remaining=players_remaining,
        )

    def log_player_standings(
        self, hand: HandRecord, outcome: HandOutcomeDetails
    ) -> None:
        eliminated_ids = {e.player_id for e in outcome.eliminated}
        standings_info = [
            f"{po.player_name}: {po.final_stack.value} "
            f"({'eliminated' if po.player_id in eliminated_ids else 'active'})"
            for po in sorted(
                outcome.player_outcomes,
                key=lambda p: p.final_stack.value,
                reverse=True,
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
        self._logger.warning(
            "Player eliminated",
            hand=hand_number,
            player=player_name,
            eliminated_by=eliminated_by,
            position=position,
        )

    def _get_eliminated_by_name(
        self, outcome: HandOutcomeDetails, game_record: GameRecord
    ) -> str | None:
        if len(outcome.winners) != 1:
            return None

        eliminated_by_id = outcome.winners[0].player_id
        if eliminated_by_id in game_record.player_records:
            return game_record.player_records[eliminated_by_id].player_name
        return None

    def _get_starting_chips(self, player_id: str, hand: HandRecord) -> int:
        if player_id in hand.player_records:
            return hand.player_records[player_id].starting_chips.value
        return 0

    def _sort_eliminated_by_starting_chips(
        self, eliminated_players: list[EliminatedInfo], hand: HandRecord
    ) -> list[EliminatedInfo]:
        return sorted(
            eliminated_players,
            key=lambda ei: self._get_starting_chips(ei.player_id, hand),
            reverse=True,
        )

    def _assign_elimination_positions(
        self,
        sorted_eliminated: list[EliminatedInfo],
        active_count: int,
        hand: HandRecord,
    ) -> list[int]:
        current_position = active_count - len(sorted_eliminated) + 1
        prev_stack: int | None = None
        prev_position: int = current_position
        positions: list[int] = []

        for ei in sorted_eliminated:
            stack_value = self._get_starting_chips(ei.player_id, hand)

            if prev_stack is not None and stack_value == prev_stack:
                position = prev_position
            else:
                position = current_position
                prev_position = position
                current_position += 1

            prev_stack = stack_value
            positions.append(position)

        return positions

    def log_hand_completed_with_eliminations(
        self, game_record: GameRecord, outcome: HandOutcomeDetails
    ) -> None:
        if not game_record.completed_hands:
            return

        hand = game_record.completed_hands[-1]

        self.log_hand_completed(hand, outcome)
        self.log_player_standings(hand, outcome)

        eliminated_players: list[EliminatedInfo] = list(outcome.eliminated)
        if not eliminated_players:
            return

        eliminated_ids = {e.player_id for e in outcome.eliminated}
        active_count: int = sum(
            1
            for p in outcome.player_outcomes
            if p.player_id not in eliminated_ids
        )

        eliminated_by_name: str | None = self._get_eliminated_by_name(
            outcome, game_record
        )
        sorted_eliminated: list[EliminatedInfo] = (
            self._sort_eliminated_by_starting_chips(eliminated_players, hand)
        )
        positions: list[int] = self._assign_elimination_positions(
            sorted_eliminated, active_count, hand
        )

        for ei, position in zip(sorted_eliminated, positions, strict=False):
            self.log_player_eliminated(
                hand.hand_number,
                ei.player_id,
                ei.player_name,
                eliminated_by_name,
                position,
            )

    def log_game_ended(
        self, record: GameRecord, total_hands: int, total_actions: int
    ) -> None:
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
