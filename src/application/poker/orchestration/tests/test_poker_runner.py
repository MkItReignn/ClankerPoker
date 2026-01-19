"""Integration tests for PokerGameRunner.

Tests verify the observable behavior of the game runner:
- Input: Game state + actions
- Output: Updated game state with correct status, chips, phases

These are behavioral tests that treat the runner as a black box.
The only mock is the action provider (LLM boundary).
"""

from __future__ import annotations

import pytest

from src.application.poker.orchestration.runner import PokerGameRunner
from src.config.poker.config import PokerGameConfig
from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import Game, GamePhase, GameStatus

from .conftest import (BIG_BLIND, SMALL_BLIND, STARTING_CHIPS,
                       bet, call, check, fold,
                       raise_to)


class TestInitializeGame:
    """Tests for game initialization behavior."""

    def test_transitions_status_from_waiting_to_in_progress(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given WAITING game, when initialized, status becomes IN_PROGRESS."""
        # Arrange
        assert two_player_waiting_game.status == GameStatus.WAITING

        # Act
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Assert
        assert initialized.status == GameStatus.IN_PROGRESS

    def test_starts_hand_number_one(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given new game, when initialized, hand number is 1."""
        # Act
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Assert
        assert initialized.hand_state.hand_number == 1
        assert initialized.hand_state.is_initial_hand_setup is False

    def test_deals_hole_cards_to_all_players(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given new game, when initialized, all players have hole cards."""
        # Act
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Assert
        for player in initialized.players:
            assert player.hole_cards is not None, f"Player {player.id} has no hole cards"
            assert player.hole_cards.card1 is not None
            assert player.hole_cards.card2 is not None

    def test_posts_blinds_from_correct_positions(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given 2-player game, when initialized, blinds are posted.

        In heads-up: button posts small blind, other player posts big blind.
        """
        # Arrange
        initial_chips = two_player_waiting_game.players.get_by_id("player-1")
        assert initial_chips is not None
        assert initial_chips.remaining_chips == STARTING_CHIPS

        # Act
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Assert: total invested across players equals SB + BB
        total_invested = sum(p.total_invested_this_hand.value for p in initialized.players)
        expected_blinds = SMALL_BLIND.value + BIG_BLIND.value
        assert total_invested == expected_blinds

    def test_players_have_invested_blind_amounts(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given initialized game, players have invested blinds.

        Note: Investments are tracked on players until hand completion.
        The pot amount is only updated when the hand resolves.
        """
        # Act
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Assert: Players have invested their blinds
        investments = [p.total_invested_this_hand.value for p in initialized.players]
        assert SMALL_BLIND.value in investments
        assert BIG_BLIND.value in investments

    def test_initializes_history(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given new game, when initialized, history is created."""
        # Arrange
        assert poker_runner.history is None

        # Act
        poker_runner.initialize_game(two_player_waiting_game)

        # Assert
        assert poker_runner.history is not None
        assert poker_runner.history.game_id == two_player_waiting_game.id


class TestRunTurn:
    """Tests for single turn execution."""

    @pytest.mark.asyncio
    async def test_fold_action_removes_player_from_hand(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given player's turn, when they fold, they are no longer in hand."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([fold()])

        # Act
        result = await poker_runner.run_turn(initialized, provider)

        # Assert
        assert result is not None
        assert result.action.action_type == ActionType.FOLD

        folded_player = result.state.players.get_by_id(result.player_id)
        assert folded_player is not None
        assert folded_player.is_in_hand() is False

    @pytest.mark.asyncio
    async def test_call_action_increases_player_investment(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given player needs to call, when they call, their investment increases."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        total_invested_before = sum(p.total_invested_this_hand.value for p in initialized.players)
        provider = scripted_provider_factory([call()])

        # Act
        result = await poker_runner.run_turn(initialized, provider)

        # Assert
        assert result is not None
        assert result.action.action_type == ActionType.CALL

        total_invested_after = sum(p.total_invested_this_hand.value for p in result.state.players)
        assert total_invested_after > total_invested_before

    @pytest.mark.asyncio
    async def test_returns_none_when_hand_complete(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given hand complete (one player folded), run_turn returns None."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([fold()])

        # One player folds, hand is complete
        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None
        assert result.state.is_hand_complete()

        # Act: Try to run another turn
        provider_empty = scripted_provider_factory([])
        result = await poker_runner.run_turn(result.state, provider_empty)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_records_action_in_history(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given player takes action, action is recorded in history."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([call()])

        # Act
        await poker_runner.run_turn(initialized, provider)

        # Assert
        history = poker_runner.history
        assert history is not None
        assert history.current_hand is not None
        assert len(history.current_hand.rounds) > 0

        current_round = history.current_hand.rounds[-1]
        assert len(current_round.turns) > 0

        last_turn = current_round.turns[-1]
        assert last_turn.action.action_type == ActionType.CALL


class TestAdvanceGamePhase:
    """Tests for phase advancement behavior."""

    @pytest.mark.asyncio
    async def test_completes_hand_when_all_but_one_fold(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given one player remaining, when phase advances, hand completes."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([fold()])

        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None

        # At this point only one player is in hand
        players_in_hand = list(result.state.players_in_hand())
        assert len(players_in_hand) == 1

        # Act
        advanced = poker_runner.advance_game_phase(result.state)

        # Assert: Hand completed and new hand started
        assert advanced.hand_state.hand_number == 2

    @pytest.mark.asyncio
    async def test_advances_to_flop_after_preflop_betting_complete(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given preflop betting complete, when phase advances, moves to FLOP."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        assert initialized.current_phase == GamePhase.PRE_FLOP

        # Complete preflop: small blind calls, big blind checks
        provider = scripted_provider_factory([call(), check()])

        state = initialized
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state

        assert state.is_round_complete()

        # Act
        advanced = poker_runner.advance_game_phase(state)

        # Assert
        assert advanced.current_phase == GamePhase.FLOP
        assert len(advanced.community_cards) == 3

    @pytest.mark.asyncio
    async def test_deals_community_cards_on_flop(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given advancing to FLOP, 3 community cards are dealt."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        assert len(initialized.community_cards) == 0

        # Complete preflop
        provider = scripted_provider_factory([call(), check()])
        state = initialized
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state

        # Act
        flop_state = poker_runner.advance_game_phase(state)

        # Assert
        assert len(flop_state.community_cards) == 3


class TestRunGame:
    """Tests for full game execution."""

    @pytest.mark.asyncio
    async def test_completes_when_one_player_wins_all_chips(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 2-player game, when one player folds repeatedly, game completes."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Script: Player 1 always folds (will eventually lose all chips to blinds)
        # We need enough folds to deplete one player's stack through blinds
        # Each hand costs SB (10) + BB (20) = 30 chips in rotation
        # 1000 chips / ~15 chips per hand average = ~66 hands needed
        # But player folding loses their blind each hand, so faster

        # Simpler approach: just fold many times
        folds = [fold() for _ in range(200)]  # Enough for many hands
        provider = scripted_provider_factory(folds)

        # Act
        final_state = await poker_runner.run_game(
            initialized,
            provider,
            max_turns=500,
        )

        # Assert
        assert final_state.status == GameStatus.COMPLETED

        # One player should have all the chips
        active_players = final_state.get_active_players()
        assert len(active_players) == 1

    @pytest.mark.asyncio
    async def test_respects_max_turns_limit(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given max_turns limit, game stops even if not complete."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Script: For preflop, need call then check. After that, all checks work.
        # Using only checks keeps the game going across all phases.
        actions = [call(), check()] + [check()] * 100
        provider = scripted_provider_factory(actions)

        # Act
        final_state = await poker_runner.run_game(
            initialized,
            provider,
            max_turns=5,
        )

        # Assert: Game stopped but may not be complete
        assert provider.actions_taken <= 5

    @pytest.mark.asyncio
    async def test_invokes_on_turn_callback_for_each_action(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given on_turn callback, it is called after each player action."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([call(), check()])

        turn_results: list = []

        def on_turn(result):
            turn_results.append(result)

        # Act
        await poker_runner.run_game(
            initialized,
            provider,
            on_turn=on_turn,
            max_turns=2,
        )

        # Assert
        assert len(turn_results) == 2
        assert turn_results[0].action.action_type == ActionType.CALL
        assert turn_results[1].action.action_type == ActionType.CHECK


class TestHistoryRecording:
    """Tests for game history recording throughout game lifecycle."""

    @pytest.mark.asyncio
    async def test_records_completed_hand(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given hand completes via fold, history contains the completed hand."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        provider = scripted_provider_factory([fold()])

        # Act: Run one turn (fold) and advance to complete hand
        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None
        poker_runner.advance_game_phase(result.state)

        # Assert
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) == 1

    @pytest.mark.asyncio
    async def test_tracks_player_chip_changes(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given players win/lose pots, history tracks chip changes."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # One player folds, other wins blinds
        provider = scripted_provider_factory([fold()])
        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None

        # Advance to complete the hand
        advanced = poker_runner.advance_game_phase(result.state)

        # Assert
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) == 1

        completed_hand = history.completed_hands[0]
        assert completed_hand.outcome is not None
        assert len(completed_hand.outcome.winner_ids) == 1


class TestDeterminism:
    """Tests for deterministic game behavior based on seed."""

    def test_same_seed_produces_same_initial_state(
        self,
        poker_game_config: PokerGameConfig,
        two_player_waiting_game: Game,
    ) -> None:
        """Given same seed, initialization produces identical game states."""
        # Arrange
        runner1 = PokerGameRunner(config=poker_game_config)
        runner2 = PokerGameRunner(config=poker_game_config)

        # Act
        game1 = runner1.initialize_game(two_player_waiting_game)
        game2 = runner2.initialize_game(two_player_waiting_game)

        # Assert: Same hole cards dealt
        for player1, player2 in zip(game1.players, game2.players, strict=True):
            assert player1.hole_cards == player2.hole_cards

        # Assert: Same button position
        assert game1.button_seat == game2.button_seat


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_get_current_player_returns_none_for_waiting_game(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given WAITING game, get_current_player_id returns None."""
        # Act
        player_id = poker_runner.get_current_player_id(two_player_waiting_game)

        # Assert
        assert player_id is None

    def test_is_game_over_returns_false_for_active_game(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
    ) -> None:
        """Given IN_PROGRESS game, is_game_over returns False."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Act & Assert
        assert poker_runner.is_game_over(initialized) is False

    @pytest.mark.asyncio
    async def test_three_player_game_continues_after_one_fold(
        self,
        poker_runner: PokerGameRunner,
        three_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 3-player game, one fold does not end the hand."""
        # Arrange
        initialized = poker_runner.initialize_game(three_player_waiting_game)
        provider = scripted_provider_factory([fold()])

        # Act
        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None

        # Assert: Still 2 players in hand, hand not complete
        players_in_hand = list(result.state.players_in_hand())
        assert len(players_in_hand) == 2
        assert result.state.is_hand_complete() is False


class TestBetAndRaiseActions:
    """Tests for bet and raise action behaviors."""

    @pytest.mark.asyncio
    async def test_bet_action_increases_investment(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given post-flop with no bet, when player bets, their investment increases."""
        # Arrange: Complete preflop to get to flop
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        preflop_actions = [call(), check()]  # SB calls, BB checks
        provider = scripted_provider_factory(preflop_actions)

        state = initialized
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state

        # Advance to flop
        state = poker_runner.advance_game_phase(state)
        assert state.current_phase == GamePhase.FLOP

        # Act: First player bets
        bet_amount = BIG_BLIND.value * 2  # Standard bet size
        bet_provider = scripted_provider_factory([bet(bet_amount)])
        result = await poker_runner.run_turn(state, bet_provider)

        # Assert
        assert result is not None
        assert result.action.action_type == ActionType.BET
        assert result.action.amount == ChipAmount(bet_amount)

    @pytest.mark.asyncio
    async def test_raise_action_increases_current_bet(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given player faces a bet, when they raise, the bet amount increases."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Preflop: SB raises instead of just calling
        raise_amount = BIG_BLIND.value * 3  # 3x BB raise
        provider = scripted_provider_factory([raise_to(raise_amount)])

        # Act
        result = await poker_runner.run_turn(initialized, provider)

        # Assert
        assert result is not None
        assert result.action.action_type == ActionType.RAISE
        assert result.action.amount == ChipAmount(raise_amount)

        # Verify the acting player's investment increased
        acting_player = result.state.players.get_by_id(result.player_id)
        assert acting_player is not None
        assert acting_player.total_invested_this_hand.value >= raise_amount


class TestPhaseProgression:
    """Tests for complete phase progression through all betting rounds."""

    @pytest.mark.asyncio
    async def test_advances_through_all_phases_to_showdown(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players checking through, game progresses PRE_FLOP→FLOP→TURN→RIVER→SHOWDOWN."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        assert initialized.current_phase == GamePhase.PRE_FLOP
        assert len(initialized.community_cards) == 0

        # Script: call preflop, then check through all streets
        # PRE_FLOP: SB calls, BB checks (2 actions)
        # FLOP: check, check (2 actions)
        # TURN: check, check (2 actions)
        # RIVER: check, check (2 actions)
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        state = initialized

        # --- PRE_FLOP ---
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        assert state.is_round_complete()

        # Advance to FLOP
        state = poker_runner.advance_game_phase(state)
        assert state.current_phase == GamePhase.FLOP
        assert len(state.community_cards) == 3

        # --- FLOP ---
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        assert state.is_round_complete()

        # Advance to TURN
        state = poker_runner.advance_game_phase(state)
        assert state.current_phase == GamePhase.TURN
        assert len(state.community_cards) == 4

        # --- TURN ---
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        assert state.is_round_complete()

        # Advance to RIVER
        state = poker_runner.advance_game_phase(state)
        assert state.current_phase == GamePhase.RIVER
        assert len(state.community_cards) == 5

        # --- RIVER ---
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        assert state.is_round_complete()

        # Advance to SHOWDOWN (hand completion)
        state = poker_runner.advance_game_phase(state)

        # Assert: Hand completed and new hand started (hand number 2)
        assert state.hand_state.hand_number == 2

    @pytest.mark.asyncio
    async def test_turn_deals_one_community_card(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given FLOP complete, when advancing to TURN, 1 additional card is dealt."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        actions = [call(), check()] + [check()] * 2  # Preflop + Flop
        provider = scripted_provider_factory(actions)

        state = initialized

        # Complete preflop
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        state = poker_runner.advance_game_phase(state)  # To FLOP

        # Complete flop
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state

        assert len(state.community_cards) == 3

        # Act: Advance to TURN
        state = poker_runner.advance_game_phase(state)

        # Assert
        assert state.current_phase == GamePhase.TURN
        assert len(state.community_cards) == 4

    @pytest.mark.asyncio
    async def test_river_deals_one_community_card(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given TURN complete, when advancing to RIVER, 1 additional card is dealt."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        actions = [call(), check()] + [check()] * 4  # Preflop + Flop + Turn
        provider = scripted_provider_factory(actions)

        state = initialized

        # Complete preflop
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        state = poker_runner.advance_game_phase(state)  # To FLOP

        # Complete flop
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state
        state = poker_runner.advance_game_phase(state)  # To TURN

        # Complete turn
        for _ in range(2):
            result = await poker_runner.run_turn(state, provider)
            if result is None:
                break
            state = result.state

        assert len(state.community_cards) == 4

        # Act: Advance to RIVER
        state = poker_runner.advance_game_phase(state)

        # Assert
        assert state.current_phase == GamePhase.RIVER
        assert len(state.community_cards) == 5


class TestShowdown:
    """Tests for showdown scenarios with multiple players."""

    @pytest.mark.asyncio
    async def test_showdown_determines_winner_by_hand_strength(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players reach showdown, winner is determined by hand evaluation."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

        # Check all streets to reach showdown
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        state = initialized
        total_invested_before = sum(p.total_invested_this_hand.value for p in state.players)

        # Play through all phases
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for phase in phases:
            for _ in range(2):
                result = await poker_runner.run_turn(state, provider)
                if result is None:
                    break
                state = result.state
            if state.is_round_complete() and phase != GamePhase.RIVER:
                state = poker_runner.advance_game_phase(state)

        # Act: Complete hand (triggers showdown)
        final_state = poker_runner.advance_game_phase(state)

        # Assert: Hand completed, winner received pot
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) == 1

        completed_hand = history.completed_hands[0]
        assert completed_hand.outcome is not None
        assert len(completed_hand.outcome.winner_ids) >= 1

        # Winner should have gained chips (minus blinds already invested)
        winner_id = completed_hand.outcome.winner_ids[0]
        winner = final_state.players.get_by_id(winner_id)
        assert winner is not None
        # Winner has more chips than starting (they won the pot)
        assert winner.remaining_chips.value > STARTING_CHIPS.value - BIG_BLIND.value

    @pytest.mark.asyncio
    async def test_three_player_showdown(
        self,
        poker_runner: PokerGameRunner,
        three_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 3 players reach showdown, winner is correctly determined."""
        # Arrange
        initialized = poker_runner.initialize_game(three_player_waiting_game)

        # All 3 players check through all streets
        # PRE_FLOP: call, call, check (3 actions)
        # FLOP/TURN/RIVER: check x3 each (9 actions)
        actions = [call(), call(), check()] + [check()] * 9
        provider = scripted_provider_factory(actions)

        state = initialized

        # Play through all phases
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for phase in phases:
            # 3 players means 3 actions per round
            for _ in range(3):
                result = await poker_runner.run_turn(state, provider)
                if result is None:
                    break
                state = result.state
            if state.is_round_complete() and phase != GamePhase.RIVER:
                state = poker_runner.advance_game_phase(state)

        # Act: Complete hand
        final_state = poker_runner.advance_game_phase(state)

        # Assert
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) == 1
        assert history.completed_hands[0].outcome is not None


class TestCompleteGame:
    """Tests for running complete games from start to finish."""

    @pytest.mark.asyncio
    async def test_full_game_with_betting_and_showdowns(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given 2 players, game runs to completion with mix of folds and showdowns."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)

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

        # Act
        final_state = await poker_runner.run_game(
            initialized,
            provider,
            max_turns=200,
        )

        # Assert: Game progressed (multiple hands played)
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) > 1

    @pytest.mark.asyncio
    async def test_game_completes_with_single_winner(
        self,
        poker_game_config: PokerGameConfig,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given game runs to completion, exactly one player remains active."""
        # Arrange: Use fresh runner
        runner = PokerGameRunner(config=poker_game_config)
        initialized = runner.initialize_game(two_player_waiting_game)

        # Player 1 always folds - will lose chips via blinds
        folds = [fold() for _ in range(200)]
        provider = scripted_provider_factory(folds)

        # Act
        final_state = await runner.run_game(
            initialized,
            provider,
            max_turns=500,
        )

        # Assert
        assert final_state.status == GameStatus.COMPLETED

        active_players = final_state.get_active_players()
        assert len(active_players) == 1

        # Winner has chips remaining
        winner = active_players[0]
        assert winner.remaining_chips.value > 0

    @pytest.mark.asyncio
    async def test_full_hand_records_all_rounds_in_history(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given hand plays through all streets, history records each round."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        actions = [call(), check()] + [check()] * 6
        provider = scripted_provider_factory(actions)

        state = initialized

        # Play through all phases manually to ensure history recording
        for phase in [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]:
            for _ in range(2):
                result = await poker_runner.run_turn(state, provider)
                if result is None:
                    break
                state = result.state
            if state.is_round_complete():
                state = poker_runner.advance_game_phase(state)

        # Assert: History contains all rounds
        history = poker_runner.history
        assert history is not None
        assert len(history.completed_hands) == 1

        completed_hand = history.completed_hands[0]
        # Should have 4 rounds: PRE_FLOP, FLOP, TURN, RIVER
        assert len(completed_hand.rounds) == 4

    @pytest.mark.asyncio
    async def test_button_rotates_between_hands(
        self,
        poker_runner: PokerGameRunner,
        two_player_waiting_game: Game,
        scripted_provider_factory,
    ) -> None:
        """Given multiple hands played, button position rotates."""
        # Arrange
        initialized = poker_runner.initialize_game(two_player_waiting_game)
        first_button = initialized.button_seat

        # Complete first hand via fold
        provider = scripted_provider_factory([fold()])
        result = await poker_runner.run_turn(initialized, provider)
        assert result is not None

        # Advance to complete hand and start new one
        state_after_hand1 = poker_runner.advance_game_phase(result.state)

        # Assert: Button has rotated
        assert state_after_hand1.button_seat != first_button
