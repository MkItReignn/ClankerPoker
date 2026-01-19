#!/usr/bin/env python3
"""Run a poker tournament with bot players.

This script demonstrates running a complete poker tournament using
the PokerTournamentOrchestrator with BotActionProvider.

Usage:
    python run_tournament.py [--players N] [--chips N] [--seed N] [--verbose]

Examples:
    # Run with 4 players (default)
    python run_tournament.py

    # Run with 6 players and 2000 starting chips
    python run_tournament.py --players 6 --chips 2000

    # Run with fixed seed for reproducibility
    python run_tournament.py --seed 42

    # Run with verbose logging
    python run_tournament.py --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from src.application.poker.orchestration import (
    BotActionProvider,
    GameFactory,
    PlayerSetup,
    PokerTournamentOrchestrator,
    TournamentResult,
)
from src.application.poker.action_selector import PokerRandomActionSelector
from src.application.poker.orchestration.runner import PokerGameRunner
from src.config.poker.config import PokerGameConfig, PokerPlayerConfig
from src.domain.models.llm_model import LlmModel
from src.infrastructure.persistence.json_history_repository import JsonGameHistoryRepository

# Default player names
DEFAULT_PLAYERS = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]

# Playing styles for variety
PLAYER_STYLES = [
    ("aggressive", PokerRandomActionSelector.aggressive),
    ("tight", PokerRandomActionSelector.tight),
    ("loose", PokerRandomActionSelector.loose),
    ("passive", PokerRandomActionSelector.passive),
    ("default", PokerRandomActionSelector),
    ("aggressive", PokerRandomActionSelector.aggressive),
]


def setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down noisy loggers
    if not verbose:
        logging.getLogger("src.domain").setLevel(logging.WARNING)
        logging.getLogger("src.application.use_cases").setLevel(logging.WARNING)


def create_player_configs(player_names: list[str]) -> dict[str, PokerPlayerConfig]:
    """Create player configurations."""
    configs: dict[str, PokerPlayerConfig] = {}
    for i, name in enumerate(player_names):
        player_id = f"player-{i+1}"
        configs[player_id] = PokerPlayerConfig(
            player_id=player_id,
            name=name,
            model_id=LlmModel.ANTHROPIC_CLAUDE_35_SONNET,  # Not used by bot provider
            personality=PLAYER_STYLES[i % len(PLAYER_STYLES)][0],
            addon_prompt=None,
        )
    return configs


def create_player_selectors(
    player_names: list[str],
    seed: int | None = None,
) -> dict[str, PokerRandomActionSelector]:
    """Create per-player action selectors with different styles."""
    selectors: dict[str, PokerRandomActionSelector] = {}
    for i, _name in enumerate(player_names):
        player_id = f"player-{i+1}"
        style_name, style_factory = PLAYER_STYLES[i % len(PLAYER_STYLES)]
        # Use different seeds per player for variety
        player_seed = seed + i if seed is not None else None
        selectors[player_id] = style_factory(seed=player_seed)
    return selectors


def print_tournament_result(result: TournamentResult) -> None:
    """Print tournament results."""
    print("\n" + "=" * 60)
    print("TOURNAMENT COMPLETE")
    print("=" * 60)

    if result.winner_id:
        print(f"Winner: {result.winner_name} ({result.winner_id})")
    else:
        print("No winner (tournament ended early)")

    print(f"Total hands: {result.total_hands}")
    print(f"Total actions: {result.total_actions}")

    # Print final standings
    print("\nFinal Standings:")
    print("-" * 40)

    # Get players sorted by finish position or chips
    final_state = result.final_state
    players_sorted = sorted(
        final_state.players,
        key=lambda p: (
            p.table_finish_position if p.table_finish_position else 0,
            -p.remaining_chips.value,
        ),
    )

    for i, player in enumerate(players_sorted):
        position = player.table_finish_position or (1 if player.remaining_chips.value > 0 else i + 1)
        status = "Winner" if player.remaining_chips.value > 0 else f"Out hand #{player.elimination_hand_number}"
        print(f"  {position}. {player.bot_id} - {player.remaining_chips.value} chips ({status})")

    # Print history summary if available
    if result.history:
        print(f"\nHistory: {result.history.total_hands} hands recorded")
        if result.history.completed_hands:
            last_hand = result.history.completed_hands[-1]
            print(f"Last hand: #{last_hand.hand_number}")

    print("=" * 60)


async def run_tournament(
    num_players: int,
    starting_chips: int,
    small_blind: int,
    seed: int | None,
    save_history: bool,
) -> TournamentResult:
    """Run a complete tournament."""
    # Select player names
    player_names = DEFAULT_PLAYERS[:num_players]
    print(f"Starting tournament with {num_players} players: {', '.join(player_names)}")
    print(f"Starting chips: {starting_chips}, Blinds: {small_blind}/{small_blind * 2}")
    if seed is not None:
        print(f"Random seed: {seed}")
    print()

    # Create player configs for the runner
    player_configs = create_player_configs(player_names)
    game_config = PokerGameConfig(player_configs=player_configs)

    # Create runner
    runner = PokerGameRunner(config=game_config)

    # Create action provider with per-player styles
    player_selectors = create_player_selectors(player_names, seed)
    action_provider = BotActionProvider.with_player_styles(
        player_selectors=player_selectors,
        default=PokerRandomActionSelector(seed=seed),
    )

    # Create repository for persistence (optional)
    repository = JsonGameHistoryRepository() if save_history else None

    # Create orchestrator
    orchestrator = PokerTournamentOrchestrator(
        runner=runner,
        action_provider=action_provider,
        repository=repository,
        persist_after_each_hand=save_history,
    )

    # Create initial game
    players = [
        PlayerSetup(player_id=f"player-{i+1}", name=name)
        for i, name in enumerate(player_names)
    ]

    game = GameFactory.create_tournament(
        players=players,
        starting_chips=starting_chips,
        small_blind=small_blind,
        big_blind=small_blind * 2,
        seed=seed,
    )

    print(f"Game ID: {game.id}")
    print("-" * 40)

    # Run tournament
    start_time = datetime.now()
    result = await orchestrator.run_tournament(game, max_hands=1000)
    elapsed = datetime.now() - start_time

    print(f"\nTournament completed in {elapsed.total_seconds():.2f} seconds")

    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run a poker tournament with bot players.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--players",
        "-p",
        type=int,
        default=4,
        choices=range(2, 7),
        metavar="N",
        help="Number of players (2-6, default: 4)",
    )
    parser.add_argument(
        "--chips",
        "-c",
        type=int,
        default=1500,
        help="Starting chips per player (default: 1500)",
    )
    parser.add_argument(
        "--blinds",
        "-b",
        type=int,
        default=10,
        help="Starting small blind (default: 10)",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save game history to disk",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        result = asyncio.run(
            run_tournament(
                num_players=args.players,
                starting_chips=args.chips,
                small_blind=args.blinds,
                seed=args.seed,
                save_history=not args.no_save,
            )
        )
        print_tournament_result(result)
        return 0

    except KeyboardInterrupt:
        print("\nTournament interrupted.")
        return 1
    except Exception as e:
        logging.exception("Tournament failed")
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
