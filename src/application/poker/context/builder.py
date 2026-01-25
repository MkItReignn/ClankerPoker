"""Poker context builder - builds decision context from game state."""

from src.application.poker.context.types import (
    ActingPlayerState,
    CurrentHandRecord,
    HandState,
    OpponentCurrentState,
    PokerDecisionContext,
    PreviousHandsRecord,
)
from src.application.poker.records.context_serializer import (
    RecordToLlmContextSerializer,
)
from src.application.poker.records.models import GameRecord
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.position import TablePositionMapping
from src.domain.rules.betting_calculator import BettingCalculator
from src.domain.rules.position_manager import PositionManager


class PokerContextBuilder:
    """Builds PokerDecisionContext from game state.

    Implements the ContextBuilder protocol for poker.
    """

    def __init__(self, player_names: dict[str, str] | None = None) -> None:
        """Initialize the context builder.

        Args:
            player_names: Optional mapping of player_id to display name.
        """
        self._player_names: dict[str, str] = player_names or {}

    def _get_player_name(self, player: Player) -> str:
        """Get display name for a player."""
        if player.id in self._player_names:
            return self._player_names[player.id]
        # Fall back to bot_id or player_id
        return str(player.bot_id) if player.bot_id else player.id

    def build_context(
        self,
        state: Game,
        player_id: str,
        record: GameRecord | None = None,
    ) -> PokerDecisionContext:
        """Build a decision context for the specified player.

        Raises:
            ValueError: If player not found or has no hole cards.
        """
        player: Player | None = state.players.get_by_id(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found in game")
        if player.hole_cards is None:
            raise ValueError(f"Player {player_id} has no hole cards")

        # Calculate positions
        active_players: list[Player] = state.get_active_players()
        position_mapping: TablePositionMapping = (
            PositionManager.resolve_positions_for_hand(
                all_players=active_players,
                previous_button_seat=state.button_seat,
                advance_button=False,  # Just reading current state
            )
        )

        # Calculate call amount
        players_in_hand: list[Player] = state.players_in_hand()
        max_invested: ChipAmount = (
            BettingCalculator.get_max_invested_this_hand(players_in_hand)
        )
        call_amount: ChipAmount = BettingCalculator.calculate_call_amount(
            max_invested,
            player.total_invested_this_hand,
        )

        # Build hand state
        hand_state = HandState(
            phase=state.current_phase,
            community_cards=tuple(state.community_cards),
            pot_total=state.pot,
            hand_number=state.hand_state.hand_number,
            current_bet=call_amount,
            blinds=state.current_blind_level,
        )

        # Build acting player state
        acting_player: ActingPlayerState = ActingPlayerState(
            player_id=player_id,
            player_name=self._get_player_name(player),
            hole_cards=player.hole_cards,
            position=position_mapping.get_position_for_seat(player.seat),
            stack=player.remaining_chips,
        )

        # Build opponent info
        opponents: list[OpponentCurrentState] = []
        for p in state.players:
            if p.id == player_id:
                continue
            if p.participation_status == HandParticipationStatus.ELIMINATED:
                continue

            opponents.append(
                OpponentCurrentState(
                    player_id=p.id,
                    name=self._get_player_name(p),
                    seat=p.seat,
                    position=position_mapping.get_position_for_seat(p.seat),
                    stack=p.remaining_chips,
                    is_folded=p.participation_status
                    == HandParticipationStatus.FOLDED,
                    is_all_in=p.is_all_in(),
                    invested_this_hand=p.total_invested_this_hand,
                )
            )

        # Serialize record context
        actions_this_hand = ""
        previous_hands_summary = ""
        if record is not None:
            if record.current_hand is not None:
                actions_this_hand = RecordToLlmContextSerializer.serialize_current_hand_actions(
                    record.current_hand,
                    state.current_phase.value,
                )
            previous_hands_summary = (
                RecordToLlmContextSerializer.serialize_recent_records(
                    record,
                    viewer_id=player_id,
                    max_hands=5,
                )
            )

        # Build record wrappers
        current_hand_record: CurrentHandRecord = CurrentHandRecord(
            text=actions_this_hand
        )
        previous_hands_record: PreviousHandsRecord = PreviousHandsRecord(
            text=previous_hands_summary
        )

        return PokerDecisionContext(
            acting_player=acting_player,
            hand_state=hand_state,
            opponents=tuple(opponents),
            current_hand_record=current_hand_record,
            previous_hands_record=previous_hands_record,
        )
