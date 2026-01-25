"""Bot personality enum for bot player configuration."""

from enum import StrEnum


class BotPersonality(StrEnum):
    """Personality types for bot players.

    Maps directly to BotRandomActionSelector factory methods.
    """

    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    TIGHT = "tight"
    LOOSE = "loose"
    DEFAULT = "default"
