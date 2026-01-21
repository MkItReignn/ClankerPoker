"""Main poker response parser using strategy pattern."""

from __future__ import annotations

from src.application.poker.parser.action_parser import ActionParser, PokerActionParser
from src.application.poker.parser.narration_parser import (
    NarrationParser,
    ThoughtProcessNarrationParser,
)
from src.application.protocols.response import (
    ParseError,
    ParseFailure,
    ParseResult,
    ParseSuccess,
)
from src.domain.models.actions import Action, ActionType
from src.domain.models.available_action import (
    AvailableActions,
    AvailableCallAction,
    AvailableCheckAction,
)
from src.domain.models.narration import Narration


class PokerResponseParser:
    """Parses LLM responses into poker actions using strategy pattern.

    Composes parsing strategies to extract action and narration
    from LLM text output.

    Implements the ResponseParser protocol for poker.
    """

    def __init__(
        self,
        action_parser: ActionParser | None = None,
        narration_parser: NarrationParser | None = None,
    ) -> None:
        self._action_parser: ActionParser = action_parser or PokerActionParser()
        self._narration_parser: NarrationParser = (
            narration_parser or ThoughtProcessNarrationParser()
        )

    def parse_response(
        self,
        response_text: str,
        available_actions: list[AvailableActions],
    ) -> ParseResult[Action, Narration]:
        # Parse action (critical - failure blocks game progress)
        action_result: Action | ParseError = self._action_parser.parse(
            response_text, available_actions
        )
        if isinstance(action_result, ParseError):
            return ParseFailure(error=action_result)

        # Type checker knows action_result is Action here
        action: Action = action_result

        # Parse narration (non-critical - return error object as-is)
        narration_result: Narration | ParseError = self._narration_parser.parse(response_text)

        return ParseSuccess(
            action=action,
            narration=narration_result,
        )

    def get_fallback_action(
        self,
        available_actions: list[AvailableActions],
    ) -> Action | None:
        """Get a safe fallback action when parsing fails.

        Prefers check/call over fold to avoid throwing away hands
        due to parsing errors.

        Args:
            available_actions: The available actions.

        Returns:
            A safe fallback Action, or None if no actions available.
        """
        if not available_actions:
            return None

        # Priority: check > call > fold
        for action in available_actions:
            if isinstance(action, AvailableCheckAction):
                return Action(action_type=ActionType.CHECK)

        for action in available_actions:
            if isinstance(action, AvailableCallAction):
                return Action(action_type=ActionType.CALL)

        return Action(action_type=ActionType.FOLD)
