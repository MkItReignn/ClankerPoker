from __future__ import annotations


class SeparatorFormatter:
    @staticmethod
    def format_separator(text: str, width: int) -> str:
        """Format text with dashes and space padding around text."""
        text_padding = 2
        available_for_dashes = width - len(text) - (text_padding * 2)
        left_dashes = (available_for_dashes + 1) // 2
        right_dashes = available_for_dashes // 2
        return (
            "─" * left_dashes + " " * text_padding + text + " " * text_padding + "─" * right_dashes
        )
