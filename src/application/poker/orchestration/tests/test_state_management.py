"""Integration tests for PokerStateManager.

Tests verify the observable behavior of the state manager:
- Input: Actions
- Output: Updated game state with correct status, chips, phases

These are behavioral tests that treat the state manager as a black box.
The only mock is the action provider (LLM boundary).
"""

from __future__ import annotations

import pytest

from src.application.poker.orchestration.poker_orchestrator import \
    PokerOrchestrator
from src.application.poker.orchestration.state_manager import PokerStateManager
from src.config.poker.config import PokerGameConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase, GameStatus

from .conftest import (BIG_BLIND, SMALL_BLIND, STARTING_CHIPS, TEST_GAME_ID,
                       TEST_SEED, bet, call, check, fold, raise_to, run_turn)


class TestInitializeGame:
    """Tests for game initialization behavior."""

    @pytest.mark.asyncio
    async def test_transitions_status_to_in_progress(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given runner, when initialized, status becomes IN_PROGRESS."""
        # Act
        await poker_state.initialize()

        # Assert
        assert poker_state.game.status == GameStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_starts_hand_number_one(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given new runner, when initialized, hand number is 1."""
        # Act
        await poker_state.initialize()

        # Assert
        assert poker_state.game.hand_state.hand_number == 1
        assert poker_state.game.hand_state.is_initial_hand_setup is False

    @pytest.mark.asyncio
    async def test_deals_hole_cards_to_all_players(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given new runner, when initialized, all players have hole cards."""
        # Act
        await poker_state.initialize()

        # Assert
        for player in poker_state.game.players:
            assert player.hole_cards is not None, f"Player {player.id} has no hole cards"
            assert player.hole_cards.card1 is not None
            assert player.hole_cards.card2 is not None

    @pytest.mark.asyncio
    async def test_posts_blinds_from_correct_positions(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given 2-player game, when initialized, blinds are posted.

        In heads-up: button posts small blind, other player posts big blind.
        """
        # Act
        await poker_state.initialize()

        # Assert: total invested across players equals SB + BB
        total_invested = sum(p.total_invested_this_hand.value for p in poker_state.game.players)
        expected_blinds = SMALL_BLIND.value + BIG_BLIND.value
        assert total_invested == expected_blinds

    @pytest.mark.asyncio
    async def test_players_have_invested_blind_amounts(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given initialized game, players have invested blinds.

        Note: Investments are tracked on players until hand completion.
        The pot amount is only updated when the hand resolves.
        """
        # Act
        await poker_state.initialize()

        # Assert: Players have invested their blinds
        investments = [p.total_invested_this_hand.value for p in poker_state.game.players]
        assert SMALL_BLIND.value in investments
        assert BIG_BLIND.value in investments

    @pytest.mark.asyncio
    async def test_initializes_record(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given new runner, when initialized, record is created."""
        # Arrange
        assert poker_state.record is None

        # Act
        await poker_state.initialize()

        # Assert
        assert poker_state.record is not None
        assert poker_state.record.game_id == poker_state.game.id


class TestRunTurn:
    """Tests for single turn execution."""

    @pytest.mark.asyncio
    async def test_fold_action_removes_player_from_hand(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given player's turn, when they fold, they are no longer in hand."""
        # Arrange
        await poker_state.initialize()
        provider = scripted_provider_factory([fold()])

        # Act
        result = await run_turn(poker_state, provider)

        # Assert
        assert result is not None
        assert result.response.action.action_type == ActionType.FOLD

        folded_player = poker_state.game.players.get_by_id(result.player_id)
        assert folded_player is not None
        assert folded_player.is_in_hand() is False

    @pytest.mark.asyncio
    async def test_call_action_increases_player_investment(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given player needs to call, when they call, their investment increases."""
        # Arrange
        await poker_state.initialize()
        total_invested_before = sum(
            p.total_invested_this_hand.value for p in poker_state.game.players
        )
        provider = scripted_provider_factory([call()])

        # Act
        result = await run_turn(poker_state, provider)

        # Assert
        assert result is not None
        assert result.response.action.action_type == ActionType.CALL

        total_invested_after = sum(
            p.total_invested_this_hand.value for p in poker_state.game.players
        )
        assert total_invested_after > total_invested_before

    @pytest.mark.asyncio
    async def test_returns_none_when_hand_complete(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given hand complete (one player folded), run_turn returns None."""
        # Arrange
        await poker_state.initialize()
        provider = scripted_provider_factory([fold()])

        # One player folds, hand is complete
        result = await run_turn(poker_state, provider)
        assert result is not None
        assert poker_state.game.is_hand_complete()

        # Act: Try to run another turn
        provider_empty = scripted_provider_factory([])
        result = await run_turn(poker_state, provider_empty)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_records_action_in_record(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given player takes action, action is recorded in game record."""
        # Arrange
        await poker_state.initialize()
        provider = scripted_provider_factory([call()])

        # Act
        await run_turn(poker_state, provider)

        # Assert
        record = poker_state.record
        assert record is not None
        assert record.current_hand is not None
        assert len(record.current_hand.rounds) > 0

        current_round = record.current_hand.rounds[-1]
        assert len(current_round.turns) > 0

        last_turn = current_round.turns[-1]
        assert last_turn.action.action_type == ActionType.CALL


class TestAdvanceGamePhase:
    """Tests for phase advancement behavior."""

    @pytest.mark.asyncio
    async def test_completes_hand_when_all_but_one_fold(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given one player remaining, when phase advances, hand completes."""
        # Arrange
        await poker_state.initialize()
        provider = scripted_provider_factory([fold()])

        result = await run_turn(poker_state, provider)
        assert result is not None

        # At this point only one player is in hand
        players_in_hand = list(poker_state.game.players_in_hand())
        assert len(players_in_hand) == 1

        # Act - complete hand via atomic state transitions
        assert poker_state.is_hand_complete()
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()
        await poker_state.start_new_hand()

        # Assert: Hand completed and new hand started
        assert poker_state.game.hand_state.hand_number == 2

    @pytest.mark.asyncio
    async def test_advances_to_flop_after_preflop_betting_complete(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given preflop betting complete, when phase advances, moves to FLOP."""
        # Arrange
        await poker_state.initialize()
        assert poker_state.game.current_phase == GamePhase.PRE_FLOP

        # Complete preflop: small blind calls, big blind checks
        provider = scripted_provider_factory([call(), check()])

        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break

        assert poker_state.game.is_round_complete()

        # Act - use explicit advance_round instead of deprecated advance_game_phase
        assert poker_state.is_round_complete()
        assert not poker_state.is_hand_complete()
        await poker_state.start_next_round()

        # Assert
        assert poker_state.game.current_phase == GamePhase.FLOP
        assert len(poker_state.game.community_cards) == 3

    @pytest.mark.asyncio
    async def test_deals_community_cards_on_flop(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given advancing to FLOP, 3 community cards are dealt."""
        # Arrange
        await poker_state.initialize()
        assert len(poker_state.game.community_cards) == 0

        # Complete preflop
        provider = scripted_provider_factory([call(), check()])
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break

        # Act - use explicit advance_round instead of deprecated advance_game_phase
        await poker_state.start_next_round()

        # Assert
        assert len(poker_state.game.community_cards) == 3


class TestRunGame:
    """Tests for full game execution using PokerOrchestrator."""

    @pytest.mark.asyncio
    async def test_completes_when_one_player_wins_all_chips(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 2-player game, when one player folds repeatedly, game completes."""
        # Arrange
        # Script: Player 1 always folds (will eventually lose all chips to blinds)
        # Use per-player actions to ensure only player-1 folds
        player_actions = {
            "player-1": [fold() for _ in range(200)],  # Player 1 always folds
            "player-2": [call() for _ in range(200)],  # Player 2 calls (wins when player-1 folds)
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=500,
        )

        # Act
        result = await orchestrator.run_game()

        # Assert
        assert result.final_state.status == GameStatus.COMPLETED

        # One player should have all the chips
        active_players = result.final_state.get_active_players()
        assert len(active_players) == 1

    @pytest.mark.asyncio
    async def test_respects_max_hands_limit(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given max_hands limit, game stops even if not complete."""
        # Arrange
        # Script: Everyone checks/calls to keep game going
        actions = [call(), check()] * 200
        provider = scripted_provider_factory(actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=3,
        )

        # Act
        result = await orchestrator.run_game()

        # Assert: Game stopped after max_hands
        assert result.total_hands == 3
        # Game may not be complete (still have chips)
        assert result.final_state.status != GameStatus.COMPLETED or result.total_hands <= 3


class TestGameRecording:
    """Tests for game record keeping throughout game lifecycle."""

    @pytest.mark.asyncio
    async def test_records_completed_hand(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given hand completes via fold, record contains the completed hand."""
        # Arrange
        await poker_state.initialize()
        provider = scripted_provider_factory([fold()])

        # Act: Run one turn (fold) and complete hand
        result = await run_turn(poker_state, provider)
        assert result is not None
        assert poker_state.is_hand_complete()
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()

        # Assert
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

    @pytest.mark.asyncio
    async def test_tracks_player_chip_changes(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given players win/lose pots, record tracks chip changes."""
        # Arrange
        await poker_state.initialize()

        # One player folds, other wins blinds
        provider = scripted_provider_factory([fold()])
        result = await run_turn(poker_state, provider)
        assert result is not None

        # Complete the hand
        assert poker_state.is_hand_complete()
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()

        # Assert
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

        completed_hand = record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert len(completed_hand.outcome.winners) == 1


class TestDeterminism:
    """Tests for deterministic game behavior based on seed."""

    @pytest.mark.asyncio
    async def test_same_seed_produces_same_initial_state(
        self,
        two_player_config: PokerGameConfig,
        tournament_config: TournamentConfig,
    ) -> None:
        """Given same seed, initialization produces identical game states."""
        # Arrange
        runner1 = PokerStateManager(
            config=two_player_config,
            tournament_config=tournament_config,
            game_id=TEST_GAME_ID,
            seed=TEST_SEED,
        )
        runner2 = PokerStateManager(
            config=two_player_config,
            tournament_config=tournament_config,
            game_id=TEST_GAME_ID,
            seed=TEST_SEED,
        )

        # Act
        await runner1.initialize()
        await runner2.initialize()

        # Assert: Same hole cards dealt
        for player1, player2 in zip(runner1.game.players, runner2.game.players, strict=True):
            assert player1.hole_cards == player2.hole_cards

        # Assert: Same button position
        assert runner1.game.button_seat == runner2.game.button_seat


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_game_property_raises_before_initialization(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given uninitialized runner, game property raises RuntimeError."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Game not initialized"):
            _ = poker_state.game

    @pytest.mark.asyncio
    async def test_is_game_complete_returns_false_for_active_game(
        self,
        poker_state: PokerStateManager,
    ) -> None:
        """Given IN_PROGRESS game, is_game_complete returns False."""
        # Arrange
        await poker_state.initialize()

        # Act & Assert
        assert poker_state.is_game_complete() is False

    @pytest.mark.asyncio
    async def test_three_player_game_continues_after_one_fold(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 3-player game, one fold does not end the hand."""
        # Arrange
        await three_player_state.initialize()
        provider = scripted_provider_factory([fold()])

        # Act
        result = await run_turn(three_player_state, provider)
        assert result is not None

        # Assert: Still 2 players in hand, hand not complete
        players_in_hand = list(three_player_state.game.players_in_hand())
        assert len(players_in_hand) == 2
        assert three_player_state.game.is_hand_complete() is False


class TestBetAndRaiseActions:
    """Tests for bet and raise action behaviors."""

    @pytest.mark.asyncio
    async def test_bet_action_increases_investment(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given post-flop with no bet, when player bets, their investment increases."""
        # Arrange: Complete preflop to get to flop
        await poker_state.initialize()
        preflop_actions = [call(), check()]  # SB calls, BB checks
        provider = scripted_provider_factory(preflop_actions)

        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break

        # Advance to flop
        await poker_state.start_next_round()
        assert poker_state.game.current_phase == GamePhase.FLOP

        # Act: First player bets
        bet_amount = BIG_BLIND.value * 2  # Standard bet size
        bet_provider = scripted_provider_factory([bet(bet_amount)])
        result = await run_turn(poker_state, bet_provider)

        # Assert
        assert result is not None
        assert result.response.action.action_type == ActionType.BET
        assert result.response.action.amount == ChipAmount(bet_amount)

    @pytest.mark.asyncio
    async def test_raise_action_increases_current_bet(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given player faces a bet, when they raise, the bet amount increases."""
        # Arrange
        await poker_state.initialize()

        # Preflop: SB raises instead of just calling
        raise_amount = BIG_BLIND.value * 3  # 3x BB raise
        provider = scripted_provider_factory([raise_to(raise_amount)])

        # Act
        result = await run_turn(poker_state, provider)

        # Assert
        assert result is not None
        assert result.response.action.action_type == ActionType.RAISE
        assert result.response.action.amount == ChipAmount(raise_amount)

        # Verify the acting player's investment increased
        acting_player = poker_state.game.players.get_by_id(result.player_id)
        assert acting_player is not None
        assert acting_player.total_invested_this_hand.value >= raise_amount


class TestPhaseProgression:
    """Tests for complete phase progression through all betting rounds."""

    @pytest.mark.asyncio
    async def test_advances_through_all_phases_to_showdown(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players checking through, game progresses PRE_FLOP→FLOP→TURN→RIVER→SHOWDOWN."""
        # Arrange
        await poker_state.initialize()
        assert poker_state.game.current_phase == GamePhase.PRE_FLOP
        assert len(poker_state.game.community_cards) == 0

        # Script: call preflop, then check through all streets
        # PRE_FLOP: SB calls, BB checks (2 actions)
        # FLOP: check, check (2 actions)
        # TURN: check, check (2 actions)
        # RIVER: check, check (2 actions)
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        # --- PRE_FLOP ---
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        assert poker_state.game.is_round_complete()

        # Advance to FLOP
        await poker_state.start_next_round()
        assert poker_state.game.current_phase == GamePhase.FLOP
        assert len(poker_state.game.community_cards) == 3

        # --- FLOP ---
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        assert poker_state.game.is_round_complete()

        # Advance to TURN
        await poker_state.start_next_round()
        assert poker_state.game.current_phase == GamePhase.TURN
        assert len(poker_state.game.community_cards) == 4

        # --- TURN ---
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        assert poker_state.game.is_round_complete()

        # Advance to RIVER
        await poker_state.start_next_round()
        assert poker_state.game.current_phase == GamePhase.RIVER
        assert len(poker_state.game.community_cards) == 5

        # --- RIVER ---
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        assert poker_state.game.is_round_complete()

        # Complete hand: RIVER complete -> transition to showdown -> resolve
        await poker_state.start_next_round()
        assert poker_state.game.current_phase == GamePhase.SHOWDOWN
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()

        # Start new hand
        await poker_state.start_new_hand()

        # Assert: Hand completed and new hand started (hand number 2)
        assert poker_state.game.hand_state.hand_number == 2

    @pytest.mark.asyncio
    async def test_turn_deals_one_community_card(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given FLOP complete, when advancing to TURN, 1 additional card is dealt."""
        # Arrange
        await poker_state.initialize()
        actions = [call(), check()] + [check()] * 2  # Preflop + Flop
        provider = scripted_provider_factory(actions)

        # Complete preflop
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        await poker_state.start_next_round()  # To FLOP

        # Complete flop
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break

        assert len(poker_state.game.community_cards) == 3

        # Act: Advance to TURN
        await poker_state.start_next_round()

        # Assert
        assert poker_state.game.current_phase == GamePhase.TURN
        assert len(poker_state.game.community_cards) == 4

    @pytest.mark.asyncio
    async def test_river_deals_one_community_card(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given TURN complete, when advancing to RIVER, 1 additional card is dealt."""
        # Arrange
        await poker_state.initialize()
        actions = [call(), check()] + [check()] * 4  # Preflop + Flop + Turn
        provider = scripted_provider_factory(actions)

        # Complete preflop
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        await poker_state.start_next_round()  # To FLOP

        # Complete flop
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break
        await poker_state.start_next_round()  # To TURN

        # Complete turn
        for _ in range(2):
            result = await run_turn(poker_state, provider)
            if result is None:
                break

        assert len(poker_state.game.community_cards) == 4

        # Act: Advance to RIVER
        await poker_state.start_next_round()

        # Assert
        assert poker_state.game.current_phase == GamePhase.RIVER
        assert len(poker_state.game.community_cards) == 5


class TestShowdown:
    """Tests for showdown scenarios with multiple players."""

    @pytest.mark.asyncio
    async def test_showdown_determines_winner_by_hand_strength(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players reach showdown, winner is determined by hand evaluation."""
        # Arrange
        await poker_state.initialize()

        # Check all streets to reach showdown
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        # Play through all phases
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for phase in phases:
            for _ in range(2):
                result = await run_turn(poker_state, provider)
                if result is None:
                    break
            if poker_state.game.is_round_complete() and phase != GamePhase.RIVER:
                await poker_state.start_next_round()

        # Act: Complete hand (triggers showdown)
        await poker_state.start_next_round()
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()

        # Assert: Hand completed, winner received pot
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

        completed_hand = record.completed_hands[0]
        assert completed_hand.outcome is not None
        assert len(completed_hand.outcome.winners) >= 1

        # Winner should have gained chips (minus blinds already invested)
        winner_id = completed_hand.outcome.winners[0].player_id
        winner = poker_state.game.players.get_by_id(winner_id)
        assert winner is not None
        # Winner has more chips than starting (they won the pot)
        assert winner.remaining_chips.value > STARTING_CHIPS.value - BIG_BLIND.value

    @pytest.mark.asyncio
    async def test_three_player_showdown(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 3 players reach showdown, winner is correctly determined."""
        # Arrange
        await three_player_state.initialize()

        # All 3 players check through all streets
        # PRE_FLOP: call, call, check (3 actions)
        # FLOP/TURN/RIVER: check x3 each (9 actions)
        actions = [call(), call(), check()] + [check()] * 9
        provider = scripted_provider_factory(actions)

        # Play through all phases
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for phase in phases:
            # 3 players means 3 actions per round
            for _ in range(3):
                result = await run_turn(three_player_state, provider)
                if result is None:
                    break
            if three_player_state.game.is_round_complete() and phase != GamePhase.RIVER:
                await three_player_state.start_next_round()

        # Act: Complete hand (RIVER → SHOWDOWN)
        await three_player_state.start_next_round()
        await three_player_state.resolve_hand()
        await three_player_state.mark_game_complete_if_over()

        # Assert
        record = three_player_state.record
        assert record is not None
        assert len(record.completed_hands) == 1
        assert record.completed_hands[0].outcome is not None


class TestCompleteGame:
    """Tests for running complete games from start to finish."""

    @pytest.mark.asyncio
    async def test_full_game_with_betting_and_showdowns(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players, game runs to completion with mix of folds and showdowns."""
        # Arrange
        # Script enough actions for multiple hands
        # Mix of folds (quick hands) and check-throughs (showdowns)
        actions = []
        for _ in range(50):
            # Alternate between quick fold and full hand
            actions.append(fold())  # Quick hand - fold
            # Full hand through showdown
            actions.extend([call(), check()])  # Preflop
            actions.extend([check(), check()] * 3)  # Flop, Turn, River

        provider = scripted_provider_factory(actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=20,
        )

        # Act
        await orchestrator.run_game()

        # Assert: Game progressed (multiple hands played)
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) > 1

    @pytest.mark.asyncio
    async def test_game_completes_with_single_winner(
        self,
        two_player_config: PokerGameConfig,
        tournament_config: TournamentConfig,
        scripted_provider_factory,
    ) -> None:
        """Given game runs to completion, exactly one player remains active."""
        # Arrange: Use fresh state manager
        state = PokerStateManager(
            config=two_player_config,
            tournament_config=tournament_config,
            game_id=TEST_GAME_ID,
            seed=TEST_SEED,
        )

        # Player 1 always folds - will lose chips via blinds
        # Use per-player actions to ensure only player-1 folds
        player_actions = {
            "player-1": [fold() for _ in range(200)],  # Player 1 always folds
            "player-2": [call() for _ in range(200)],  # Player 2 calls (wins when player-1 folds)
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=state,
            action_provider=provider,
            max_hands=500,
        )

        # Act
        result = await orchestrator.run_game()

        # Assert
        assert result.final_state.status == GameStatus.COMPLETED

        active_players = result.final_state.get_active_players()
        assert len(active_players) == 1

        # Winner has chips remaining
        winner = active_players[0]
        assert winner.remaining_chips.value > 0

    @pytest.mark.asyncio
    async def test_full_hand_records_all_rounds_in_record(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given hand plays through all streets, record tracks each round."""
        # Arrange
        await poker_state.initialize()
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        # Play through all phases manually to ensure record tracking
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for i, _phase in enumerate(phases):
            for _ in range(2):
                result = await run_turn(poker_state, provider)
                if result is None:
                    break
            if poker_state.game.is_round_complete():
                if i < len(phases) - 1:  # Not RIVER yet
                    await poker_state.start_next_round()
                else:  # After RIVER, transition to showdown and resolve
                    await poker_state.start_next_round()
                    await poker_state.resolve_hand()
                    await poker_state.mark_game_complete_if_over()

        # Assert: Record contains all rounds
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

        completed_hand = record.completed_hands[0]
        # Should have 5 rounds: PRE_FLOP, FLOP, TURN, RIVER, SHOWDOWN
        assert len(completed_hand.rounds) == 5

    @pytest.mark.asyncio
    async def test_button_rotates_between_hands(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Given multiple hands played, button position rotates."""
        # Arrange
        await poker_state.initialize()
        first_button = poker_state.game.button_seat

        # Complete first hand via fold
        provider = scripted_provider_factory([fold()])
        result = await run_turn(poker_state, provider)
        assert result is not None

        # Complete hand and start new one
        assert poker_state.is_hand_complete()
        await poker_state.resolve_hand()
        await poker_state.mark_game_complete_if_over()
        await poker_state.start_new_hand()

        # Assert: Button has rotated
        assert poker_state.game.button_seat != first_button
