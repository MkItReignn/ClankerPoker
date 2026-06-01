#!/usr/bin/env python
"""Entry point for running poker tournaments with TUI viewer.

Usage:
    poetry run python run_poker_tui.py --bot
    poetry run python run_poker_tui.py --bot --seed 42
    poetry run python run_poker_tui.py --bot --max-hands 10
    poetry run python run_poker_tui.py --bot --delay 0.5
    poetry run python run_poker_tui.py --bot --web
    poetry run python run_poker_tui.py --bot --web --port 8080
    poetry run python run_poker_tui.py --replay
    poetry run python run_poker_tui.py --replay path/to/record.json
"""

import argparse
import asyncio
import sys
from pathlib import Path

from src.application.poker.events import EventPublisher, PublishedEvent
from src.application.poker.game_factory import (
    RuntimeConfig,
    RuntimeConfigFactory,
)
from src.application.poker.orchestration import (
    PokerOrchestrator,
    PokerStateManager,
)
from src.application.replay import RecordLoadError
from src.infrastructure.realtime import TuiEventTransport
from src.logger.config import configure_logging
from src.presentation.tui import PokerViewerApp

DEFAULT_REPLAY_PATH: Path = Path("replay/llm_default.json")
DEFAULT_EVENT_DELAY: float = 0.3
DEFAULT_WEB_HOST: str = "localhost"
DEFAULT_WEB_PORT: int = 8000


async def run_with_tui(
    config: RuntimeConfig,
    max_hands: int | None = None,
    event_delay: float = 0.3,
    show_seed: bool = False,
) -> int:
    configure_logging(prefix="poker_tui", dev_mode=True, verbose=False)

    try:
        event_queue: asyncio.Queue[PublishedEvent | None] = asyncio.Queue()
        transport: TuiEventTransport = TuiEventTransport(event_queue)
        publisher: EventPublisher = EventPublisher(transport=transport)
        shutdown_event: asyncio.Event = asyncio.Event()

        state: PokerStateManager = PokerStateManager(
            config=config.poker_config,
            tournament_config=config.tournament_config,
            game_id=config.game_id,
            seed=config.seed,
            repository=config.repository,
        )
        state._notifier.add_observer(publisher)

        orchestrator: PokerOrchestrator = PokerOrchestrator(
            state=state,
            action_provider=config.action_provider,
            max_hands=max_hands,
            shutdown_event=shutdown_event,
        )

        async def run_game() -> None:
            try:
                await orchestrator.run_game()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Game error: {e}")
                raise
            finally:
                await transport.close()

        app: PokerViewerApp = PokerViewerApp(
            queue=event_queue,
            event_delay=event_delay,
            show_seed=show_seed,
            seed=config.seed if show_seed else None,
            shutdown_event=shutdown_event,
        )

        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_game())
            tg.create_task(app.run_async())

        return 0

    except RecordLoadError as e:
        print(f"Failed to load replay: {e}")
        return 1
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


WEB_ONLY_ARGS: set[str] = {"--web", "--host", "--port", "--public-url"}


def build_terminal_command() -> str:
    """Reconstruct command from sys.argv, filtering out web-specific args."""
    base: list[str] = ["poetry", "run", "python", "run_poker_tui.py"]
    filtered: list[str] = []
    skip_next: bool = False

    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue

        if arg in WEB_ONLY_ARGS:
            if arg != "--web":
                skip_next = True
            continue

        if any(arg.startswith(f"{web_arg}=") for web_arg in WEB_ONLY_ARGS):
            continue

        filtered.append(arg)

    return " ".join(base + filtered)


def run_web_server(
    host: str, port: int, public_url: str | None = None
) -> None:
    from textual_serve.server import Server

    command: str = build_terminal_command()
    server: Server = Server(
        command,
        host=host,
        port=port,
        title="ClankerPoker Tournament Viewer",
        public_url=public_url,
    )

    location: str = public_url or f"http://{host}:{port}"
    print(f"Starting Poker Viewer at {location}")
    print("Press Ctrl+C to stop the server")
    server.serve()


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
        help="Maximum number of hands to run (useful for development/testing)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_EVENT_DELAY,
        help=f"Delay between events in seconds (default: {DEFAULT_EVENT_DELAY})",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Use bot players instead of LLM",
    )
    parser.add_argument(
        "--replay",
        type=Path,
        nargs="?",
        const=DEFAULT_REPLAY_PATH,
        help=f"Replay a recorded game (default: {DEFAULT_REPLAY_PATH})",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Serve TUI in web browser instead of terminal",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_WEB_HOST,
        help=f"Host for web server (default: {DEFAULT_WEB_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"Port for web server (default: {DEFAULT_WEB_PORT})",
    )
    parser.add_argument(
        "--public-url",
        type=str,
        default=None,
        help=(
            "Public base URL browsers use to reach the server, e.g. "
            "https://poker.example.com. Required behind a reverse "
            "proxy so the client websocket targets the public host "
            "rather than the internal bind address."
        ),
    )

    args: argparse.Namespace = parser.parse_args()

    web_arg_used: bool = any(
        arg in ("--host", "--port", "--public-url")
        or arg.startswith("--host=")
        or arg.startswith("--port=")
        or arg.startswith("--public-url=")
        for arg in sys.argv[1:]
    )
    if web_arg_used and not args.web:
        parser.error(
            "--host, --port, and --public-url require --web"
        )

    if args.replay and args.bot:
        parser.error("--replay and --bot are mutually exclusive")

    if args.web:
        run_web_server(
            host=args.host,
            port=args.port,
            public_url=args.public_url,
        )
    else:
        config: RuntimeConfig = _create_runtime_config(args)
        show_seed: bool = args.seed is not None or args.replay is not None

        exit_code: int = asyncio.run(
            run_with_tui(
                config=config,
                max_hands=args.max_hands,
                event_delay=args.delay,
                show_seed=show_seed,
            )
        )
        sys.exit(exit_code)


def _create_runtime_config(args: argparse.Namespace) -> RuntimeConfig:
    if args.replay:
        return RuntimeConfigFactory.for_replay(args.replay)
    if args.bot:
        return RuntimeConfigFactory.for_bot(seed=args.seed)
    return RuntimeConfigFactory.for_llm(seed=args.seed)


if __name__ == "__main__":
    main()
