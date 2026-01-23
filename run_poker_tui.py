#!/usr/bin/env python
"""Entry point for running poker tournaments with TUI viewer.

Usage:
    poetry run python run_poker_tui.py --bot
    poetry run python run_poker_tui.py --bot --seed 42
    poetry run python run_poker_tui.py --bot --max-hands 10
    poetry run python run_poker_tui.py --bot --delay 0.5
"""

import argparse
import asyncio
import secrets
import sys

from src.application.poker.events import EventPublisher, PublishedEvent
from src.application.poker.game_factory import (
    GameDependencies,
    create_bot_dependencies,
    create_llm_dependencies,
)
from src.application.poker.orchestration import PokerOrchestrator, PokerStateManager
from src.config.tournament import TournamentConfig, TournamentConfigLoader
from src.domain.utils.game_id import generate_game_id
from src.infrastructure.realtime import TuiEventTransport

# TODO: Import once presentation/tui is implemented
# from src.presentation.tui import PokerViewerApp


async def run_tournament_with_tui(
    seed: int | None = None,
    max_hands: int | None = None,
    event_delay: float = 0.3,
    use_bot: bool = False,
) -> int:
    effective_seed: int = seed if seed is not None else secrets.randbits(64)
    game_id: str = generate_game_id()

    try:
        tournament_config: TournamentConfig = TournamentConfigLoader().load()

        event_queue: asyncio.Queue[PublishedEvent | None] = asyncio.Queue()
        transport: TuiEventTransport = TuiEventTransport(event_queue)
        publisher: EventPublisher = EventPublisher(transport=transport)

        deps: GameDependencies = (
            create_bot_dependencies(seed=effective_seed)
            if use_bot
            else create_llm_dependencies()
        )

        state: PokerStateManager = PokerStateManager(
            config=deps.poker_config,
            tournament_config=tournament_config,
            game_id=game_id,
            seed=effective_seed,
        )
        state._notifier.add_observer(publisher)

        orchestrator: PokerOrchestrator = PokerOrchestrator(
            state=state,
            action_provider=deps.action_provider,
            max_hands=max_hands,
        )

        async def run_game() -> None:
            try:
                await orchestrator.run_game()
            except Exception as e:
                print(f"Game error: {e}")
                raise
            finally:
                await transport.close()

        # TODO: Replace with actual TUI app once implemented
        # app = PokerViewerApp(event_queue=event_queue, event_delay=event_delay)
        # async with asyncio.TaskGroup() as tg:
        #     tg.create_task(run_game())
        #     await app.run_async()

        # Temporary: Run game and print events to console
        async def print_events() -> None:
            while True:
                event: PublishedEvent | None = await event_queue.get()
                if event is None:
                    break
                print(f"[{event.event_type}] {event.details}")
                await asyncio.sleep(event_delay)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_game())
            tg.create_task(print_events())

        return 0

    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
        return 1
    except KeyboardInterrupt:
        print("Tournament cancelled by user")
        return 1
    except Exception as e:
        print(f"Tournament failed: {e}")
        return 1


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Run a poker tournament with TUI viewer",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible games",
    )
    parser.add_argument(
        "--max-hands",
        type=int,
        help="Maximum number of hands (safety limit)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between events in seconds (default: 0.3)",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Use bot players instead of LLM",
    )

    args: argparse.Namespace = parser.parse_args()

    exit_code: int = asyncio.run(
        run_tournament_with_tui(
            seed=args.seed,
            max_hands=args.max_hands,
            event_delay=args.delay,
            use_bot=args.bot,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
