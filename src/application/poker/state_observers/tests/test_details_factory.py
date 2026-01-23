from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.application.poker.state_observers.details import (
    ActionAppliedDetails,
    BlindInfo,
    BlindsPostedDetails,
    GameCompletedDetails,
    GameStartedDetails,
    HandStartedDetails,
    HoleCardDealtDetail,
    HoleCardsDealtDetails,
    PlayerToActDetails,
    RoundCompletedDetails,
    RoundStartedDetails,
)
from src.application.poker.state_observers.details_factory import (
    DetailsFactory,
    HasActionFields,
    HasActionTypeAndAmount,
)
from src.domain.models.actions import ActionType
from src.domain.models.card import Card, Rank, Suit
from src.domain.models.chips import ChipAmount
from src.domain.models.game import GamePhase, HandOutcome as GameHandOutcome
from src.domain.models.hand import Hand
from src.domain.models.narration import Narration, NarrationText
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    PlayerId,
)
from src.domain.models.seat import Seat


@dataclass(frozen=True)
class MockAction:
    action_type: ActionType
    amount: ChipAmount | None


@dataclass(frozen=True)
class MockActionResponse:
    action: MockAction
    narration: Narration | None


class TestGameStarted:
    def test_returns_player_count_from_game(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
            sample_player_factory(PlayerId("p3"), Seat.SEAT_2, ChipAmount(1000)),
        ]
        game = game_factory(players=players)

        result = DetailsFactory.game_started(game)

        assert result.player_count == 3

    def test_returns_starting_chips_from_tournament_config(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)

        result = DetailsFactory.game_started(game)

        assert result.starting_chips == ChipAmount(1000)


class TestGameCompleted:
    def test_returns_winner_info_when_one_active_player(
        self, game_factory, sample_player_factory
    ):
        winner = sample_player_factory(
            PlayerId("winner"),
            Seat.SEAT_0,
            ChipAmount(2000),
            name="Winner Bot",
        )
        eliminated = sample_player_factory(
            PlayerId("loser"),
            Seat.SEAT_1,
            ChipAmount(0),
            participation_status=HandParticipationStatus.ELIMINATED,
        )
        game = game_factory(players=[winner, eliminated], hand_number=5)

        result = DetailsFactory.game_completed(game)

        assert result.winner_id == "winner"
        assert result.winner_name == "Winner Bot"
        assert result.total_hands == 5

    def test_raises_when_no_active_players(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        game = game_factory(players=players)

        with pytest.raises(ValueError, match="no active players"):
            DetailsFactory.game_completed(game)


class TestHandStarted:
    def test_returns_hand_number_from_game(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players, hand_number=7)

        result = DetailsFactory.hand_started(game)

        assert result.hand_number == 7

    def test_returns_button_seat_from_game(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players, button_seat=Seat.SEAT_1)

        result = DetailsFactory.hand_started(game)

        assert result.button_seat == Seat.SEAT_1


class TestHandCompleted:
    def test_returns_winners_from_outcome(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1500), name="Alice"
            ),
            sample_player_factory(
                PlayerId("p2"), Seat.SEAT_1, ChipAmount(500), name="Bob"
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=1, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert len(result.winners) == 1
        assert result.winners[0].player_id == "p1"
        assert result.winners[0].player_name == "Alice"
        assert result.winners[0].amount == ChipAmount(100)

    def test_returns_eliminated_players_from_current_hand(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(2000)),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                name="Busted Bob",
                elimination_hand_number=3,
                table_finish_position=2,
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=3, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, hand_number=3, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert len(result.eliminated) == 1
        assert result.eliminated[0].player_id == "p2"
        assert result.eliminated[0].player_name == "Busted Bob"
        assert result.eliminated[0].finish_position == 2

    def test_excludes_players_eliminated_in_previous_hands(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(2000)),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(0),
                elimination_hand_number=1,
                table_finish_position=3,
                participation_status=HandParticipationStatus.ELIMINATED,
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=3, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, hand_number=3, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert len(result.eliminated) == 0

    def test_returns_none_showdown_when_not_showdown_phase(
        self, game_factory, sample_player_factory, sample_hand
    ):
        players = [
            sample_player_factory(
                PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000), hole_cards=sample_hand
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=1, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, current_phase=GamePhase.PRE_FLOP, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert result.showdown is None

    def test_returns_none_showdown_when_single_player_remaining(
        self, game_factory, sample_player_factory, sample_hand
    ):
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                hole_cards=sample_hand,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=1, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, current_phase=GamePhase.SHOWDOWN, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert result.showdown is None

    def test_returns_showdown_info_with_hand_evaluations(
        self, game_factory, sample_player_factory
    ):
        hand1 = Hand(
            card1=Card(rank=Rank.ACE, suit=Suit.SPADES),
            card2=Card(rank=Rank.ACE, suit=Suit.HEARTS),
        )
        hand2 = Hand(
            card1=Card(rank=Rank.KING, suit=Suit.SPADES),
            card2=Card(rank=Rank.KING, suit=Suit.HEARTS),
        )
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                hole_cards=hand1,
                name="Ace Player",
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                hole_cards=hand2,
                name="King Player",
            ),
        ]
        outcome = GameHandOutcome(
            hand_number=1, winners=[(PlayerId("p1"), ChipAmount(100))]
        )
        game = game_factory(players=players, current_phase=GamePhase.SHOWDOWN, outcome=outcome)

        result = DetailsFactory.hand_completed(game)

        assert result.showdown is not None
        assert len(result.showdown) == 2
        player_ids = {s.player_id for s in result.showdown}
        assert player_ids == {"p1", "p2"}


class TestRoundStarted:
    def test_returns_current_phase(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players, current_phase=GamePhase.FLOP)

        result = DetailsFactory.round_started(game)

        assert result.phase == GamePhase.FLOP

    def test_returns_empty_cards_for_preflop(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players, current_phase=GamePhase.PRE_FLOP)

        result = DetailsFactory.round_started(game)

        assert result.new_cards == ()

    def test_returns_three_cards_for_flop(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        community = [
            Card(rank=Rank.TWO, suit=Suit.CLUBS),
            Card(rank=Rank.FIVE, suit=Suit.HEARTS),
            Card(rank=Rank.NINE, suit=Suit.DIAMONDS),
        ]
        game = game_factory(
            players=players,
            current_phase=GamePhase.FLOP,
            community_cards=community,
        )

        result = DetailsFactory.round_started(game)

        assert len(result.new_cards) == 3
        assert result.new_cards == tuple(community)

    def test_returns_one_card_for_turn(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        community = [
            Card(rank=Rank.TWO, suit=Suit.CLUBS),
            Card(rank=Rank.FIVE, suit=Suit.HEARTS),
            Card(rank=Rank.NINE, suit=Suit.DIAMONDS),
            Card(rank=Rank.JACK, suit=Suit.SPADES),
        ]
        game = game_factory(
            players=players,
            current_phase=GamePhase.TURN,
            community_cards=community,
        )

        result = DetailsFactory.round_started(game)

        assert len(result.new_cards) == 1
        assert result.new_cards[0] == Card(rank=Rank.JACK, suit=Suit.SPADES)

    def test_returns_one_card_for_river(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        community = [
            Card(rank=Rank.TWO, suit=Suit.CLUBS),
            Card(rank=Rank.FIVE, suit=Suit.HEARTS),
            Card(rank=Rank.NINE, suit=Suit.DIAMONDS),
            Card(rank=Rank.JACK, suit=Suit.SPADES),
            Card(rank=Rank.ACE, suit=Suit.HEARTS),
        ]
        game = game_factory(
            players=players,
            current_phase=GamePhase.RIVER,
            community_cards=community,
        )

        result = DetailsFactory.round_started(game)

        assert len(result.new_cards) == 1
        assert result.new_cards[0] == Card(rank=Rank.ACE, suit=Suit.HEARTS)

    def test_returns_empty_cards_for_showdown(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players, current_phase=GamePhase.SHOWDOWN)

        result = DetailsFactory.round_started(game)

        assert result.new_cards == ()


class TestRoundCompleted:
    def test_returns_empty_details(self):
        result = DetailsFactory.round_completed()

        assert isinstance(result, RoundCompletedDetails)


class TestBlindsPosted:
    def test_returns_small_and_big_blind_info(
        self, game_factory, sample_player_factory
    ):
        sb_player = sample_player_factory(
            PlayerId("sb"),
            Seat.SEAT_1,
            ChipAmount(990),
            total_invested_this_hand=ChipAmount(10),
            name="SB Player",
        )
        bb_player = sample_player_factory(
            PlayerId("bb"),
            Seat.SEAT_0,
            ChipAmount(980),
            total_invested_this_hand=ChipAmount(20),
            name="BB Player",
        )
        game = game_factory(
            players=[bb_player, sb_player],
            button_seat=Seat.SEAT_1,
        )

        result = DetailsFactory.blinds_posted(game)

        assert result.small_blind.player_id == "sb"
        assert result.small_blind.player_name == "SB Player"
        assert result.small_blind.amount == ChipAmount(10)
        assert result.big_blind.player_id == "bb"
        assert result.big_blind.player_name == "BB Player"
        assert result.big_blind.amount == ChipAmount(20)


class TestHoleCardsDealt:
    def test_returns_hole_cards_for_all_players_in_hand(
        self, game_factory, sample_player_factory
    ):
        hand1 = Hand(
            card1=Card(rank=Rank.ACE, suit=Suit.SPADES),
            card2=Card(rank=Rank.KING, suit=Suit.SPADES),
        )
        hand2 = Hand(
            card1=Card(rank=Rank.QUEEN, suit=Suit.HEARTS),
            card2=Card(rank=Rank.JACK, suit=Suit.HEARTS),
        )
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                hole_cards=hand1,
                name="Player One",
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                hole_cards=hand2,
                name="Player Two",
            ),
        ]
        game = game_factory(players=players, button_seat=Seat.SEAT_0)

        result = DetailsFactory.hole_cards_dealt(game)

        assert len(result.players) == 2
        assert result.players["p1"].player_name == "Player One"
        assert result.players["p1"].cards == hand1
        assert result.players["p2"].player_name == "Player Two"
        assert result.players["p2"].cards == hand2

    def test_excludes_folded_players(self, game_factory, sample_player_factory):
        hand1 = Hand(
            card1=Card(rank=Rank.ACE, suit=Suit.SPADES),
            card2=Card(rank=Rank.KING, suit=Suit.SPADES),
        )
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                hole_cards=hand1,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                participation_status=HandParticipationStatus.FOLDED,
            ),
        ]
        game = game_factory(players=players)

        result = DetailsFactory.hole_cards_dealt(game)

        assert "p1" in result.players
        assert "p2" not in result.players

    def test_includes_deal_order_based_on_position(
        self, game_factory, sample_player_factory
    ):
        hand = Hand(
            card1=Card(rank=Rank.ACE, suit=Suit.SPADES),
            card2=Card(rank=Rank.KING, suit=Suit.SPADES),
        )
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(980),
                hole_cards=hand,
                total_invested_this_hand=ChipAmount(20),
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(990),
                hole_cards=hand,
                total_invested_this_hand=ChipAmount(10),
            ),
        ]
        game = game_factory(players=players, button_seat=Seat.SEAT_1)

        result = DetailsFactory.hole_cards_dealt(game)

        assert result.players["p2"].deal_order > 0
        assert result.players["p1"].deal_order > 0


class TestPlayerToAct:
    def test_returns_player_info_when_player_to_act_exists(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                name="Acting Player",
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
        ]
        game = game_factory(players=players, position_to_act=0)

        result = DetailsFactory.player_to_act(game)

        assert result.player_id == "p1"
        assert result.player_name == "Acting Player"
        assert isinstance(result.available_actions, list)

    def test_raises_when_no_player_to_act(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
            sample_player_factory(
                PlayerId("p2"),
                Seat.SEAT_1,
                ChipAmount(1000),
                betting_status=BettingRoundActionStatus.ACTED,
            ),
        ]
        game = game_factory(players=players, position_to_act=0)

        with pytest.raises(ValueError, match="No player to act"):
            DetailsFactory.player_to_act(game)


class TestActionApplied:
    def test_returns_action_details_from_response(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(
                PlayerId("p1"),
                Seat.SEAT_0,
                ChipAmount(900),
                name="Betting Player",
            ),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)
        response = MockActionResponse(
            action=MockAction(action_type=ActionType.BET, amount=ChipAmount(100)),
            narration=None,
        )

        result = DetailsFactory.action_applied(game, "p1", response)

        assert result.player_id == "p1"
        assert result.player_name == "Betting Player"
        assert result.action_type == ActionType.BET
        assert result.amount == ChipAmount(100)
        assert result.narration is None

    def test_includes_narration_when_present(
        self, game_factory, sample_player_factory
    ):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)
        narration = Narration(thought_process=NarrationText("I have a strong hand, going all-in!"))
        response = MockActionResponse(
            action=MockAction(action_type=ActionType.ALL_IN, amount=ChipAmount(1000)),
            narration=narration,
        )

        result = DetailsFactory.action_applied(game, "p1", response)

        assert result.narration == narration

    def test_raises_when_player_not_found(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)
        response = MockActionResponse(
            action=MockAction(action_type=ActionType.FOLD, amount=None),
            narration=None,
        )

        with pytest.raises(ValueError, match="not found"):
            DetailsFactory.action_applied(game, "nonexistent", response)

    def test_handles_fold_with_no_amount(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)
        response = MockActionResponse(
            action=MockAction(action_type=ActionType.FOLD, amount=None),
            narration=None,
        )

        result = DetailsFactory.action_applied(game, "p1", response)

        assert result.action_type == ActionType.FOLD
        assert result.amount is None

    def test_handles_check_with_no_amount(self, game_factory, sample_player_factory):
        players = [
            sample_player_factory(PlayerId("p1"), Seat.SEAT_0, ChipAmount(1000)),
            sample_player_factory(PlayerId("p2"), Seat.SEAT_1, ChipAmount(1000)),
        ]
        game = game_factory(players=players)
        response = MockActionResponse(
            action=MockAction(action_type=ActionType.CHECK, amount=None),
            narration=None,
        )

        result = DetailsFactory.action_applied(game, "p1", response)

        assert result.action_type == ActionType.CHECK
        assert result.amount is None
