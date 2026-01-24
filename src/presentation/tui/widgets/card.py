from __future__ import annotations

from typing import Any, ClassVar


class CardRenderer:
    """Utilities for rendering playing cards in the TUI."""

    SUIT_SYMBOLS: ClassVar[dict[str, str]] = {
        "hearts": "♥",
        "diamonds": "♦",
        "clubs": "♣",
        "spades": "♠",
    }

    SUIT_COLORS: ClassVar[dict[str, str]] = {
        "hearts": "red",
        "diamonds": "red",
        "clubs": "white",
        "spades": "white",
    }

    @classmethod
    def format_card(cls, card_dict: dict[str, Any]) -> str:
        """Format a single card as [R♠] style string."""
        rank = card_dict["rank"]
        suit = card_dict["suit"]
        symbol = cls.SUIT_SYMBOLS.get(suit, "?")
        return f"[{rank}{symbol}]"

    @classmethod
    def format_cards(cls, cards: list[dict[str, Any]]) -> str:
        """Format multiple cards as [R♠] [R♥] style string."""
        return " ".join(cls.format_card(card) for card in cards)

    @classmethod
    def format_card_rich(cls, card_dict: dict[str, Any]) -> str:
        """Format card with Rich markup for colored suits."""
        rank = card_dict["rank"]
        suit = card_dict["suit"]
        symbol = cls.SUIT_SYMBOLS.get(suit, "?")
        color = cls.SUIT_COLORS.get(suit, "white")
        return f"[{color}][{rank}{symbol}][/{color}]"

    @classmethod
    def format_cards_rich(cls, cards: list[dict[str, Any]]) -> str:
        """Format multiple cards with Rich markup."""
        return " ".join(cls.format_card_rich(card) for card in cards)

    @classmethod
    def format_community_cards(cls, cards: list[dict[str, Any]], total_slots: int = 5) -> str:
        """Format community cards with empty slots for undealt cards."""
        result: list[str] = []
        for i in range(total_slots):
            if i < len(cards):
                result.append(cls.format_card_rich(cards[i]))
            else:
                result.append("[dim][--][/dim]")
        return "  ".join(result)

    @classmethod
    def empty_card(cls) -> str:
        """Return representation of an empty card slot."""
        return "[--]"

    @classmethod
    def face_down_card(cls) -> str:
        """Return representation of a face-down card."""
        return "[??]"
