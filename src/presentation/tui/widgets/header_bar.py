from typing import Any

from textual.reactive import reactive
from textual.widgets import Static


class HeaderBar(Static):
    """Header bar displaying game info: hand number, blinds, phase, player count, seed."""

    # init=False prevents watchers from firing before mount
    hand_number: reactive[int] = reactive(1, init=False)
    small_blind: reactive[int] = reactive(0, init=False)
    big_blind: reactive[int] = reactive(0, init=False)
    phase: reactive[str] = reactive("PRE-FLOP", init=False)
    active_players: reactive[int] = reactive(0, init=False)
    total_players: reactive[int] = reactive(6, init=False)
    seed: reactive[int | None] = reactive(None, init=False)
    show_seed: reactive[bool] = reactive(False, init=False)

    def __init__(
        self,
        show_seed: bool = False,
        seed: int | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.show_seed = show_seed
        self.seed = seed

    def on_mount(self) -> None:
        self._update_display()

    def _format_phase(self, phase: str) -> str:
        phase_display: dict[str, str] = {
            "pre_flop": "PRE-FLOP",
            "flop": "FLOP",
            "turn": "TURN",
            "river": "RIVER",
            "showdown": "SHOWDOWN",
        }
        return phase_display.get(phase.lower(), phase.upper())

    def _update_display(self) -> None:
        phase_display = self._format_phase(self.phase)

        parts = [
            f"Hand #{self.hand_number}",
            f"Blinds: {self.small_blind}/{self.big_blind}",
            f"[bold]{phase_display}[/bold]",
            f"Players: {self.active_players}/{self.total_players}",
        ]

        if self.show_seed and self.seed is not None:
            parts.append(f"Seed: {self.seed}")

        self.update(" │ ".join(parts))

    def watch_hand_number(self, _: int) -> None:
        self._update_display()

    def watch_small_blind(self, _: int) -> None:
        self._update_display()

    def watch_big_blind(self, _: int) -> None:
        self._update_display()

    def watch_phase(self, _: str) -> None:
        self._update_display()

    def watch_active_players(self, _: int) -> None:
        self._update_display()

    def watch_total_players(self, _: int) -> None:
        self._update_display()

    def update_from_game_state(self, game_state: dict[str, Any]) -> None:
        self.hand_number = game_state.get("hand_state", {}).get(
            "hand_number", 1
        )
        self.phase = game_state.get("hand_state", {}).get(
            "current_phase", "pre_flop"
        )

        blind_level = game_state.get("blind_level", {})
        self.small_blind = blind_level.get("small_blind", 0)
        self.big_blind = blind_level.get("big_blind", 0)

        players = game_state.get("players", [])
        self.total_players = len(players)
        self.active_players = sum(
            1 for p in players if p.get("participation_status") != "eliminated"
        )
