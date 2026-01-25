from dataclasses import dataclass
from typing import Any, Self

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

from src.presentation.tui.theme import PlayerTheme
from src.presentation.tui.widgets.card import CardRenderer


@dataclass
class PlayerDisplayState:
    player_id: str
    name: str
    chips: int
    hole_cards: list[dict[str, Any]] | None
    current_bet: int
    is_dealer: bool
    is_small_blind: bool
    is_big_blind: bool
    is_active: bool
    is_folded: bool
    is_all_in: bool
    is_eliminated: bool
    seat: int

    @classmethod
    def empty(cls, seat: int) -> Self:
        return cls(
            player_id="",
            name="Empty",
            chips=0,
            hole_cards=None,
            current_bet=0,
            is_dealer=False,
            is_small_blind=False,
            is_big_blind=False,
            is_active=False,
            is_folded=False,
            is_all_in=False,
            is_eliminated=True,
            seat=seat,
        )

    @classmethod
    def from_player_dict(
        cls,
        player: dict[str, Any],
        button_seat: int,
        player_to_act_id: str | None,
        sb_seat: int | None = None,
        bb_seat: int | None = None,
    ) -> Self:
        seat = player.get("seat", 0)
        participation = player.get("participation_status", "in_hand")

        return cls(
            player_id=player.get("id", ""),
            name=player.get("name", "Unknown"),
            chips=player.get("remaining_chips", 0),
            hole_cards=player.get("hole_cards"),
            current_bet=player.get("total_invested_this_hand", 0),
            is_dealer=(seat == button_seat),
            is_small_blind=(seat == sb_seat),
            is_big_blind=(seat == bb_seat),
            is_active=(player.get("id") == player_to_act_id),
            is_folded=(participation == "folded"),
            is_all_in=player.get("is_all_in", False),
            is_eliminated=(participation == "eliminated"),
            seat=seat,
        )


class PlayerPanel(Static):

    DEFAULT_CSS = """
    PlayerPanel {
        width: 22;
        height: 5;
        border: solid $primary;
        padding: 0 1;
    }

    PlayerPanel.player-active {
        border: heavy $warning;
    }

    PlayerPanel.player-folded {
        opacity: 0.7;
        border: round #5588bb;
        background: #5588bb 70%;
    }

    PlayerPanel.player-eliminated {
        opacity: 0.3;
        border: dashed $error;
    }

    PlayerPanel.player-all-in {
        border: solid $accent;
    }

    PlayerPanel.player-winner {
        border: double $success;
    }

    PlayerPanel .player-name {
        text-style: bold;
    }

    PlayerPanel .dealer-badge {
        color: $warning;
    }

    PlayerPanel .active-indicator {
        color: $warning;
    }
    """

    # init=False prevents watchers from firing before mount
    player_id: reactive[str] = reactive("", init=False)
    player_name: reactive[str] = reactive("", init=False)
    chips: reactive[int] = reactive(0, init=False)
    current_bet: reactive[int] = reactive(0, init=False)
    is_dealer: reactive[bool] = reactive(False, init=False)
    is_small_blind: reactive[bool] = reactive(False, init=False)
    is_big_blind: reactive[bool] = reactive(False, init=False)
    is_active: reactive[bool] = reactive(False, init=False)
    is_folded: reactive[bool] = reactive(False, init=False)
    is_all_in: reactive[bool] = reactive(False, init=False)
    is_eliminated: reactive[bool] = reactive(False, init=False)
    is_winner: reactive[bool] = reactive(False, init=False)
    seat: reactive[int] = reactive(0, init=False)

    def __init__(self, seat: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.seat = seat
        self._hole_cards: list[dict[str, Any]] | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="player-line1")
        yield Static(id="player-line2")
        yield Static(id="player-line3")

    def on_mount(self) -> None:
        self._update_display()

    def update_state(self, state: PlayerDisplayState) -> None:
        self.player_id = state.player_id
        self.player_name = state.name
        self.chips = state.chips
        self._hole_cards = state.hole_cards
        self.current_bet = state.current_bet
        self.is_dealer = state.is_dealer
        self.is_small_blind = state.is_small_blind
        self.is_big_blind = state.is_big_blind
        self.is_active = state.is_active
        self.is_folded = state.is_folded
        self.is_all_in = state.is_all_in
        self.is_eliminated = state.is_eliminated
        self._update_display()
        self._update_classes()

    def set_winner(self, is_winner: bool) -> None:
        self.is_winner = is_winner
        self._update_classes()

    def _update_classes(self) -> None:
        if not self.is_mounted:
            return

        self.remove_class(
            "player-active",
            "player-folded",
            "player-eliminated",
            "player-all-in",
            "player-winner",
        )

        if self.is_winner:
            self.add_class("player-winner")
        elif self.is_eliminated:
            self.add_class("player-eliminated")
        elif self.is_folded:
            self.add_class("player-folded")
        elif self.is_all_in:
            self.add_class("player-all-in")
        elif self.is_active:
            self.add_class("player-active")

    def _build_badges(self) -> str:
        badges: list[str] = []
        if self.is_dealer:
            badges.append("[yellow]Ⓓ[/yellow]")
        if self.is_small_blind:
            badges.append("[#87d7af bold]SB[/#87d7af bold]")
        if self.is_big_blind:
            badges.append("[#FF7F50 bold]BB[/#FF7F50 bold]")
        if self.is_active:
            badges.append("[yellow]◀[/yellow]")
        return " ".join(badges)

    def _build_cards_display(self) -> str:
        if self._hole_cards:
            return CardRenderer.format_cards_rich(self._hole_cards)
        if self.is_folded:
            return "[dim]FOLDED[/dim]"
        return "--"

    def _build_bet_display(self) -> str:
        if self.is_all_in:
            return f"[cyan]ALL-IN: {self.current_bet:,}[/cyan]"
        if self.current_bet > 0:
            return f"Bet: {self.current_bet:,}"
        return ""

    def _update_display(self) -> None:
        if not self.is_mounted:
            return

        line1 = self.query_one("#player-line1", Static)
        line2 = self.query_one("#player-line2", Static)
        line3 = self.query_one("#player-line3", Static)

        if self.is_eliminated:
            seat_color = PlayerTheme.get_color(self.seat)
            line1.update(
                f"[dim {seat_color}]{self.player_name}[/dim {seat_color}]"
            )
            line2.update("[dim]ELIMINATED[/dim]")
            line3.update("[dim]--[/dim]")
            return

        seat_color = PlayerTheme.get_color(self.seat)
        badge_str = self._build_badges()
        name_with_color = (
            f"[{seat_color} bold]{self.player_name}[/{seat_color} bold]"
        )
        name_display = (
            f"{name_with_color} {badge_str}" if badge_str else name_with_color
        )

        line1.update(name_display)
        line2.update(f"{self.chips:,}  {self._build_cards_display()}")
        line3.update(self._build_bet_display())

    def watch_player_name(self, _: str) -> None:
        self._update_display()

    def watch_chips(self, _: int) -> None:
        self._update_display()

    def watch_current_bet(self, _: int) -> None:
        self._update_display()

    def watch_is_dealer(self, _: bool) -> None:
        self._update_display()

    def watch_is_active(self, active: bool) -> None:
        self._update_display()
        self._update_classes()

    def watch_is_folded(self, _: bool) -> None:
        self._update_display()
        self._update_classes()

    def watch_is_all_in(self, _: bool) -> None:
        self._update_display()
        self._update_classes()

    def watch_is_eliminated(self, _: bool) -> None:
        self._update_display()
        self._update_classes()
