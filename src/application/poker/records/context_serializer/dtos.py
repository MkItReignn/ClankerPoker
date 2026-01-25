from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.models.actions import ActionType
from src.domain.models.chips import ChipAmount
from src.domain.models.game import HandPhase
from src.domain.models.hand import Hand
from src.domain.models.position import PositionName

if TYPE_CHECKING:
    from src.application.poker.records.models import (
        GameRecord,
        HandLevelPlayerRecord,
        HandRecord,
        RoundRecord,
        TurnRecord,
    )


@dataclass(frozen=True, slots=True)
class TurnDto:
    """A player's turn/action for LLM context.

    Example serialized output:
        - "Alice(BTN):R150" (raise to 150)
        - "Bob(SB):C" (call)
        - "you(BB):F" (fold, viewer perspective)
    """

    name: str
    position: PositionName
    action_type: ActionType
    amount: ChipAmount | None

    @classmethod
    def from_turn_record(
        cls,
        turn: TurnRecord,
        hand: HandRecord,
        viewer_id: str | None = None,
    ) -> TurnDto:
        action = turn.action
        player_record = hand.player_records.get(action.player_id)
        if player_record is None:
            raise ValueError(
                f"Player {action.player_id} not found in hand records"
            )
        if player_record.position is None:
            raise ValueError(f"Player {action.player_id} has no position")

        name = (
            "you"
            if viewer_id and action.player_id == viewer_id
            else action.player_name
        )
        return cls(
            name=name,
            position=player_record.position,
            action_type=action.action_type,
            amount=action.amount,
        )

    def serialize(self) -> str:
        pos_str = f"({self.position.to_short_string()})"
        action_str = self.action_type.to_short_string()
        if self.amount is not None and self.action_type in (
            ActionType.BET,
            ActionType.RAISE,
            ActionType.ALL_IN,
            ActionType.POST_SMALL_BLIND,
            ActionType.POST_BIG_BLIND,
        ):
            action_str = f"{action_str}{self.amount.value}"
        return f"{self.name}{pos_str}:{action_str}"


@dataclass(frozen=True, slots=True)
class PlayerDto:
    """A player's stack for LLM context.

    Example serialized output:
        - "Alice(BTN)=1500"
        - "you(SB)=980"
    """

    name: str
    position: PositionName
    stack: ChipAmount

    @classmethod
    def from_player_record(
        cls,
        player_record: HandLevelPlayerRecord,
        viewer_id: str | None = None,
    ) -> PlayerDto:
        if player_record.position is None:
            raise ValueError(
                f"Player {player_record.player_id} has no position"
            )

        name = (
            "you"
            if viewer_id and player_record.player_id == viewer_id
            else player_record.player_name
        )
        return cls(
            name=name,
            position=player_record.position,
            stack=player_record.starting_chips,
        )

    def serialize(self) -> str:
        pos_str = f"({self.position.to_short_string()})"
        return f"{self.name}{pos_str}={self.stack.value}"


@dataclass(frozen=True, slots=True)
class RoundDto:
    """A betting round for LLM context.

    Example serialized output:
        - "PREFLOP: Alice(BTN):R150, Bob(SB):C"
        - "FLOP: ?" (current phase with no actions yet)
    """

    phase: HandPhase
    turns: tuple[TurnDto, ...]
    is_current_phase: bool = False

    @classmethod
    def from_round_record(
        cls,
        round_record: RoundRecord,
        hand: HandRecord,
        viewer_id: str | None = None,
        is_current: bool = False,
    ) -> RoundDto:
        turns = tuple(
            TurnDto.from_turn_record(turn, hand, viewer_id)
            for turn in round_record.turns
        )
        return cls(
            phase=round_record.phase,
            turns=turns,
            is_current_phase=is_current,
        )

    def serialize(self) -> str:
        phase_name = self.phase.value.upper()
        if not self.turns:
            return (
                f"{phase_name}: ?"
                if self.is_current_phase
                else f"{phase_name}:"
            )
        actions_str = ", ".join(turn.serialize() for turn in self.turns)
        if self.is_current_phase:
            actions_str += ", ?"
        return f"{phase_name}: {actions_str}"


@dataclass(frozen=True, slots=True)
class HandDto:
    """A complete hand for LLM context.

    Example serialized output:
        H1: Winner=Alice, Pot=300, Showdown=no
          Stacks: Alice(BTN)=1500, Bob(SB)=980
          PREFLOP: Alice(BTN):R150, Bob(SB):C
    """

    hand_number: int
    player_stacks: tuple[PlayerDto, ...]
    rounds: tuple[RoundDto, ...]
    winner_names: tuple[str, ...] | None
    pot: ChipAmount | None
    was_showdown: bool
    shown_hands: tuple[tuple[str, Hand], ...]

    @classmethod
    def from_hand_record(
        cls,
        hand: HandRecord,
        viewer_id: str | None = None,
    ) -> HandDto:
        stacks = tuple(
            PlayerDto.from_player_record(pr, viewer_id)
            for pr in hand.player_records.values()
        )
        rounds = tuple(
            RoundDto.from_round_record(r, hand, viewer_id) for r in hand.rounds
        )

        winner_names: tuple[str, ...] | None = None
        pot: ChipAmount | None = None
        was_showdown = False
        shown_hands: tuple[tuple[str, Hand], ...] = ()

        if hand.outcome is not None:
            outcome = hand.outcome

            winner_name_list: list[str] = []
            for winner in outcome.winners:
                if viewer_id and winner.player_id == viewer_id:
                    winner_name_list.append("you")
                else:
                    winner_name_list.append(winner.player_name)
            winner_names = tuple(winner_name_list)

            pot = outcome.pot_amount
            was_showdown = outcome.showdown is not None

            if was_showdown and outcome.showdown:
                shown_hands = tuple(
                    (
                        (
                            "you"
                            if viewer_id
                            and showdown_result.player_id == viewer_id
                            else showdown_result.player_name
                        ),
                        showdown_result.hole_cards,
                    )
                    for showdown_result in outcome.showdown
                )

        return cls(
            hand_number=hand.hand_number,
            player_stacks=stacks,
            rounds=rounds,
            winner_names=winner_names,
            pot=pot,
            was_showdown=was_showdown,
            shown_hands=shown_hands,
        )

    def _serialize_summary(self) -> str:
        if self.winner_names is None or self.pot is None:
            return f"H{self.hand_number}: (incomplete)"

        winners_str = ",".join(self.winner_names)
        showdown_str = "yes" if self.was_showdown else "no"
        summary = f"H{self.hand_number}: Winner={winners_str}, Pot={self.pot.value}, Showdown={showdown_str}"
        if self.was_showdown and self.shown_hands:
            shown_str = "; ".join(
                f"{name} showed {cards}" for name, cards in self.shown_hands
            )
            summary += f", {shown_str}"
        return summary

    def _serialize_stacks(self) -> str:
        stacks_str = ", ".join(ps.serialize() for ps in self.player_stacks)
        return f"  Stacks: {stacks_str}"

    def serialize(self) -> str:
        lines = [self._serialize_summary(), self._serialize_stacks()]
        for round_dto in self.rounds:
            phase_name = round_dto.phase.value.upper()
            if round_dto.turns:
                actions_str = ", ".join(
                    turn.serialize() for turn in round_dto.turns
                )
                lines.append(f"  {phase_name}: {actions_str}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class PreviousHandsDto:
    """Previous hands for LLM context.

    Example serialized output:
        === PREVIOUS HANDS ===
        H1: Winner=Alice, Pot=300, Showdown=no
          Stacks: ...
          PREFLOP: ...
    """

    hands: tuple[HandDto, ...]

    @classmethod
    def from_game_record(
        cls,
        record: GameRecord,
        viewer_id: str | None = None,
        max_hands: int = 5,
    ) -> PreviousHandsDto:
        recent = record.get_last_hand_records(max_hands)
        hands = tuple(HandDto.from_hand_record(h, viewer_id) for h in recent)
        return cls(hands=hands)

    def serialize(self) -> str:
        if not self.hands:
            return ""
        lines = ["=== PREVIOUS HANDS ==="]
        lines.extend(hand.serialize() for hand in self.hands)
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class CurrentHandActionsDto:
    """Current hand actions for LLM context.

    Example serialized output:
        ACTIONS THIS HAND:
          PREFLOP: Alice(BTN):R150, Bob(SB):C, ?
          FLOP: ?
    """

    rounds: tuple[RoundDto, ...]

    @classmethod
    def from_hand_record(
        cls,
        hand: HandRecord,
        current_phase: str,
    ) -> CurrentHandActionsDto:
        current_phase_upper = current_phase.upper()

        rounds: list[RoundDto] = []
        found_current = False

        for round_record in hand.rounds:
            is_current = (
                round_record.phase.value.upper() == current_phase_upper
            )
            if is_current:
                found_current = True
            rounds.append(
                RoundDto.from_round_record(
                    round_record, hand, None, is_current
                )
            )

        if not found_current:
            phase = HandPhase(current_phase.lower())
            rounds.append(
                RoundDto(phase=phase, turns=(), is_current_phase=True)
            )

        return cls(rounds=tuple(rounds))

    def serialize(self) -> str:
        if not self.rounds:
            return ""
        lines = ["ACTIONS THIS HAND:"]
        for round_dto in self.rounds:
            lines.append(f"  {round_dto.serialize()}")
        return "\n".join(lines)
