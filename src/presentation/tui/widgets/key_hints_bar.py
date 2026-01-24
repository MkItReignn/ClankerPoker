from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class KeyHintsBar(Static):

    DEFAULT_CSS = """
    KeyHintsBar {
        dock: bottom;
        height: 1;
        width: 100%;
        background: $primary-darken-3;
        color: $text;
        padding: 0;
    }

    #hints-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
        align: center middle;
    }

    .hint {
        width: 1fr;
        text-align: center;
    }
    """

    HINTS: ClassVar[list[tuple[str, str]]] = [
        ("q", "Quit"),
        ("space", "Pause/Resume"),
        ("↑/↓", "Scroll Log"),
        ("PgUp/PgDn", "Scroll Narration"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="hints-container"):
            for key, desc in self.HINTS:
                yield Static(f"[bold]{key}[/bold]: {desc}", classes="hint")
