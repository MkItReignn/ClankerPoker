import secrets
from datetime import UTC, datetime

from src.config.poker.config import PokerPlayerConfig
from src.config.tournament.config import TournamentConfig
from src.domain.models.bot import BotId
from src.domain.models.chips import ChipAmount
from src.domain.models.game import (
    NO_POSITION_TO_ACT,
    BettingState,
    BlindState,
    Game,
    GameIdentity,
    GameStatus,
    HandPhase,
    HandState,
)
from src.domain.models.player import (
    BettingRoundActionStatus,
    HandParticipationStatus,
    Player,
)
from src.domain.models.players import Players
from src.domain.models.pot import Pot, PotState
from src.domain.models.seat import Seat
from src.domain.rules.button_assigner import ButtonAssigner
from src.domain.utils import generate_game_id


class GameInitializer:
    """Creates tournament games ready for play.

    Handles player creation, game structure setup, and button assignment via
    high card draw. Returns a game in IN_PROGRESS status with is_initial_hand_setup=True,
    ready for StateManager to deal the first hand.
    """

    @staticmethod
    def create_tournament(
        player_configs: list[PokerPlayerConfig],
        tournament_config: TournamentConfig,
        seed: int | None = None,
        game_id: str | None = None,
    ) -> Game:
        """Create a tournament game ready for first hand.

        Returns a game with:
        - Status: IN_PROGRESS
        - Button assigned via high card draw
        - is_initial_hand_setup=True (cards not yet dealt)

        StateManager should call _init_new_hand to deal the first hand.
        """
        if len(player_configs) < 2:
            raise ValueError(
                f"Tournament requires at least 2 players, got {len(player_configs)}"
            )
        if len(player_configs) > 6:
            raise ValueError(
                f"Tournament allows at most 6 players, got {len(player_configs)}"
            )

        if game_id is None:
            game_id = generate_game_id()

        if seed is None:
            seed = secrets.randbits(64)

        players = GameInitializer._create_players(
            player_configs, tournament_config
        )
        game = GameInitializer._create_base_game(
            players, tournament_config, game_id, seed
        )
        game = ButtonAssigner.assign_button(game)

        return game

    @staticmethod
    def _create_players(
        configs: list[PokerPlayerConfig],
        tournament_config: TournamentConfig,
    ) -> Players:
        starting_chips = tournament_config.starting_chip_stack.value
        player_list: list[Player] = []
        seen_ids: set[str] = set()

        for i, config in enumerate(configs):
            if config.player_id in seen_ids:
                raise ValueError(f"Duplicate player_id: {config.player_id}")
            seen_ids.add(config.player_id)

            player = Player(
                id=config.player_id,
                name=config.name,
                bot_id=BotId(config.name),
                llm_model=config.model_id,
                seat=Seat.from_int(i),
                remaining_chips=ChipAmount(starting_chips),
                hole_cards=None,
                betting_status=BettingRoundActionStatus.NEEDS_ACTION,
                participation_status=HandParticipationStatus.IN_HAND,
                total_invested_this_hand=ChipAmount(0),
                hands_played=0,
                can_raise=True,
            )
            player_list.append(player)

        return Players.from_list(player_list)

    @staticmethod
    def _create_base_game(
        players: Players,
        tournament_config: TournamentConfig,
        game_id: str,
        seed: int,
    ) -> Game:
        now = datetime.now(UTC)

        identity = GameIdentity(
            id=game_id,
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=None,
            status=GameStatus.IN_PROGRESS,
            seed=seed,
        )

        hand_state = HandState(
            hand_number=1,
            current_phase=HandPhase.PRE_FLOP,
            community_cards=[],
            is_initial_hand_setup=True,
        )

        all_player_ids = frozenset(p.id for p in players)
        pot_state = PotState(
            main_pot=Pot(
                amount=ChipAmount(0), eligible_player_ids=all_player_ids
            ),
            side_pots=[],
        )

        betting_state = BettingState(
            last_raise_increment=ChipAmount(0),
            position_to_act=NO_POSITION_TO_ACT,
        )

        initial_blind_level = (
            tournament_config.blind_schedule.get_blind_level_for_hand(1)
        )
        blind_state = BlindState(current_blind_level=initial_blind_level)

        return Game(
            identity=identity,
            tournament_config=tournament_config,
            hand_state=hand_state,
            pot_state=pot_state,
            betting_state=betting_state,
            button_seat=Seat.from_int(0),  # Placeholder, set by ButtonAssigner
            blind_state=blind_state,
            players=players,
            outcome=None,
        )
