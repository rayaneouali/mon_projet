"""Data shapes of a conversation. Pure data, no I/O."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from voxmail.domain.contacts import Candidate
from voxmail.domain.state_machine import ConversationState, transition

Tone = Literal["vous", "tu"]


class Extraction(BaseModel):
    """What the LLM understood from ONE user message. Every field is optional."""

    recipient: str | None = Field(
        default=None,
        description="Name or email address of the person to write to, as given by the user. "
        "Dictated addresses must be converted to a real address "
        "('jean point dupont arobase gmail point com' -> 'jean.dupont@gmail.com').",
    )
    subject: str | None = Field(default=None, description="Email subject, if the user gave one.")
    intent: str | None = Field(
        default=None,
        description="Complete, up-to-date description (in French) of what the email must say, "
        "merging what was already known with the new message. Null if still too vague.",
    )
    tone: Tone | None = Field(
        default=None,
        description="'tu' only if the user asks for it or the context clearly says so.",
    )
    choice: int | None = Field(
        default=None,
        description="Number (1-based) of the option the user picked, if a list was offered.",
    )
    confirmation: bool | None = Field(
        default=None, description="Answer to the last yes/no question: true = yes, false = no."
    )
    cancel: bool = Field(default=False, description="True if the user wants to abandon this email.")
    wants_to_send: bool = Field(
        default=False, description="True if the user asks in words to send the email."
    )
    edit_instruction: str | None = Field(
        default=None, description="If a draft exists: what the user wants to change in it."
    )
    unclear: bool = Field(
        default=False,
        description="True only if the message is garbled or incoherent (bad transcription).",
    )
    reformulation: str | None = Field(
        default=None, description="If unclear: what you think the user meant, in French."
    )


class EmailDraft(BaseModel):
    """What the LLM writes. The signature is added by code, not by the LLM."""

    subject: str = Field(description="Short email subject, in French.")
    body: str = Field(description="Email body in French, from greeting to closing, no signature.")


class Draft(BaseModel):
    subject: str
    body: str
    version: int = 1


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    state: ConversationState = ConversationState.COLLECTING
    state_entered_at: datetime

    recipient_query: str | None = None  # what the user said: "Jean", "jean@x.fr"...
    recipient_name_hint: str | None = None  # name kept when we must ask for an address
    recipient: Candidate | None = None  # resolved and safe to use
    choices: list[Candidate] = []  # options offered when ambiguous
    unconfirmed_email: str | None = None  # new address waiting for spelling confirmation
    pending_extraction: Extraction | None = None  # unclear message waiting for confirmation

    subject: str | None = None
    intent: str | None = None
    tone: Tone = "vous"
    draft: Draft | None = None
    pending_edit: str | None = None

    last_agent_message: str | None = None
    idempotency_key: str | None = None
    send_at: datetime | None = None

    def move_to(self, target: ConversationState, now: datetime) -> None:
        """The ONLY way to change state: it goes through the state machine."""
        self.state = transition(self.state, target)
        self.state_entered_at = now


class Action(StrEnum):
    """Closed choices (buttons). Only these can trigger a send."""

    SEND = "send"
    EDIT = "edit"
    CANCEL = "cancel"


class ReplyKind(StrEnum):
    ASK_RECIPIENT = "ask_recipient"
    ASK_CHOICE = "ask_choice"
    ASK_EMAIL = "ask_email"
    CONFIRM_EMAIL = "confirm_email"
    ASK_INTENT = "ask_intent"
    CLARIFY = "clarify"
    PREVIEW = "preview"
    ASK_EDIT = "ask_edit"
    USE_BUTTONS = "use_buttons"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ERROR = "error"


class AgentReply(BaseModel):
    kind: ReplyKind
    text: str
    actions: list[Action] = []
