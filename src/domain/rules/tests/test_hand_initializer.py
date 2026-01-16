"""Behavioral tests for HandInitializer.

Tests verify hand initialization behavior according to poker rules:
- Dealing hole cards to active players
- Posting blinds (small and big blind)
- Advancing hand number
- Resetting players for new hand
- Setting up initial betting state
- Handling insufficient chips for blinds (all-in)
- Excluding eliminated players from new hands
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from src.config.tournament.config import (BlindScheduleConfig,
                                          BlindScheduleEntry)
from src.domain.models.blinds import BlindLevel
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import Game, GamePhase, HandState
from src.domain.models.player import (BettingRoundActionStatus,
                                      HandParticipationStatus, Player)
from src.domain.models.players import Players
from src.domain.models.seat import Seat
from src.domain.rules.hand_initializer import HandInitializer

STARTING_CHIPS = ChipAmount(1000)
SMALL_BLIND = ChipAmount(10)
BIG_BLIND = ChipAmount(20)


class TestHandInitializationBasics:
    """Basic hand initialization: cards dealt, blinds posted, state updated."""

    def test_deals_two_hole_cards_to_each_active_player(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
            ),
            sample_player_factory(
                player_id="p3",
                seat=Seat.SEAT_2,
                remaining_chips=STARTING_CHIPS,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        for player in new_game.players:
            assert player.hole_cards is not None
            assert len(player.hole_cards.cards) == 2

    def test_small_blind_posts_correct_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        sb_seat = new_game.button_seat  # Heads-up: button is SB
        sb_player = new_game.players.get_by_seat(sb_seat)
        assert sb_player is not None
        assert sb_player.total_invested_this_hand == SMALL_BLIND
        assert sb_player.remaining_chips == ChipAmount(STARTING_CHIPS.value - SMALL_BLIND.value)

    def test_big_blind_posts_correct_amount(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                player_id="p1",
                seat=Seat.SEAT_0,
                remaining_chips=STARTING_CHIPS,
            ),
            sample_player_factory(
                player_id="p2",
                seat=Seat.SEAT_1,
                remaining_chips=STARTING_CHIPS,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        # In heads-up, non-button player is BB
        bb_seat = Seat.SEAT_1
        bb_player = new_game.players.get_by_seat(bb_seat)
        assert bb_player is not None
        assert bb_player.total_invested_this_hand == BIG_BLIND
        assert bb_player.remaining_chips == ChipAmount(STARTING_CHIPS.value - BIG_BLIND.value)

    def test_advances_hand_number_after_first_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        game = replace(
            game,
            hand_state=HandState(
                hand_number=1,
                current_phase=GamePhase.PRE_FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.hand_state.hand_number == 2

    def test_first_hand_receives_hand_number_one(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        assert game.hand_state.is_initial_hand_setup is True
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.hand_state.hand_number == 1
        assert new_game.hand_state.is_initial_hand_setup is False

    def test_resets_phase_to_preflop(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.hand_state.current_phase == GamePhase.PRE_FLOP

    def test_clears_community_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.hand_state.community_cards == []


class TestPlayerResetBehavior:
    """Players are reset for new hand: investments cleared, status reset."""

    def test_resets_player_investments_from_previous_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(1000),  # Previous hand investment
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                STARTING_CHIPS,
                total_invested_this_hand=ChipAmount(2000),  # Previous hand investment
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        # After initialization, only blinds are invested
        sb_player = new_game.players.get_by_seat(Seat.SEAT_0)
        bb_player = new_game.players.get_by_seat(Seat.SEAT_1)
        assert sb_player is not None and bb_player is not None
        assert sb_player.total_invested_this_hand == SMALL_BLIND
        assert bb_player.total_invested_this_hand == BIG_BLIND

    def test_resets_player_participation_status_to_in_hand(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
                participation_status=HandParticipationStatus.FOLDED,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                STARTING_CHIPS,
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        for player in new_game.players:
            assert player.participation_status == HandParticipationStatus.IN_HAND


class TestBlindPostingEdgeCases:
    """Blind posting with insufficient chips: players go all-in."""

    def test_small_blind_with_insufficient_chips_goes_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        insufficient_chips = ChipAmount(5)  # Less than SB
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                insufficient_chips,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                STARTING_CHIPS,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        sb_player = new_game.players.get_by_seat(Seat.SEAT_0)
        assert sb_player is not None
        assert sb_player.total_invested_this_hand == insufficient_chips
        assert sb_player.remaining_chips == ChipAmount(0)
        assert sb_player.betting_status == BettingRoundActionStatus.ACTED  # All-in

    def test_big_blind_with_insufficient_chips_goes_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        insufficient_chips = ChipAmount(15)  # Less than BB
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                insufficient_chips,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        bb_player = new_game.players.get_by_seat(Seat.SEAT_1)
        assert bb_player is not None
        assert bb_player.total_invested_this_hand == insufficient_chips
        assert bb_player.remaining_chips == ChipAmount(0)
        assert bb_player.betting_status == BettingRoundActionStatus.ACTED  # All-in

    def test_player_with_exactly_blind_amount_goes_all_in(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        exact_bb_chips = BIG_BLIND
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                exact_bb_chips,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        bb_player = new_game.players.get_by_seat(Seat.SEAT_1)
        assert bb_player is not None
        assert bb_player.total_invested_this_hand == BIG_BLIND
        assert bb_player.remaining_chips == ChipAmount(0)
        assert bb_player.betting_status == BettingRoundActionStatus.ACTED  # All-in

    def test_non_all_in_blind_poster_needs_action(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        sb_player = new_game.players.get_by_seat(Seat.SEAT_0)
        assert sb_player is not None
        assert sb_player.betting_status == BettingRoundActionStatus.NEEDS_ACTION


class TestEliminatedPlayers:
    """Eliminated players do not receive cards or participate in new hands."""

    def test_eliminated_player_does_not_receive_hole_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p3",
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        eliminated_player = new_game.players.get_by_id("p3")
        assert eliminated_player is not None
        assert eliminated_player.hole_cards is None

    def test_only_active_players_receive_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory(
                "p1",
                Seat.SEAT_0,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                STARTING_CHIPS,
            ),
            sample_player_factory(
                "p3",
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                "p4",
                Seat.SEAT_3,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        players_with_cards = [p for p in new_game.players if p.hole_cards is not None]
        assert len(players_with_cards) == 2

    def test_eliminated_players_remain_eliminated(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory(
                "p3",
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        eliminated_player = new_game.players.get_by_id("p3")
        assert eliminated_player is not None
        assert eliminated_player.participation_status == HandParticipationStatus.ELIMINATED


class TestDeckConsumption:
    """Deck state is properly updated as cards are dealt."""

    def test_deck_consumes_correct_number_of_cards(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory("p3", Seat.SEAT_2, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)
        initial_cards_remaining = deck.cards_remaining()

        _, new_deck = HandInitializer.initialize(game, deck)

        # 3 active players * 2 cards each = 6 cards dealt
        assert new_deck.cards_remaining() == initial_cards_remaining - 6

    def test_deck_only_deals_to_active_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory(
                "p3",
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)
        initial_cards_remaining = deck.cards_remaining()

        _, new_deck = HandInitializer.initialize(game, deck)

        # Only 2 active players * 2 cards each = 4 cards dealt
        assert new_deck.cards_remaining() == initial_cards_remaining - 4


class TestBettingStateInitialization:
    """Betting state is correctly initialized for first action."""

    def test_sets_position_to_act_to_first_active_player_after_blinds(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory("p3", Seat.SEAT_2, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        # Position to act should be set (non-negative)
        assert new_game.betting_state.position_to_act >= 0

    def test_skips_all_in_players_for_first_to_act(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        # 3-player game: button at SEAT_0, SB at SEAT_1, BB at SEAT_2 (all-in)
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory("p3", Seat.SEAT_2, BIG_BLIND),  # Exactly BB, will be all-in
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        # Verify BB is all-in
        bb_player = new_game.players.get_by_seat(Seat.SEAT_2)
        assert bb_player is not None
        assert bb_player.remaining_chips == ChipAmount(0)
        assert bb_player.betting_status == BettingRoundActionStatus.ACTED

        # Position to act should not be the all-in BB
        assert new_game.betting_state.position_to_act != Seat.SEAT_2.value


class TestMinimumPlayerRequirement:
    """Hand initialization requires at least 2 active players."""

    def test_rejects_initialization_with_fewer_than_two_active_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory(
                "p2",
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        with pytest.raises(ValueError, match="need at least 2 players"):
            HandInitializer.initialize(game, deck)


class TestBlindSchedule:
    """Blind levels can increase based on hand number."""

    def test_uses_blind_schedule_when_provided(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        blind_schedule = BlindScheduleConfig(
            entries=(
                BlindScheduleEntry(
                    level=BlindLevel(small_blind=ChipAmount(10), big_blind=ChipAmount(20), level=1),
                    start_hand=1,
                    duration_hands=2,
                ),
                BlindScheduleEntry(
                    level=BlindLevel(small_blind=ChipAmount(25), big_blind=ChipAmount(50), level=2),
                    start_hand=3,
                    duration_hands=2,
                ),
            )
        )
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        game = replace(
            game,
            tournament_config=replace(game.tournament_config, blind_schedule=blind_schedule),
            hand_state=HandState(
                hand_number=2,  # Moving to hand 3, which should trigger level 2
                current_phase=GamePhase.PRE_FLOP,
                community_cards=[],
                is_initial_hand_setup=False,
            ),
        )
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.blind_state.current_blind_level.small_blind == ChipAmount(25)
        assert new_game.blind_state.current_blind_level.big_blind == ChipAmount(50)
        assert new_game.blind_state.current_blind_level.level == 2

    def test_uses_default_blinds_when_no_schedule_provided(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        game = replace(
            game,
            tournament_config=replace(game.tournament_config, blind_schedule=None),
        )
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.blind_state.current_blind_level.small_blind == ChipAmount(10)
        assert new_game.blind_state.current_blind_level.big_blind == ChipAmount(20)


class TestPotStateReset:
    """Pot state is reset for new hand with eligible players."""

    def test_pot_starts_at_zero(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.pot_state.main_pot.amount == ChipAmount(0)

    def test_pot_eligible_players_includes_only_active_players(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
            sample_player_factory(
                "p3",
                Seat.SEAT_2,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert len(new_game.pot_state.main_pot.eligible_player_ids) == 2
        assert "p1" in new_game.pot_state.main_pot.eligible_player_ids
        assert "p2" in new_game.pot_state.main_pot.eligible_player_ids
        assert "p3" not in new_game.pot_state.main_pot.eligible_player_ids

    def test_side_pots_are_cleared(
        self,
        sample_player_factory: Callable[..., Player],
        minimal_game_factory: Callable[..., Game],
    ) -> None:
        players = [
            sample_player_factory("p1", Seat.SEAT_0, STARTING_CHIPS),
            sample_player_factory("p2", Seat.SEAT_1, STARTING_CHIPS),
        ]
        game = minimal_game_factory(players=Players.from_list(players))
        deck = Deck.create_shuffled(seed=42)

        new_game, _ = HandInitializer.initialize(game, deck)

        assert new_game.pot_state.side_pots == []
