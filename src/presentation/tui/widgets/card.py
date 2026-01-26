from typing import Any, ClassVar


class CardRenderer:
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
    def format_card_rich(cls, card_dict: dict[str, Any]) -> str:
        rank = card_dict["rank"]
        suit = card_dict["suit"]
        symbol = cls.SUIT_SYMBOLS.get(suit, "?")
        color = cls.SUIT_COLORS.get(suit, "white")
        return f"[{color}][{rank}{symbol}][/{color}]"

    @classmethod
    def format_cards_rich(cls, cards: list[dict[str, Any]]) -> str:
        return " ".join(cls.format_card_rich(card) for card in cards)

    @classmethod
    def format_community_cards(
        cls, cards: list[dict[str, Any]], total_slots: int = 5
    ) -> str:
        result: list[str] = []
        for i in range(total_slots):
            if i < len(cards):
                result.append(cls.format_card_rich(cards[i]))
            else:
                result.append("[dim][--][/dim]")
        return "  ".join(result)
