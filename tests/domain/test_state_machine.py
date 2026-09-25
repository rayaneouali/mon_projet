from datetime import UTC, datetime, timedelta
from itertools import product

import pytest

from voxmail.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    ConversationState,
    InvalidTransitionError,
    is_expired,
    is_final,
    transition,
)

State = ConversationState
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_every_state_has_an_entry_in_the_table():
    assert set(ALLOWED_TRANSITIONS) == set(State)


def test_happy_path_to_sent():
    state = State.COLLECTING
    for target in (
        State.DRAFT_READY,
        State.AWAITING_VALIDATION,
        State.PENDING_SEND,
        State.SENT,
    ):
        state = transition(state, target)
    assert state == State.SENT


def test_edit_loop_is_allowed():
    state = transition(State.AWAITING_VALIDATION, State.DRAFT_READY)
    assert transition(state, State.AWAITING_VALIDATION) == State.AWAITING_VALIDATION


def test_send_can_be_cancelled_during_the_delay():
    assert transition(State.PENDING_SEND, State.CANCELLED) == State.CANCELLED


@pytest.mark.parametrize(
    "current",
    [State.COLLECTING, State.DRAFT_READY, State.SENT, State.CANCELLED, State.FAILED],
)
def test_sending_requires_validation(current):
    # Security rule: the only way into PENDING_SEND is from AWAITING_VALIDATION.
    with pytest.raises(InvalidTransitionError):
        transition(current, State.PENDING_SEND)


def test_nothing_reaches_sent_without_pending_send():
    for current in State:
        if current != State.PENDING_SEND:
            assert State.SENT not in ALLOWED_TRANSITIONS[current]


@pytest.mark.parametrize(
    ("current", "target"),
    [(c, t) for c, t in product(State, State) if t not in ALLOWED_TRANSITIONS[c]],
)
def test_every_forbidden_transition_raises(current, target):
    with pytest.raises(InvalidTransitionError):
        transition(current, target)


@pytest.mark.parametrize("state", [State.SENT, State.CANCELLED, State.FAILED])
def test_final_states(state):
    assert is_final(state)


def test_non_final_state():
    assert not is_final(State.COLLECTING)


def test_draft_expires_after_23_hours():
    entered = NOW - timedelta(hours=23)
    assert is_expired(State.AWAITING_VALIDATION, entered, NOW)


def test_draft_not_expired_before_23_hours():
    entered = NOW - timedelta(hours=22, minutes=59)
    assert not is_expired(State.AWAITING_VALIDATION, entered, NOW)


def test_final_states_never_expire():
    entered = NOW - timedelta(days=365)
    assert not is_expired(State.SENT, entered, NOW)
