"""Shared fixtures for parser tests."""

import pytest

from src.domain.models.available_action import (AvailableAllInAction,
                                                AvailableBetAction,
                                                AvailableCallAction,
                                                AvailableCheckAction,
                                                AvailableFoldAction,
                                                AvailableRaiseAction)
from src.domain.models.chips import ChipAmount


@pytest.fixture
def fold_action():
    return AvailableFoldAction()


@pytest.fixture
def check_action():
    return AvailableCheckAction()


@pytest.fixture
def call_action():
    return AvailableCallAction(call_amount=ChipAmount(100))


@pytest.fixture
def bet_action():
    return AvailableBetAction(
        min_bet_amount=ChipAmount(100),
        max_bet_amount=ChipAmount(1000),
    )


@pytest.fixture
def raise_action():
    return AvailableRaiseAction(
        min_raise_amount=ChipAmount(200),
        max_raise_amount=ChipAmount(2000),
    )


@pytest.fixture
def all_in_action():
    return AvailableAllInAction(all_in_amount=ChipAmount(5000))


@pytest.fixture
def preflop_actions(fold_action, call_action, raise_action):
    """Typical preflop available actions: fold, call, raise."""
    return [fold_action, call_action, raise_action]


@pytest.fixture
def postflop_actions(fold_action, check_action, bet_action):
    """Typical postflop available actions when first to act: fold, check, bet."""
    return [fold_action, check_action, bet_action]


@pytest.fixture
def facing_bet_actions(fold_action, call_action, raise_action, all_in_action):
    """Available actions when facing a bet: fold, call, raise, all-in."""
    return [fold_action, call_action, raise_action, all_in_action]


@pytest.fixture
def full_narration_response():
    """A complete LLM response with all 9 narration fields."""
    return """
GAME_STAGE_ASSESSMENT:
Mid-tournament, 37BB stack, no survival pressure.

POSITIONAL_CONTEXT:
Button position, 3:1 pot odds, 24BB effective.

RANGE_ANALYSIS:
UTG range: JJ+, AK, AQ. C-bet polarizes to Kx or air.

EQUITY_ASSESSMENT:
TPTK has 70-75% equity vs her range.

OPPONENT_MODELING:
Alice plays straightforward, commits with strong hands.

BET_SIZING_RATIONALE:
3x raise to 300 builds pot while keeping her range wide.

MULTI_STREET_PLAN:
Bet 60% pot on safe turns, check dangerous cards.

META_CONSIDERATIONS:
Establishes strong table image, pure chip EV spot.

FINAL_DECISION:
Raise for value with TPTK against straightforward opponent.

ACTION: raise 300

REASONING:
Value raise with position and range advantage.
""".strip()


@pytest.fixture
def minimal_response():
    """Minimal valid response with just ACTION and REASONING."""
    return """
ACTION: fold

REASONING:
Hand is too weak to continue.
""".strip()
