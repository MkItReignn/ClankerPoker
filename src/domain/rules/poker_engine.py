from __future__ import annotations

from copy import deepcopy

from src.domain.models.blinds import BlindLevel, BlindSchedule
from src.domain.models.chips import ChipAmount
from src.domain.models.deck import Deck
from src.domain.models.game import (
    NO_CURRENT_PLAYER,
    BettingState,
    BlindState,
    Game,
    GamePhase,
    GameResults,
    HandState,
    TablePositions,
)
from src.domain.models.hand import Hand
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
    PlayerId,
)
from src.domain.models.pot import Pot, PotState
from src.domain.rules.first_to_act_calculator import FirstToActCalculator
from src.domain.rules.hand_evaluator import HandEvaluation, HandEvaluator
from src.domain.rules.position_resolver import PositionResolver
from src.domain.rules.pot_calculator import PotCalculator


class PokerEngine:
    """
    Main poker engine orchestrator.

    Coordinates high-level game operations:
    - advance_betting_round: Completes betting round and advances phase
    - initialize_hand: Starts new hand, deals cards, posts blinds
    - determine_winners: Determines winners across all pots
    - complete_hand: Completes hand and distributes winnings
    """

    @staticmethod
    def advance_betting_round(game: Game) -> Game:
        """
        Complete current betting round and advance to next phase.

        Handles:
        - Updating pot state (pot calculation now handled by PotCalculator)
        - Resetting player betting status to NEEDS_ACTION
        - Advancing game phase (PRE_FLOP -> FLOP -> TURN -> RIVER -> SHOWDOWN)
        """
        players_in_hand = game.players_in_hand()
        if not players_in_hand:
            raise ValueError("Cannot advance betting round: no players in hand")

        updated_pot_state = PotCalculator.calculate_pot_state(players_in_hand)

        updated_players = deepcopy(game.players)
        for player in updated_players:
            if player.is_in_hand():
                if not player.is_all_in():
                    player.betting_status = BettingRoundActionStatus.NEEDS_ACTION

        next_phase = game.hand_state.current_phase.next_phase()
        if next_phase is None:
            raise ValueError(f"Cannot advance beyond {game.hand_state.current_phase}")

        cards_to_deal = next_phase.card_count - len(game.hand_state.community_cards)
        if cards_to_deal > 0:
            raise ValueError(
                "Cannot advance betting round: community cards must be dealt externally"
            )

        updated_community_cards = list(game.hand_state.community_cards)
        updated_hand_state = HandState(
            hand_number=game.hand_state.hand_number,
            current_phase=next_phase,
            community_cards=updated_community_cards,
        )

        next_player_position = FirstToActCalculator.calculate_first_to_act(
            all_players=updated_players,
            table_positions=game.table_positions,
            phase=next_phase,
        )

        updated_betting_state = BettingState(
            last_raise_increment=ChipAmount(0),
            current_player_position=next_player_position,
        )

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=updated_hand_state,
            pot_state=updated_pot_state,
            betting_state=updated_betting_state,
            table_positions=game.table_positions,
            blind_state=game.blind_state,
            players=updated_players,
            results=game.results,
        )

    @staticmethod
    def _get_blind_level_for_hand(
        hand_number: int, blind_schedule: BlindSchedule | None
    ) -> BlindLevel:
        """Get the blind level that applies to the given hand number.

        If blind_schedule is provided, uses it to determine the level.
        Otherwise, returns a default level (for backward compatibility).
        """
        if blind_schedule is not None:
            return blind_schedule.get_blind_level_for_hand(hand_number)

        return BlindLevel(
            small_blind=ChipAmount(10),
            big_blind=ChipAmount(20),
            level=1,
        )

    @staticmethod
    def _post_blind(
        players: list[Player],
        blind_position: int,
        blind_amount: ChipAmount,
    ) -> Player:
        """Post a blind for a single player.

        Posts the blind amount (or all chips if insufficient),
        updates investment, and sets betting status.

        Both blinds need to act during the betting round unless all-in.

        Returns:
            Updated player after posting blind.
        """
        player = players[blind_position]

        blind_posted = min(blind_amount.value, player.remaining_chips.value)

        player.remaining_chips = ChipAmount(player.remaining_chips.value - blind_posted)
        player.total_invested_this_hand = ChipAmount(blind_posted)

        is_all_in = player.remaining_chips.value == 0
        player.betting_status = (
            BettingRoundActionStatus.ACTED if is_all_in else BettingRoundActionStatus.NEEDS_ACTION
        )

        return player

    @staticmethod
    def _post_blinds(
        players: list[Player],
        small_blind_pos: int,
        big_blind_pos: int,
        small_blind_amount: ChipAmount,
        big_blind_amount: ChipAmount,
    ) -> tuple[Player, Player]:
        """Post small and big blinds for the current hand.

        Both blinds need to act during the betting round unless all-in:
        - SB acts before BB in normal play
        - BB has the option to check or raise when action returns

        Returns:
            Tuple of (small_blind_player, big_blind_player) after posting.
        """
        small_blind_player = PokerEngine._post_blind(players, small_blind_pos, small_blind_amount)
        big_blind_player = PokerEngine._post_blind(players, big_blind_pos, big_blind_amount)

        return (small_blind_player, big_blind_player)

    @staticmethod
    def initialize_hand(game: Game, deck: Deck) -> tuple[Game, Deck]:
        """
        Start a new hand:
        - Deal hole cards to all active players
        - Post small/big blinds
        - Set dealer button
        - Initialize betting round

        Returns:
            (new_game, updated_deck)
        """
        active_players = game.get_non_eliminated_players()
        if len(active_players) < 2:
            raise ValueError(
                f"Cannot initialize hand: need at least 2 players, got {len(active_players)}"
            )

        updated_deck = deepcopy(x=deck)
        updated_players = deepcopy(game.players)

        for player in updated_players:
            if player.participation_status != HandParticipationStatus.ELIMINATED:
                card1 = updated_deck.deal_card()
                card2 = updated_deck.deal_card()
                player.reset_for_new_hand(Hand(card1=card1, card2=card2))

        next_hand_number = game.hand_state.hand_number + 1
        blind_level = PokerEngine._get_blind_level_for_hand(
            next_hand_number, game.tournament_config.blind_schedule
        )
        updated_blind_state = BlindState(current_blind_level=blind_level)

        updated_table_positions: TablePositions = PositionResolver.resolve_positions_for_new_hand(
            all_players=updated_players,
            current_dealer_position=game.table_positions.dealer_position,
            is_first_hand=(game.hand_state.hand_number == 0),
        )

        small_blind_pos = updated_table_positions.small_blind_position
        big_blind_pos = updated_table_positions.big_blind_position

        small_blind_player, big_blind_player = PokerEngine._post_blinds(
            updated_players,
            small_blind_pos,
            big_blind_pos,
            blind_level.small_blind,
            blind_level.big_blind,
        )

        updated_players[small_blind_pos] = small_blind_player
        updated_players[big_blind_pos] = big_blind_player

        updated_hand_state = HandState(
            hand_number=next_hand_number,
            current_phase=GamePhase.PRE_FLOP,
            community_cards=[],
        )

        eligible_ids = game.get_non_eliminated_player_ids()
        updated_pot_state = PotState(
            main_pot=Pot(amount=ChipAmount(0), eligible_player_ids=eligible_ids),
            side_pots=[],
        )

        first_to_act = FirstToActCalculator.calculate_first_to_act(
            all_players=updated_players,
            table_positions=updated_table_positions,
            phase=GamePhase.PRE_FLOP,
        )

        if first_to_act == NO_CURRENT_PLAYER:
            temp_game = Game(
                identity=game.identity,
                tournament_config=game.tournament_config,
                hand_state=updated_hand_state,
                pot_state=updated_pot_state,
                betting_state=BettingState(
                    last_raise_increment=ChipAmount(0),
                    current_player_position=NO_CURRENT_PLAYER,
                ),
                table_positions=updated_table_positions,
                blind_state=updated_blind_state,
                players=updated_players,
                results=game.results,
            )
            if not temp_game.is_round_complete():
                raise ValueError(
                    "Cannot initialize hand: no player to act and betting round is not complete"
                )

        updated_betting_state = BettingState(
            last_raise_increment=ChipAmount(0),
            current_player_position=first_to_act,
        )

        return (
            Game(
                identity=game.identity,
                tournament_config=game.tournament_config,
                hand_state=updated_hand_state,
                pot_state=updated_pot_state,
                betting_state=updated_betting_state,
                table_positions=updated_table_positions,
                blind_state=updated_blind_state,
                players=updated_players,
                results=game.results,
            ),
            updated_deck,
        )

    @staticmethod
    def determine_winners(game: Game) -> list[tuple[PlayerId, ChipAmount]]:
        """
        Determine winners and calculate payouts including side pots.

        For each pot (main + side pots):
        1. Find eligible players (those who can win this pot)
        2. Evaluate each eligible player's hand
        3. Determine winners (strongest hands, ties split pot)
        4. Distribute pot among winners

        Returns:
            List of (player_id, total_payout) tuples for all winners.
            Payouts are aggregated across all pots the player won.
        """
        players_in_hand = game.players_in_hand()

        if not players_in_hand:
            return []

        if len(players_in_hand) == 1:
            total_pot = game.pot_state.main_pot.amount.value + sum(
                pot.amount.value for pot in game.pot_state.side_pots
            )
            return [(players_in_hand[0].id, ChipAmount(total_pot))]

        player_payouts: dict[PlayerId, int] = {}

        all_pots = [game.pot_state.main_pot] + game.pot_state.side_pots

        for pot in all_pots:
            eligible_players = [p for p in players_in_hand if p.id in pot.eligible_player_ids]

            if not eligible_players:
                continue

            if len(eligible_players) == 1:
                player_id = eligible_players[0].id
                player_payouts[player_id] = player_payouts.get(player_id, 0) + pot.amount.value
                continue

            evaluations: list[tuple[Player, HandEvaluation]] = []
            for player in eligible_players:
                if player.hole_cards is None:
                    continue
                evaluation = HandEvaluator.evaluate_hand_strength(
                    player.hole_cards, game.community_cards
                )
                evaluations.append((player, evaluation))

            if not evaluations:
                continue

            best_evaluation = evaluations[0][1]
            for _, evaluation in evaluations[1:]:
                if evaluation.compare(best_evaluation) > 0:
                    best_evaluation = evaluation

            winners = [player for player, eval in evaluations if eval.compare(best_evaluation) == 0]

            if not winners:
                continue

            pot_per_winner = pot.amount.value // len(winners)
            remainder = pot.amount.value % len(winners)

            for i, player in enumerate(winners):
                payout = pot_per_winner + (1 if i < remainder else 0)
                player_payouts[player.id] = player_payouts.get(player.id, 0) + payout

        return [(player_id, ChipAmount(payout)) for player_id, payout in player_payouts.items()]

    @staticmethod
    def complete_hand(game: Game) -> Game:
        """
        Complete the current hand and distribute winnings.

        Handles two scenarios:
        1. Early win: Only one player remains → award entire pot
        2. Showdown: Multiple players remain → calculate side pots, determine winners, distribute

        Returns:
            Updated game with winnings distributed and hand marked as complete
        """
        if not game.is_hand_complete():
            raise ValueError("Cannot complete hand: hand is not yet complete")

        players_in_hand = game.players_in_hand()

        if len(players_in_hand) == 1:
            return PokerEngine._complete_hand_early_win(game, players_in_hand[0])

        if game.current_phase == GamePhase.SHOWDOWN:
            return PokerEngine._complete_hand_showdown(game, players_in_hand)

        raise ValueError(
            f"Cannot complete hand: invalid state - phase={game.current_phase.value}, "
            + f"players_in_hand={len(players_in_hand)}"
        )

    @staticmethod
    def _complete_hand_early_win(game: Game, winner: Player) -> Game:
        """
        Complete hand when only one player remains (all others folded).

        Awards entire pot to the remaining player.
        """
        total_pot = game.pot_state.main_pot.amount.value + sum(
            pot.amount.value for pot in game.pot_state.side_pots
        )

        updated_players = deepcopy(game.players)
        winner_index = next(i for i, p in enumerate(updated_players) if p.id == winner.id)

        updated_players[winner_index].remaining_chips = ChipAmount(
            updated_players[winner_index].remaining_chips.value + total_pot
        )

        updated_table_positions = TablePositions(
            dealer_position=game.table_positions.dealer_position,
            small_blind_position=game.table_positions.small_blind_position,
            big_blind_position=game.table_positions.big_blind_position,
        )

        updated_results = GameResults(winners=[(winner.id, ChipAmount(total_pot))])

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=game.pot_state,
            betting_state=game.betting_state,
            table_positions=updated_table_positions,
            blind_state=game.blind_state,
            players=updated_players,
            results=updated_results,
        )

    @staticmethod
    def _complete_hand_showdown(game: Game, players_in_hand: list[Player]) -> Game:
        """
        Complete hand at showdown.

        Calculates side pots, determines winners, and distributes winnings.
        Requires HandEvaluator to be implemented for determine_winners().
        """
        updated_pot_state = PotCalculator.calculate_pot_state(players_in_hand)

        game_with_updated_pots = Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=updated_pot_state,
            betting_state=game.betting_state,
            table_positions=game.table_positions,
            blind_state=game.blind_state,
            players=game.players,
            results=game.results,
        )

        winners = PokerEngine.determine_winners(game_with_updated_pots)

        updated_players = deepcopy(game.players)
        for winner_id, payout in winners:
            player_index = next(i for i, p in enumerate(updated_players) if p.id == winner_id)
            updated_players[player_index].remaining_chips = ChipAmount(
                updated_players[player_index].remaining_chips.value + payout.value
            )

        updated_table_positions = TablePositions(
            dealer_position=game.table_positions.dealer_position,
            small_blind_position=game.table_positions.small_blind_position,
            big_blind_position=game.table_positions.big_blind_position,
        )

        updated_results = GameResults(winners=winners)

        return Game(
            identity=game.identity,
            tournament_config=game.tournament_config,
            hand_state=game.hand_state,
            pot_state=updated_pot_state,
            betting_state=game.betting_state,
            table_positions=updated_table_positions,
            blind_state=game.blind_state,
            players=updated_players,
            results=updated_results,
        )
