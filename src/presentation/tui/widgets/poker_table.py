from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from src.presentation.tui.player_registry import PlayerRegistry
from src.presentation.tui.widgets.card import CardRenderer
from src.presentation.tui.widgets.player_panel import (
    PlayerDisplayState,
    PlayerPanel,
)


class TableCenter(Static):

    DEFAULT_CSS = """
    TableCenter {
        overflow: hidden;
    }

    TableCenter Static {
        overflow: hidden;
    }
    """

    # init=False prevents watchers from firing before mount
    community_cards: reactive[list[dict[str, Any]]] = reactive(
        list, init=False
    )
    pot_total: reactive[int] = reactive(0, init=False)
    main_pot: reactive[int] = reactive(0, init=False)
    side_pots: reactive[list[int]] = reactive(list, init=False)

    def compose(self) -> ComposeResult:
        initial_cards = CardRenderer.format_community_cards([], total_slots=5)
        yield Static(initial_cards, id="community-cards")
        yield Static("[bold green]POT: 0[/bold green]", id="pot-display")
        yield Static(id="pot-breakdown")

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        if not self.is_mounted:
            return
        cards_widget = self.query_one("#community-cards", Static)
        pot_widget = self.query_one("#pot-display", Static)
        breakdown_widget = self.query_one("#pot-breakdown", Static)

        cards_str = CardRenderer.format_community_cards(
            list(self.community_cards), total_slots=5
        )
        cards_widget.update(cards_str)

        pot_widget.update(f"[bold green]POT: {self.pot_total:,}[/bold green]")

        breakdown_widget.update(self._format_pot_breakdown())

    def _format_pot_breakdown(self) -> str:
        items = [f"Main: {self.main_pot:,}"]
        items.extend(
            f"S{i + 1}: {pot:,}" for i, pot in enumerate(self.side_pots)
        )

        lines: list[str] = []
        for i in range(0, len(items), 4):
            chunk = items[i : i + 4]
            lines.append(" │ ".join(chunk))

        return "\n".join(lines)

    def update_from_game_state(self, game_state: dict[str, Any]) -> None:
        hand_state = game_state.get("hand_state", {})
        self.community_cards = hand_state.get("community_cards", [])

        pot_state = game_state.get("pot_state", {})
        self.pot_total = pot_state.get("total", 0)
        self.main_pot = pot_state.get("main_pot", {}).get("amount", 0)

        side_pot_list = pot_state.get("side_pots", [])
        self.side_pots = [
            sp.get("amount", 0)
            for sp in side_pot_list
            if sp.get("amount", 0) > 0
        ]

    def watch_community_cards(self, _: list[dict[str, Any]]) -> None:
        self._update_display()

    def watch_pot_total(self, _: int) -> None:
        self._update_display()

    def watch_side_pots(self, _: list[int]) -> None:
        self._update_display()


class PokerTableArea(Static):

    DEFAULT_CSS = """
    PokerTableArea {
        height: auto;
        width: 100%;
        padding: 1;
        overflow: hidden;
    }

    PokerTableArea Horizontal {
        width: 100%;
        overflow: hidden;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._player_panels: dict[int, PlayerPanel] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-players", classes="player-row"):
            for seat in [0, 1, 2]:
                panel = PlayerPanel(seat=seat, id=f"player-{seat}")
                self._player_panels[seat] = panel
                yield panel

        yield TableCenter(id="table-center")

        with Horizontal(id="bottom-players", classes="player-row"):
            for seat in [5, 4, 3]:
                panel = PlayerPanel(seat=seat, id=f"player-{seat}")
                self._player_panels[seat] = panel
                yield panel

    def get_player_panel(self, seat: int) -> PlayerPanel | None:
        return self._player_panels.get(seat)

    def get_table_center(self) -> TableCenter:
        return self.query_one("#table-center", TableCenter)

    def update_from_game_state(self, game_state: dict[str, Any]) -> None:
        players = game_state.get("players", [])
        PlayerRegistry.register_all(players)

        button_seat = game_state.get("button_seat", 0)
        sb_seat = game_state.get("sb_seat")
        bb_seat = game_state.get("bb_seat")
        player_to_act_id = game_state.get("player_to_act_id")

        player_by_seat: dict[int, dict[str, Any]] = {}
        for player in players:
            seat = player.get("seat", 0)
            player_by_seat[seat] = player

        for seat in range(6):
            panel = self._player_panels.get(seat)
            if panel is None:
                continue

            if seat in player_by_seat:
                player = player_by_seat[seat]
                state = PlayerDisplayState.from_player_dict(
                    player, button_seat, player_to_act_id, sb_seat, bb_seat
                )
                panel.update_state(state)
            else:
                panel.update_state(PlayerDisplayState.empty(seat))

        self.get_table_center().update_from_game_state(game_state)

    def set_winner(self, player_id: str) -> None:
        for panel in self._player_panels.values():
            panel.set_winner(panel.player_id == player_id)

    def clear_winner(self) -> None:
        for panel in self._player_panels.values():
            panel.set_winner(False)
