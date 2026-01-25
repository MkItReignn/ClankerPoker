from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize

from src.presentation.tui.event_handler import EventHandler
from src.presentation.tui.widgets.action_log import ActionLog
from src.presentation.tui.widgets.header_bar import HeaderBar
from src.presentation.tui.widgets.key_hints_bar import KeyHintsBar
from src.presentation.tui.widgets.narration_panel import NarrationPanel
from src.presentation.tui.widgets.poker_table import PokerTableArea

if TYPE_CHECKING:
    from src.application.poker.events import PublishedEvent


class ColumnLayoutConfig:
    LEFT_MAX_WIDTH = 110
    RIGHT_MAX_WIDTH = 80
    PHASE_1_THRESHOLD = 165  # 2:1 ratio until left would hit max (110 * 3/2)
    PHASE_2_THRESHOLD = 190  # LEFT_MAX + RIGHT_MAX


class PokerViewerApp(App[None]):

    TITLE = "Poker Tournament Viewer"
    CSS_PATH = Path(__file__).parent / "styles" / "poker.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("space", "toggle_pause", "Pause/Resume", show=True),
        Binding("up", "scroll_log_up", "Scroll Up", show=False),
        Binding("down", "scroll_log_down", "Scroll Down", show=False),
        Binding("pageup", "scroll_narration_up", "Page Up", show=False),
        Binding("pagedown", "scroll_narration_down", "Page Down", show=False),
    ]

    def __init__(
        self,
        queue: asyncio.Queue[PublishedEvent | None],
        event_delay: float = 0.3,
        show_seed: bool = False,
        seed: int | None = None,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        super().__init__()
        self._queue = queue
        self._event_delay = event_delay
        self._show_seed = show_seed
        self._seed = seed
        self._shutdown_event = shutdown_event
        self._paused = False
        self._event_handler: EventHandler | None = None

    def compose(self) -> ComposeResult:
        yield KeyHintsBar(id="key-hints")
        with Horizontal(id="main-container"):
            with Vertical(id="left-column"):
                yield HeaderBar(
                    show_seed=self._show_seed, seed=self._seed, id="header"
                )
                yield PokerTableArea(id="poker-table")
                yield NarrationPanel(id="narration-panel")
            with Vertical(id="right-column"):
                yield ActionLog(id="action-log")

    def on_mount(self) -> None:
        header = self.query_one("#header", HeaderBar)
        table = self.query_one("#poker-table", PokerTableArea)
        action_log = self.query_one("#action-log", ActionLog)
        narration = self.query_one("#narration-panel", NarrationPanel)

        self._event_handler = EventHandler(
            header, table, action_log, narration
        )
        self.run_worker(self._consume_events(), exclusive=True)
        self._apply_column_layout(self.size.width)

    def on_resize(self, event: Resize) -> None:
        self._apply_column_layout(event.size.width)

    def _apply_column_layout(self, terminal_width: int) -> None:
        left_column = self.query_one("#left-column")
        right_column = self.query_one("#right-column")
        cfg = ColumnLayoutConfig

        if terminal_width <= cfg.PHASE_1_THRESHOLD:
            left_width = (terminal_width * 2) // 3
            right_width = terminal_width - left_width
        elif terminal_width <= cfg.PHASE_2_THRESHOLD:
            left_width = cfg.LEFT_MAX_WIDTH
            right_width = terminal_width - cfg.LEFT_MAX_WIDTH
        else:
            extra = terminal_width - cfg.PHASE_2_THRESHOLD
            left_width = cfg.LEFT_MAX_WIDTH + (extra * 2) // 3
            right_width = cfg.RIGHT_MAX_WIDTH + extra - (extra * 2) // 3

        left_column.styles.width = left_width
        right_column.styles.width = right_width

    async def _consume_events(self) -> None:
        while True:
            event = await self._queue.get()

            if event is None:
                break

            while self._paused:
                await asyncio.sleep(0.1)

            if self._event_handler:
                await self._event_handler.handle_event(event)

            await asyncio.sleep(self._event_delay)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        status = "PAUSED" if self._paused else "RUNNING"
        self.notify(f"Tournament {status}", timeout=1)

    def action_scroll_log_up(self) -> None:
        action_log = self.query_one("#action-log", ActionLog)
        scroll = action_log.query_one("#log-scroll")
        scroll.scroll_up()

    def action_scroll_log_down(self) -> None:
        action_log = self.query_one("#action-log", ActionLog)
        scroll = action_log.query_one("#log-scroll")
        scroll.scroll_down()

    def action_scroll_narration_up(self) -> None:
        narration = self.query_one("#narration-panel", NarrationPanel)
        scroll = narration.query_one("#narration-scroll")
        scroll.scroll_page_up()

    def action_scroll_narration_down(self) -> None:
        narration = self.query_one("#narration-panel", NarrationPanel)
        scroll = narration.query_one("#narration-scroll")
        scroll.scroll_page_down()

    async def action_quit(self) -> None:
        if self._shutdown_event:
            self._shutdown_event.set()
        await super().action_quit()
