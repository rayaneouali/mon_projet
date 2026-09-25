from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str


class MailSendError(Exception):
    """The email could not be sent."""


class MailSender(Protocol):
    def send(self, email: OutgoingEmail, idempotency_key: str) -> None: ...


class FakeMailSender:
    """Simulated sending. Like the real one will, it never sends the same key twice."""

    def __init__(self) -> None:
        self.sent: dict[str, OutgoingEmail] = {}

    def send(self, email: OutgoingEmail, idempotency_key: str) -> None:
        if idempotency_key in self.sent:
            return  # already sent: do nothing (idempotency)
        self.sent[idempotency_key] = email
