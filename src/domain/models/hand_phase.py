from enum import Enum


class HandPhase(Enum):
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

    @property
    def card_count(self) -> int:
        """Number of community cards required for this phase."""
        mapping = {
            HandPhase.PRE_FLOP: 0,
            HandPhase.FLOP: 3,
            HandPhase.TURN: 4,
            HandPhase.RIVER: 5,
            HandPhase.SHOWDOWN: 5,
        }
        return mapping[self]

    @classmethod
    def get_phase_order(cls) -> tuple["HandPhase", ...]:
        """Returns phases in sequence order."""
        return (
            cls.PRE_FLOP,
            cls.FLOP,
            cls.TURN,
            cls.RIVER,
            cls.SHOWDOWN,
        )

    def next_phase(self) -> "HandPhase | None":
        """Returns the next phase in sequence, or None if this is the last phase."""
        order = self.get_phase_order()
        try:
            current_index = order.index(self)
            if current_index + 1 >= len(order):
                return None
            return order[current_index + 1]
        except ValueError:
            return None
