from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from src.presentation.tui.formatters import SeparatorFormatter
from src.presentation.tui.player_registry import PlayerRegistry
from src.presentation.tui.theme import PlayerTheme
from src.presentation.tui.widgets.card import CardRenderer


class NarrationPanel(Static):
    HAND_SEPARATOR_WIDTH = 40
    PHASE_SEPARATOR_WIDTH = 50

    DEFAULT_CSS = """
    NarrationPanel {
        width: 100%;
        height: 100%;
        border: solid $primary;
    }

    NarrationPanel > VerticalScroll {
        height: 100%;
    }

    NarrationPanel .phase-header {
        color: $text-muted;
        text-align: center;
        margin-top: 1;
        margin-bottom: 1;
    }

    NarrationPanel .showdown-header {
        color: $warning;
        text-align: center;
        margin-top: 1;
        margin-bottom: 1;
    }

    NarrationPanel .hand-header {
        color: $text;
        text-align: center;
        margin-top: 1;
        margin-bottom: 1;
    }

    NarrationPanel .community-cards {
        text-align: center;
        margin-bottom: 1;
    }

    NarrationPanel .player-thinking {
        color: $primary;
        margin-top: 1;
    }

    NarrationPanel .thought-process {
        padding: 0 1;
        color: $text;
        margin-bottom: 1;
        width: 100%;
    }
    """

    # init=False prevents watchers from firing before mount
    current_phase: reactive[str] = reactive("pre_flop", init=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._last_phase: str = ""

    def _format_player_name(
        self, player_name: str, player_id: str | None = None
    ) -> str:
        if player_id is None:
            return player_name
        seat = PlayerRegistry.get_seat(player_id)
        if seat is None:
            return player_name
        return PlayerTheme.format_name_italic(player_name, seat)

    def compose(self) -> ComposeResult:
        yield Static("NARRATION", id="narration-title")
        yield VerticalScroll(id="narration-scroll")

    def _is_scrolled_to_bottom(self, scroll: VerticalScroll) -> bool:
        return scroll.scroll_y >= scroll.max_scroll_y - 1

    def add_hand_started(self, hand_number: int) -> None:
        if not self.is_mounted:
            return
        scroll = self.query_one("#narration-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)

        text = f"HAND #{hand_number} START"
        formatted = SeparatorFormatter.format_separator(
            text, self.HAND_SEPARATOR_WIDTH
        )
        header = Static(formatted, classes="hand-header")
        scroll.mount(header)

        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_hand_completed(self, hand_number: int) -> None:
        if not self.is_mounted:
            return
        scroll = self.query_one("#narration-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)

        text = f"HAND #{hand_number} COMPLETE"
        formatted = SeparatorFormatter.format_separator(
            text, self.HAND_SEPARATOR_WIDTH
        )
        header = Static(formatted, classes="hand-header")
        scroll.mount(header)

        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_phase_header(
        self, phase: str, community_cards: list[dict] | None = None
    ) -> None:
        if not self.is_mounted:
            return
        if phase == self._last_phase:
            return

        self._last_phase = phase
        scroll = self.query_one("#narration-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)

        phase_display = phase.upper().replace("_", "-")
        formatted = SeparatorFormatter.format_separator(
            phase_display, self.PHASE_SEPARATOR_WIDTH
        )
        css_class = (
            "showdown-header" if phase == "showdown" else "phase-header"
        )
        header = Static(formatted, classes=css_class)
        scroll.mount(header)

        if community_cards:
            cards_str = CardRenderer.format_cards_rich(community_cards)
            cards_widget = Static(cards_str, classes="community-cards")
            scroll.mount(cards_widget)

        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_thinking(
        self, player_name: str, player_id: str | None = None
    ) -> None:
        if not self.is_mounted:
            return
        scroll = self.query_one("#narration-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)
        name_display = self._format_player_name(player_name, player_id)
        thinking = Static(
            f"{name_display} is analyzing...", classes="player-thinking"
        )
        scroll.mount(thinking)
        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_thought_process(
        self,
        player_name: str,
        thought_process: str,
        player_id: str | None = None,
    ) -> None:
        if not self.is_mounted:
            return
        scroll = self.query_one("#narration-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)

        for child in scroll.children:
            if isinstance(child, Static) and "is analyzing..." in str(
                child.renderable
            ):
                child.remove()
                break

        formatted_thought = self._format_thought_process(thought_process)
        name_display = self._format_player_name(player_name, player_id)
        player_header = Static(name_display, classes="player-thinking")
        thought_widget = Static(formatted_thought, classes="thought-process")

        scroll.mount(player_header)
        scroll.mount(thought_widget)
        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def _format_thought_process(self, thought: str) -> str:
        lines = thought.strip().split("\n")
        formatted_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped:
                formatted_lines.append(f'"{stripped}"')

        return "\n".join(formatted_lines)

    def clear_panel(self) -> None:
        self._last_phase = ""
        if self.is_mounted:
            scroll = self.query_one("#narration-scroll", VerticalScroll)
            scroll.remove_children()
