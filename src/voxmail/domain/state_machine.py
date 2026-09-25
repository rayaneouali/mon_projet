"""Conversation state machine.

A conversation is always in exactly one state. Only the transitions listed in
ALLOWED_TRANSITIONS are possible: this is what guarantees that an email can
never be sent without an explicit validation by the user.
"""

from datetime import datetime, timedelta
from enum import StrEnum


class ConversationState(StrEnum):
    COLLECTING = "collecting"  # gathering recipient, subject and intent
    DRAFT_READY = "draft_ready"  # a draft has been written
    AWAITING_VALIDATION = "awaiting_validation"  # preview shown, waiting for Send/Edit/Cancel
    PENDING_SEND = "pending_send"  # validated, 30 s window to cancel
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


State = ConversationState

ALLOWED_TRANSITIONS: dict[State, frozenset[State]] = {
    State.COLLECTING: frozenset({State.DRAFT_READY, State.CANCELLED}),
    State.DRAFT_READY: frozenset({State.AWAITING_VALIDATION, State.CANCELLED}),
    State.AWAITING_VALIDATION: frozenset(
        {
            State.PENDING_SEND,  # user pressed "Send"
            State.DRAFT_READY,  # user pressed "Edit": a new version is written
            State.COLLECTING,  # the edit needs new information (e.g. another recipient)
            State.CANCELLED,  # user pressed "Cancel"
        }
    ),
    State.PENDING_SEND: frozenset({State.SENT, State.CANCELLED, State.FAILED}),
    # Final states: nothing can happen after them.
    State.SENT: frozenset(),
    State.CANCELLED: frozenset(),
    State.FAILED: frozenset(),
}

# WhatsApp only allows free-form replies within 24 h of the user's last message,
# so we give up a bit earlier to still be able to notify the user.
STATE_TIMEOUTS: dict[State, timedelta] = {
    State.COLLECTING: timedelta(hours=23),
    State.DRAFT_READY: timedelta(hours=23),
    State.AWAITING_VALIDATION: timedelta(hours=23),
}


class InvalidTransitionError(Exception):
    """Raised when code tries a transition that is not allowed."""


def is_final(state: State) -> bool:
    return not ALLOWED_TRANSITIONS[state]


def transition(current: State, target: State) -> State:
    """Return the new state, or raise if moving from `current` to `target` is forbidden."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"Cannot go from {current} to {target}")
    return target


def is_expired(state: State, entered_at: datetime, now: datetime) -> bool:
    """True if the conversation stayed too long in `state` and must be abandoned."""
    timeout = STATE_TIMEOUTS.get(state)
    if timeout is None:
        return False
    return now - entered_at >= timeout
