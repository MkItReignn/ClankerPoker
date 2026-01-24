from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from src.presentation.tui.formatters import SeparatorFormatter
from src.presentation.tui.player_registry import PlayerRegistry
from src.presentation.tui.theme import PlayerTheme
from src.presentation.tui.widgets.card import CardRenderer


class ActionLog(Static):
    HAND_SEPARATOR_WIDTH = 30
    PHASE_SEPARATOR_WIDTH = 40

    DEFAULT_CSS = """
    ActionLog {
        height: 100%;
        border: solid $primary;
    }

    ActionLog > VerticalScroll {
        height: 100%;
    }

    ActionLog .log-entry {
        padding: 0 1;
    }

    ActionLog .phase-separator {
        color: $text-muted;
        text-align: center;
    }

    ActionLog .hand-separator {
        color: $text;
        text-align: center;
    }

    ActionLog .showdown-separator {
        color: $warning;
        text-align: center;
    }

    ActionLog .winner-entry {
        color: $success;
    }

    ActionLog .thinking-entry {
        color: $primary;
    }

    ActionLog .community-cards {
        text-align: center;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: list[str] = []

    def _format_player_name(self, player_name: str, player_id: str | None = None) -> str:
        if player_id is None:
            return player_name
        seat = PlayerRegistry.get_seat(player_id)
        if seat is None:
            return player_name
        return PlayerTheme.format_name(player_name, seat)

    def compose(self) -> ComposeResult:
        yield Static("ACTION LOG", id="action-log-title")
        yield VerticalScroll(id="log-scroll")

    def _is_scrolled_to_bottom(self, scroll: VerticalScroll) -> bool:
        return scroll.scroll_y >= scroll.max_scroll_y - 1

    def add_entry(self, text: str, css_class: str = "log-entry") -> None:
        if not self.is_mounted:
            return
        self._entries.append(text)
        scroll = self.query_one("#log-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)
        entry = Static(text, classes=css_class)
        scroll.mount(entry)
        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_phase_separator(self, phase: str, cards: list[dict] | None = None) -> None:
        if not self.is_mounted:
            return

        scroll = self.query_one("#log-scroll", VerticalScroll)
        was_at_bottom = self._is_scrolled_to_bottom(scroll)

        phase_display = phase.upper().replace("_", "-")
        formatted = SeparatorFormatter.format_separator(phase_display, self.PHASE_SEPARATOR_WIDTH)
        css_class = "showdown-separator" if phase == "showdown" else "phase-separator"
        separator = Static(formatted, classes=css_class)
        scroll.mount(separator)

        if cards:
            card_str = CardRenderer.format_cards_rich(cards)
            cards_widget = Static(card_str, classes="community-cards")
            scroll.mount(cards_widget)

        if was_at_bottom:
            scroll.scroll_end(animate=False)

    def add_hand_started(self, hand_number: int, button_seat: int) -> None:
        text = f"HAND #{hand_number} START"
        formatted = SeparatorFormatter.format_separator(text, self.HAND_SEPARATOR_WIDTH)
        self.add_entry(formatted, "hand-separator")
        self.add_entry(f"Button: Seat {button_seat}")

    def add_blinds_posted(
        self,
        sb_name: str,
        sb_amount: int,
        bb_name: str,
        bb_amount: int,
        sb_player_id: str | None = None,
        bb_player_id: str | None = None,
    ) -> None:
        sb_display = self._format_player_name(sb_name, sb_player_id)
        bb_display = self._format_player_name(bb_name, bb_player_id)
        self.add_entry(f"{sb_display} posts small blind: {sb_amount}")
        self.add_entry(f"{bb_display} posts big blind: {bb_amount}")

    def add_action(
        self,
        player_name: str,
        action_type: str,
        amount: int | None = None,
        player_id: str | None = None,
    ) -> None:
        action_display: dict[str, str] = {
            "fold": "folds",
            "check": "checks",
            "call": "calls",
            "bet": "bets",
            "raise": "raises to",
            "all_in": "goes all-in:",
        }
        action_text = action_display.get(action_type, action_type)
        name_display = self._format_player_name(player_name, player_id)

        if amount is not None and action_type in ("bet", "raise", "all_in", "call"):
            if action_type == "call":
                self.add_entry(f"{name_display} calls {amount}")
            else:
                self.add_entry(f"{name_display} {action_text} {amount:,}")
        else:
            self.add_entry(f"{name_display} {action_text}")

    def add_thinking(self, player_name: str, player_id: str | None = None) -> None:
        name_display = self._format_player_name(player_name, player_id)
        self.add_entry(f"> [italic]{name_display} is thinking...[/italic]", "thinking-entry")

    def add_winner(
        self,
        player_name: str,
        amount: int,
        hand_description: str | None = None,
        player_id: str | None = None,
    ) -> None:
        name_display = self._format_player_name(player_name, player_id)
        if hand_description:
            self.add_entry(
                f"[bold green]{name_display} wins {amount:,} with {hand_description}[/bold green]",
                "winner-entry",
            )
        else:
            self.add_entry(
                f"[bold green]{name_display} wins {amount:,}[/bold green]",
                "winner-entry",
            )

    def add_showdown_result(
        self,
        player_name: str,
        hole_cards: list[dict],
        hand_description: str,
        is_winner: bool = False,
        player_id: str | None = None,
    ) -> None:
        name_display = self._format_player_name(player_name, player_id)
        cards_str = CardRenderer.format_cards_rich(hole_cards)
        winner_badge = " [bold yellow]★ WINNER[/bold yellow]" if is_winner else ""
        self.add_entry(f"{name_display}: {cards_str} - {hand_description}{winner_badge}")

    def add_elimination(
        self, player_name: str, position: int, player_id: str | None = None
    ) -> None:
        name_display = self._format_player_name(player_name, player_id)
        self.add_entry(f"[bold red]{name_display} eliminated (#{position})[/bold red]")

    def add_hand_complete(
        self,
        hand_number: int,
        winner_name: str,
        amount: int,
        hand_description: str | None = None,
        winner_id: str | None = None,
    ) -> None:
        text = f"HAND #{hand_number} COMPLETE"
        formatted = SeparatorFormatter.format_separator(text, self.HAND_SEPARATOR_WIDTH)
        self.add_entry(formatted, "hand-separator")
        name_display = self._format_player_name(winner_name, winner_id)
        if hand_description:
            self.add_entry(f"Winner: {name_display} (+{amount:,}) with {hand_description}")
        else:
            self.add_entry(f"Winner: {name_display} (+{amount:,})")

    def add_game_complete(
        self,
        winner_name: str,
        total_hands: int,
        final_standings: list[dict] | None = None,
        winner_id: str | None = None,
    ) -> None:
        self.add_entry("════════ TOURNAMENT COMPLETE ════════")
        winner_display = self._format_player_name(winner_name, winner_id)
        self.add_entry(f"[bold green]Winner: {winner_display}[/bold green]")
        self.add_entry(f"Total hands played: {total_hands}")

        if final_standings:
            self.add_entry("")
            self.add_entry("[bold]Final Standings:[/bold]")
            for standing in final_standings:
                position = standing.get("finish_position", 0)
                name = standing.get("player_name", "Unknown")
                player_id = standing.get("player_id")
                elim_hand = standing.get("elimination_hand")
                name_display = self._format_player_name(name, player_id)

                if position == 1:
                    self.add_entry(f"  [bold green]1st: {name_display} 🏆[/bold green]")
                elif elim_hand:
                    self.add_entry(
                        f"  {position}{self._ordinal_suffix(position)}: {name_display} (out Hand #{elim_hand})"
                    )
                else:
                    self.add_entry(f"  {position}{self._ordinal_suffix(position)}: {name_display}")

    @staticmethod
    def _ordinal_suffix(n: int) -> str:
        if 11 <= n % 100 <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    def clear_log(self) -> None:
        self._entries.clear()
        if self.is_mounted:
            scroll = self.query_one("#log-scroll", VerticalScroll)
            scroll.remove_children()
