from dataclasses import dataclass
from typing import Any, NewType, Self

NarrationText = NewType("NarrationText", str)


@dataclass(frozen=True, slots=True)
class Narration:
    """Single stream-of-consciousness thought process from an LLM poker player.

    The thought_process field contains the player's natural analysis of the hand,
    covering relevant factors from the decision framework in a conversational style.
    """

    thought_process: NarrationText

    def __post_init__(self) -> None:
        if not self.thought_process.strip():
            raise ValueError("thought_process cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert narration to dictionary for JSON serialization."""
        return {
            "thought_process": self.thought_process,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct narration from dictionary."""
        return cls(
            thought_process=NarrationText(data["thought_process"]),
        )


# Narration Field Specifications
#
# thought_process (200-500 words recommended, max 600 with tolerance)
#   Stream of consciousness analysis from an elite poker player's perspective.
#   Should cover relevant factors from the decision framework naturally:
#   - Game stage and tournament context
#   - Position and pot odds
#   - Opponent ranges and tendencies
#   - Equity assessment
#   - Bet sizing rationale (if applicable)
#   - Multi-street planning
#
#   Style: Conversational, analytical, uses full sentences and paragraphs.
#   Should read like a pro commentator breaking down a hand.
#   Avoids jargon - uses clear language accessible to non-poker players.
