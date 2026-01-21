"""Game state recorder for capturing game state snapshots."""

from __future__ import annotations

from datetime import datetime

from src.application.poker.records.record_logger import RecordLogger
from src.application.poker.records.models import (
    ActionRecord,
    GameMetadata,
    GameRecord,
    HandLevelPlayerRecord,
    HandOutcome,
    PlayerConfig,
    PlayerOutcome,
    RoundLevelPlayerRecord,
    RoundRecord,
    ShowdownResult,
    TurnLevelPlayerRecord,
    TurnRecord,
)
from src.application.protocols.player import ActionResponse
from src.config.poker.config import PokerPlayerConfig
from src.domain.models.actions import Action
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase
from src.domain.models.llm_model import LlmModel
from src.domain.models.narration import Narration
from src.domain.models.player import HandParticipationStatus, Player
from src.domain.models.position import PositionName, TablePositionMapping
from src.domain.rules.betting_calculator import BettingCalculator
from src.domain.rules.hand_evaluator import HandEvaluator
from src.domain.rules.position_manager import PositionManager
from src.logger.factories import get_generic_logger


class Recorder:
    """Records game state snapshots at each level of the game hierarchy.

    Responsible for capturing state snapshots and building record objects:
    - Game level: tournament metadata and player registration
    - Hand level: player positions, hole cards, blinds
    - Round level: player states at start of each betting round
    - Turn level: individual actions with pot changes
    """

    def __init__(self, player_configs: dict[str, PokerPlayerConfig]) -> None:
        """Initialize the recorder.

        Args:
            player_configs: Dictionary mapping player_id to player configuration.
        """
        self._player_configs = player_configs
        self._record: GameRecord | None = None
        self._logger = get_generic_logger(__name__.removeprefix("src."))
        self._record_logger = RecordLogger()

    @property
    def record(self) -> GameRecord | None:
        """Get the current game record."""
        return self._record

    def _get_player_name(self, player_id: str) -> str:
        if player_id not in self._player_configs:
            raise KeyError(f"Player ID '{player_id}' not found in player_configs")
        return self._player_configs[player_id].name

    def _get_player_model_id(self, player_id: str) -> LlmModel:
        if player_id not in self._player_configs:
            raise KeyError(f"Player ID '{player_id}' not found in player_configs")
        return self._player_configs[player_id].model_id

    # =========================================================================
    # Game Lifecycle
    # =========================================================================

    def initialize_record(
        self,
        state: Game,
        metadata: GameMetadata,
    ) -> None:
        """Initialize game record with metadata and register all players.

        Args:
            state: Current game state with players.
            metadata: Tournament configuration metadata.
        """
        self._record = GameRecord(state.id, metadata)

        # Register all players with initial state and LLM config
        for player in state.players:
            player_name = self._get_player_name(player.id)
            poker_config = self._player_configs[player.id]

            # Convert PokerPlayerConfig to PlayerConfig DTO (personality/prompts only)
            player_config = PlayerConfig(
                personality=poker_config.personality,
                addon_prompt=poker_config.addon_prompt,
            )

            self._record.register_player(
                player_id=player.id,
                name=player_name,
                initial_chips=player.remaining_chips,
                seat=player.seat,
                model_id=poker_config.model_id,
                player_config=player_config,
            )

        self._record_logger.log_game_started(self._record)

    def complete_game(self, completed_at: datetime) -> None:
        """Mark the game as complete.

        Args:
            completed_at: Timestamp when game completed.
        """
        if self._record is not None:
            self._record.metadata.completed_at = completed_at

    # =========================================================================
    # Hand Lifecycle
    # =========================================================================

    def record_hand_start(self, state: Game) -> None:
        """Record the start of a new hand.

        Creates HandLevelPlayerRecord for each active player and starts
        the hand in record.

        Args:
            state: Game state after hand initialization.
        """
        if self._record is None:
            return

        # Capture hand-level player records
        hand_player_records: dict[str, HandLevelPlayerRecord] = {}
        position_mapping: TablePositionMapping = PositionManager.resolve_positions_for_hand(
            all_players=list(state.players),
            previous_button_seat=state.button_seat,
            advance_button=False,  # Reading current state for record
        )

        for player in state.players:
            if player.participation_status != HandParticipationStatus.ELIMINATED:
                # Get position name for this player
                position_name: PositionName | None = position_mapping.get_position_for_seat(
                    player.seat
                )
                player_name: str = self._get_player_name(player.id)

                hand_player_records[player.id] = HandLevelPlayerRecord(
                    player_id=player.id,
                    player_name=player_name,
                    seat=player.seat,
                    chips=player.remaining_chips,
                    model_id=self._get_player_model_id(player.id),
                    hole_cards=player.hole_cards,
                    position=position_name,
                    starting_chips=player.remaining_chips,
                    total_invested_in_hand=ChipAmount(0),  # Hand just started
                )

        # Start the hand
        self._record.start_hand(
            hand_number=state.hand_state.hand_number,
            button_seat=state.button_seat,
            blinds=state.current_blind_level,
            player_records=hand_player_records,
        )

        if self._record.current_hand is not None:
            self._record_logger.log_hand_started(self._record.current_hand)

    def record_hand_complete(self, state: Game) -> None:
        """Record the completion of a hand.

        Builds the hand outcome and completes the hand in record.

        Args:
            state: Game state after hand completion.
        """
        if self._record is None or self._record.current_hand is None:
            return

        outcome: HandOutcome = self._build_hand_outcome(state)
        self._record.complete_hand(outcome)

        self._record_logger.log_hand_completed_with_eliminations(self._record)

    # =========================================================================
    # Round Lifecycle
    # =========================================================================

    def record_round_start(self, state: Game) -> None:
        """Record the start of a betting round.

        Creates RoundLevelPlayerRecord for each player and starts
        the round in record.

        Args:
            state: Current game state at round start.
        """
        if self._record is None or self._record.current_hand is None:
            return

        # Capture round-level player records
        round_player_records: dict[str, RoundLevelPlayerRecord] = {}

        for player in state.players:
            # Determine participation status
            if player.participation_status == HandParticipationStatus.ELIMINATED:
                participation_status = HandParticipationStatus.ELIMINATED
            elif player.participation_status == HandParticipationStatus.FOLDED:
                participation_status = HandParticipationStatus.FOLDED
            else:
                participation_status = HandParticipationStatus.IN_HAND

            # Calculate total invested in hand so far
            total_invested = ChipAmount(0)
            if player.stack_at_hand_start is not None:
                total_invested = ChipAmount(
                    player.stack_at_hand_start.value - player.remaining_chips.value
                )

            # Calculate total invested in this round
            total_invested_in_round = ChipAmount(0)
            if len(self._record.current_hand.rounds) > 0:
                # Get the last completed round (current round hasn't been added yet)
                previous_round = self._record.current_hand.rounds[-1]

                if player.id in previous_round.player_records:
                    previous_total = previous_round.player_records[player.id].total_invested_in_hand
                    total_invested_in_round = ChipAmount(
                        total_invested.value - previous_total.value
                    )
                else:
                    # First round (preflop) - total_invested is the round investment
                    total_invested_in_round = total_invested
            else:
                # First round (preflop) - total_invested is the round investment
                total_invested_in_round = total_invested

            player_name = self._get_player_name(player.id)
            round_player_records[player.id] = RoundLevelPlayerRecord(
                player_id=player.id,
                player_name=player_name,
                seat=player.seat,
                chips=player.remaining_chips,
                model_id=self._get_player_model_id(player.id),
                chips_at_round_start=player.remaining_chips,
                total_invested_in_hand=total_invested,
                total_invested_in_round=total_invested_in_round,
                participation_status=participation_status,
                is_all_in=player.is_all_in(),
            )

        # Get community cards (may be empty for preflop, or 5 cards if dealt upfront)
        community_cards = tuple(state.community_cards) if state.community_cards else ()

        # Start the round
        round_record = self._record.current_hand.start_round(
            phase=state.current_phase,
            community_cards=community_cards,
            player_records=round_player_records,
        )

        if round_record.phase != GamePhase.PRE_FLOP:
            self._record_logger.log_round_advanced(self._record.current_hand, round_record)

    def record_round_complete(self) -> None:
        """Record the completion of a betting round."""
        if self._record is None or self._record.current_hand is None:
            return

        current_round = self._record.current_hand.current_round()
        if current_round is not None and not current_round.is_complete:
            current_round.complete()
            self._record_logger.log_betting_round_ended(
                self._record.current_hand, current_round
            )

    # =========================================================================
    # Action Recording
    # =========================================================================

    def record_action(
        self,
        state_before: Game,
        state_after: Game,
        player_id: str,
        response: ActionResponse[Action, Narration],
    ) -> None:
        """Record an action taken by a player.

        Creates TurnLevelPlayerRecord (before action), ActionRecord,
        and TurnRecord with pot changes.

        Args:
            state_before: Game state before the action.
            state_after: Game state after the action.
            player_id: ID of player who acted.
            response: The action response containing action, narration, reasoning.
        """
        if self._record is None or self._record.current_hand is None:
            return

        current_round: RoundRecord | None = self._record.current_hand.current_round()
        if current_round is None:
            return

        player: Player | None = state_before.players.get_by_id(player_id)
        if player is None:
            return

        player_name = self._get_player_name(player_id)

        # Extract action from response
        action = response.action

        # Capture state BEFORE action
        chips_before: int = player.remaining_chips.value
        pot_before: int = state_before.pot.value
        current_bet_before: int = BettingCalculator.get_max_invested_this_hand(
            state_before.players_in_hand()
        ).value
        invested_before: int = (
            player.stack_at_hand_start.value - player.remaining_chips.value
            if player.stack_at_hand_start is not None
            else 0
        )

        # Capture state AFTER action
        pot_after: int = state_after.pot.value
        current_bet_after: int = BettingCalculator.get_max_invested_this_hand(
            state_after.players_in_hand()
        ).value

        # Create turn-level player record (BEFORE action)
        turn_player_record: TurnLevelPlayerRecord = TurnLevelPlayerRecord(
            player_id=player_id,
            player_name=player_name,
            seat=player.seat,
            chips=ChipAmount(chips_before),
            model_id=self._get_player_model_id(player_id),
            total_invested_before_action=ChipAmount(invested_before),
            can_raise=player.can_raise,
        )

        # Create action record
        action_record: ActionRecord = ActionRecord(
            player_id=player_id,
            player_name=player_name,
            phase=state_before.current_phase,
            action_type=action.action_type,
            amount=action.amount,
            timestamp=datetime.now(),
        )

        # Create turn record
        turn_number: int = len(current_round.turns) + 1
        turn_record: TurnRecord = TurnRecord(
            turn_number=turn_number,
            player_record=turn_player_record,
            action=action_record,
            timestamp=datetime.now(),
            pot_before=ChipAmount(pot_before),
            pot_after=ChipAmount(pot_after),
            current_bet_before=ChipAmount(current_bet_before),
            current_bet_after=ChipAmount(current_bet_after),
            narration=response.narration,
        )

        # Add turn to current round
        current_round.add_turn(turn_record)

        self._record_logger.log_action_taken(
            turn_record, self._record.current_hand.hand_number
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _build_hand_outcome(self, state: Game) -> HandOutcome:
        """Build hand outcome from game state.

        Args:
            state: Game state after hand completion.

        Returns:
            HandOutcome with winners, showdown results, and player outcomes.
        """
        # Get winners from results
        winner_ids: list[str] = []
        total_pot: ChipAmount = state.pot

        if state.outcome is not None:
            winner_ids = [w[0] for w in state.outcome.winners]
            # Sum up all winnings for pot total if available
            if state.outcome.winners:
                total_pot = sum((w[1] for w in state.outcome.winners), start=ChipAmount(0))

        # Determine if showdown
        players_in_hand = state.players_in_hand()
        was_showdown = len(players_in_hand) > 1 and state.current_phase == GamePhase.SHOWDOWN

        # Build showdown results
        showdown_results: list[ShowdownResult] = []
        if was_showdown:
            community_cards = state.community_cards
            if len(community_cards) != 5:
                raise ValueError(
                    f"Showdown requires exactly 5 community cards, got {len(community_cards)}"
                )
            for player in players_in_hand:
                if player.hole_cards is not None:
                    hand_evaluation = HandEvaluator.evaluate_hand_strength(
                        player.hole_cards, community_cards
                    )
                    showdown_results.append(
                        ShowdownResult(
                            player_id=player.id,
                            player_name=self._get_player_name(player.id),
                            hole_cards=player.hole_cards,
                            hand_evaluation=hand_evaluation,
                        )
                    )

        # Build player outcomes
        player_outcomes: list[PlayerOutcome] = []
        for player in state.players:
            if player.participation_status == HandParticipationStatus.ELIMINATED:
                continue

            chips_won = ChipAmount(0)
            chips_lost = ChipAmount(0)

            if player.id in winner_ids and state.outcome is not None:
                for w_id, w_amount in state.outcome.winners:
                    if w_id == player.id:
                        chips_won = w_amount

            # Check if player was eliminated this hand
            was_eliminated_this_hand = (
                player.remaining_chips.value == 0
                and player.participation_status != HandParticipationStatus.FOLDED
            )
            player_outcomes.append(
                PlayerOutcome(
                    player_id=player.id,
                    player_name=self._get_player_name(player.id),
                    chips_won=chips_won,
                    chips_lost=chips_lost,
                    final_stack=player.remaining_chips,
                    was_eliminated=was_eliminated_this_hand,
                )
            )

        return HandOutcome(
            winner_ids=tuple(winner_ids) if winner_ids else ("unknown",),
            pot_amount=ChipAmount(max(total_pot.value, 1)),  # Ensure positive
            was_showdown=was_showdown,
            showdown_results=tuple(showdown_results),
            player_outcomes=tuple(player_outcomes),
        )
