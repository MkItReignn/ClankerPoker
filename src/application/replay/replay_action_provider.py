from collections import deque
from typing import Self

from src.application.poker.context import PokerDecisionContext
from src.application.poker.records.models import GameRecord, TurnRecord
from src.application.protocols.player import PlayerConfig
from src.application.protocols.response import ActionResponse
from src.domain.models.actions import Action
from src.domain.models.available_action import AvailableActions
from src.domain.models.narration import Narration


class ReplayActionProvider:
    def __init__(self, record: GameRecord) -> None:
        self._action_queue: deque[tuple[Action, Narration | None]] = (
            self._build_action_queue(record)
        )
        self._total_actions: int = len(self._action_queue)

    def _build_action_queue(
        self, record: GameRecord
    ) -> deque[tuple[Action, Narration | None]]:
        actions: deque[tuple[Action, Narration | None]] = deque()

        for hand in record.completed_hands:
            for round_record in hand.rounds:
                for turn in round_record.turns:
                    if self._is_blind_action(turn):
                        continue

                    action = self._convert_to_action(turn)
                    actions.append((action, turn.narration))

        return actions

    def _is_blind_action(self, turn: TurnRecord) -> bool:
        return turn.action.action_type.is_blind_action

    def _convert_to_action(self, turn: TurnRecord) -> Action:
        return Action(
            action_type=turn.action.action_type,
            amount=turn.action.amount,
        )

    @property
    def remaining_actions(self) -> int:
        return len(self._action_queue)

    @property
    def actions_played(self) -> int:
        return self._total_actions - len(self._action_queue)

    async def get_action(
        self,
        context: PokerDecisionContext,
        available_actions: list[AvailableActions],
        config: PlayerConfig,
    ) -> ActionResponse[Action, Narration]:
        if not self._action_queue:
            raise RuntimeError(
                f"Replay exhausted: no more recorded actions. "
                f"Played {self._total_actions} actions total. "
                f"Expected action for player '{config.player_id}'."
            )

        action, narration = self._action_queue.popleft()
        return ActionResponse(action=action, narration=narration)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass
