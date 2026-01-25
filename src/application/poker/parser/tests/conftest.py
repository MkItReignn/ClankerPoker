"""Shared fixtures for parser tests."""

import pytest

from src.domain.models.available_action import (
    AvailableAllInAction,
    AvailableBetAction,
    AvailableCallAction,
    AvailableCheckAction,
    AvailableFoldAction,
    AvailableRaiseAction,
)
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
def full_thought_process_response():
    """A complete LLM response with THOUGHT_PROCESS and ACTION."""
    return """
THOUGHT_PROCESS:
We're in the middle of the tournament with a healthy 37 big blind stack, so there's no
immediate survival pressure. I'm on the button which is an excellent position - I'll be
last to act on every street after the flop.

Looking at the pot odds, I'm getting about 3:1 with 24 big blinds effective stacks.
The under-the-gun player typically has a strong range here - pocket jacks or better,
ace-king, ace-queen. Their continuation bet could be a strong king or a bluff.

With top pair and best kicker, I estimate my equity at around 70-75% against their
likely range. Alice tends to play straightforward and commits with strong hands,
so I can extract value here.

A raise to 300 (about 3 times the bet) builds the pot while keeping her range wide
enough to call. On safe turn cards I'll continue betting around 60% of the pot,
but I'll check back if a dangerous card comes. This is a pure value spot with
position advantage.

ACTION: raise 300
""".strip()


@pytest.fixture
def minimal_response():
    """Minimal valid response with just ACTION."""
    return """
ACTION: fold
""".strip()
