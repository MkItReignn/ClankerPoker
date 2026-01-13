from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NewType

from src.domain.models.llm_model import LlmModel

BotId = NewType("BotId", str)
Prompt = NewType("Prompt", str)


class BotType(Enum):
    HOUSE = "house"
    USER = "user"


@dataclass(frozen=True, slots=True)
class Bot:
    id: BotId
    name: str
    bot_type: BotType
    llm_model: LlmModel
    system_prompt: Prompt
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Bot id cannot be empty")
        if not self.name.strip():
            raise ValueError("Bot name cannot be empty")
        if not self.system_prompt.strip():
            raise ValueError("System prompt cannot be empty")
