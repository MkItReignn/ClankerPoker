"""Integration tests for PokerOrchestrator.

Tests verify the observable behavior of the orchestrator:
- Input: Game configuration and action provider
- Output: Complete game results with correct status, chips, winners

These are behavioral tests that treat the orchestrator as a black box.
The only mock is the action provider (LLM boundary).
"""

import pytest

from src.application.poker.orchestration.poker_orchestrator import (
    PokerOrchestrator,
)
from src.application.poker.orchestration.state_manager import PokerStateManager
from src.config.poker.config import PokerGameConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GameStatus, HandPhase

from .conftest import (
    BIG_BLIND,
    SMALL_BLIND,
    STARTING_CHIPS,
    TEST_GAME_ID,
    TEST_SEED,
    all_in,
    bet,
    call,
    check,
    fold,
    raise_to,
    run_turn,
)


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
            "player-2": [
                call() for _ in range(200)
            ],  # Player 2 calls (wins when player-1 folds)
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
        assert (
            result.final_state.status != GameStatus.COMPLETED
            or result.total_hands <= 3
        )


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
            "player-2": [
                call() for _ in range(200)
            ],  # Player 2 calls (wins when player-1 folds)
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


class TestAllInRunout:
    """Tests for all-in run-out scenarios where no more betting is possible.

    These tests verify the fix for the edge case where one player is all-in
    and another player has called but still has chips remaining. In this case,
    no more meaningful betting can occur, so the game should skip to showdown.

    In heads-up: Button/SB (player-2) acts first preflop with 990 chips (1000-10 SB).
    BB (player-1) has 980 chips (1000-20 BB).
    """

    @pytest.mark.asyncio
    async def test_one_player_allin_other_calls_skips_to_showdown(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """When one player is all-in and another calls, remaining streets are dealt automatically."""
        # Heads-up: Button/SB (player-2) acts first, goes all-in with remaining 990 chips
        # BB (player-1) calls with their remaining 980 chips (also all-in)
        player_actions = {
            "player-2": [all_in(990)],
            "player-1": [call()],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # Verify only 2 actions were taken - no prompts for flop/turn/river betting
        assert provider.actions_taken == 2

        # Check record for completed hand reaching showdown
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1
        completed_hand = record.completed_hands[0]
        assert completed_hand.outcome is not None

    @pytest.mark.asyncio
    async def test_one_player_allin_other_calls_no_betting_prompts_after(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """After all-in is called, no additional betting prompts should occur."""
        # Button/SB goes all-in, BB calls - no more actions should be requested
        player_actions = {
            "player-2": [all_in(990)],
            "player-1": [call()],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # Verify only 2 actions consumed (the all-in and call)
        # If the bug existed, more actions would be requested for flop/turn/river
        assert provider.actions_taken == 2

    @pytest.mark.asyncio
    async def test_three_player_one_allin_one_calls_one_folds(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """With 3 players: one folds, one all-in, one calls - should run out without extra prompts.

        3-player positions: Button (player-2), SB (player-3), BB (player-1).
        Preflop action order: Button acts first (UTG in 3-way), then SB, then BB.
        """
        # Button folds, SB goes all-in (has 990), BB calls (all-in for 980)
        player_actions = {
            "player-2": [fold()],
            "player-3": [all_in(990)],
            "player-1": [call()],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=three_player_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # Should only take 3 actions - no prompts for post-flop betting
        assert provider.actions_taken == 3

        # Check record for completed hand
        record = three_player_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

    @pytest.mark.asyncio
    async def test_allin_on_flop_skips_remaining_streets(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """When all-in occurs on flop, turn and river are dealt without betting.

        Preflop: Button/SB calls (10 more to match BB), BB checks.
        Both now have invested 20, remaining chips: 980 each.
        Flop: BB acts first post-flop, goes all-in with 980.
        """
        player_actions = {
            "player-2": [call(), call()],
            "player-1": [check(), all_in(980)],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # 4 actions: call, check (preflop), all-in, call (flop) - no turn/river prompts
        assert provider.actions_taken == 4

        # Check record for completed hand
        record = poker_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

    @pytest.mark.asyncio
    async def test_smaller_allin_covered_by_call_no_more_prompts(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """When short stack goes all-in and big stack calls, no more betting occurs.

        This is the KEY edge case: one player is all-in, other player has chips
        remaining after calling. The player with chips shouldn't be prompted
        for flop/turn/river actions since there's no one to bet against.

        Preflop: Button/SB raises to 200 (has 800 left), BB goes all-in for 980.
        Button/SB calls 780 more (total 990), has 10 chips remaining.
        BB is all-in with 1000 total, Button has 10 left.
        Only 1 player can act (Button) but the all-in player can't respond.
        """
        # Button raises, BB shoves all-in, Button calls (has chips left)
        player_actions = {
            "player-2": [raise_to(200), call()],
            "player-1": [all_in(980)],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # Should only take 3 actions, then run out to showdown
        assert provider.actions_taken == 3

    @pytest.mark.asyncio
    async def test_allin_on_turn_skips_river(
        self,
        poker_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """When all-in occurs on turn, river is dealt without betting.

        Heads-up post-flop order: BB (player-1) acts first, Button (player-2) second.
        Preflop: Button calls, BB checks.
        Flop: BB checks, Button checks.
        Turn: BB goes all-in, Button calls.
        """
        player_actions = {
            "player-2": [call(), check(), call()],
            "player-1": [check(), check(), all_in(980)],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=poker_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # 6 actions total: 2 preflop + 2 flop + 2 turn, no river prompts
        assert provider.actions_taken == 6

    @pytest.mark.asyncio
    async def test_three_player_sequential_allins_different_rounds(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """3 players with all-ins at different rounds eventually run out.

        3-player post-flop order: SB (player-3) acts first, then BB (player-1), then Button.
        Preflop: Button calls, SB calls, BB checks.
        Flop: SB checks, BB folds, Button all-in, SB calls.
        """
        player_actions = {
            "player-2": [call(), all_in(980)],
            "player-3": [call(), check(), call()],
            "player-1": [check(), fold()],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=three_player_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # 7 actions: 3 preflop + 4 flop (check, fold, all-in, call)
        # After this, only all-in players remain, turn/river dealt automatically
        assert provider.actions_taken == 7

    @pytest.mark.asyncio
    async def test_sequential_allins_across_multiple_rounds(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """3 players with progressive all-ins across flop and turn.

        Round 1 (Preflop): All check through to see flop.
        Round 2 (Flop): Player goes all-in, others call (still have chips).
        Round 3 (Turn): Another player goes all-in, remaining player calls.
        Then we move to showdown without river prompts.

        3-player order:
        - Preflop: Button (player-2), SB (player-3), BB (player-1)
        - Post-flop: SB (player-3), BB (player-1), Button (player-2)

        Since all start with same chips (1000), when SB goes all-in (980) on flop,
        BB and Button calling also go all-in. So we simulate the "one smaller all-in"
        by having SB bet (not all-in) on flop, then go all-in on turn.
        """
        # Preflop: Button calls, SB calls, BB checks (all at 20, 980 remaining)
        # Flop: SB bets 100, BB calls, Button calls (all at 120, 880 remaining)
        # Turn: SB goes all-in (880), BB calls (all-in), Button folds
        # Now SB and BB are all-in → river dealt automatically
        player_actions = {
            "player-2": [call(), call(), fold()],
            "player-3": [call(), bet(100), all_in(880)],
            "player-1": [check(), call(), call()],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=three_player_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # 9 actions: 3 preflop + 3 flop + 3 turn, no river prompts
        assert provider.actions_taken == 9

        # Check record for completed hand
        record = three_player_state.record
        assert record is not None
        assert len(record.completed_hands) == 1

    @pytest.mark.asyncio
    async def test_caller_with_chips_remaining_vs_allin_no_prompts_after(
        self,
        three_player_state: PokerStateManager,
        scripted_provider_factory,
    ) -> None:
        """Caller with remaining chips vs all-in: no betting prompts on later streets.

        This tests the exact scenario from the user's bug report:
        - One player goes all-in
        - Another player calls and still has chips remaining
        - Third player folds
        - No prompts should occur on flop/turn/river since the caller
          can't bet against anyone (opponent is all-in, third folded)

        3-player order:
        - Preflop: Button (player-2), SB (player-3), BB (player-1)
        - Post-flop: SB (player-3), BB (player-1), Button (player-2)

        Setup:
        - Button raises to 200 (has 800 remaining)
        - SB calls 200 (has 800 remaining)
        - BB goes all-in for 980 (their remaining chips)
        - Button folds
        - SB calls (needs 780 more, has 800, ends with 20 remaining)

        After preflop: SB has 20 chips remaining, BB is all-in, Button folded.
        On flop/turn/river, only SB can act but they don't owe anything.
        """
        player_actions = {
            "player-2": [raise_to(200), fold()],
            "player-3": [call(), call()],
            "player-1": [all_in(980)],
        }
        provider = scripted_provider_factory(player_actions)

        orchestrator = PokerOrchestrator(
            state=three_player_state,
            action_provider=provider,
            max_hands=1,
        )

        await orchestrator.run_game()

        # Should only take 5 actions (raise, call, all-in, fold, call)
        # No prompts for flop/turn/river since SB is the only one with chips
        # and BB (all-in) can't respond to any bets
        assert provider.actions_taken == 5

        # Check record for completed hand reaching showdown
        record = three_player_state.record
        assert record is not None
        assert len(record.completed_hands) == 1
