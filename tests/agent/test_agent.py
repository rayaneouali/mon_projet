from datetime import UTC, datetime, timedelta

import pytest

from voxmail.agent.agent import Agent
from voxmail.contacts.directory import InMemoryContactDirectory
from voxmail.domain.contacts import Contact
from voxmail.domain.models import Action, EmailDraft, Extraction, ReplyKind
from voxmail.domain.state_machine import ConversationState as State
from voxmail.llm.base import LLMError
from voxmail.llm.fake import FakeLLM
from voxmail.mail.sender import FakeMailSender, MailSendError

CONTACTS = [
    Contact("Jean Dupont", ("jean.dupont@btp-dupont.fr",)),
    Contact("Jean Martin", ("jmartin@gmail.com",)),
    Contact("Sophie Garnier", ("s.garnier@comptable.fr",)),
]
DRAFT = EmailDraft(subject="Factures", body="Bonjour Madame Garnier,\n\nVoici les factures.")


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


class FailingSender:
    def send(self, email, idempotency_key):
        raise MailSendError("boom")


def make_agent(responses, sender=None):
    clock = Clock()
    agent = Agent(
        llm=FakeLLM(responses),
        contacts=InMemoryContactDirectory(CONTACTS),
        sender=sender or FakeMailSender(),
        signature="Rayane Ouali",
        clock=clock,
    )
    return agent, clock


def full_request():
    return Extraction(recipient="Sophie Garnier", intent="Envoyer les factures")


def to_preview(responses=None, sender=None):
    agent, clock = make_agent(responses or [full_request(), DRAFT], sender)
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Sophie pour les factures")
    return agent, clock, conv, reply


def test_complete_request_gives_a_preview():
    _, _, conv, reply = to_preview()
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.state == State.AWAITING_VALIDATION
    assert "s.garnier@comptable.fr" in reply.text
    assert "Rayane Ouali" in reply.text  # signature added by code
    assert reply.actions == [Action.SEND, Action.EDIT, Action.CANCEL]


def test_send_waits_for_the_delay_then_sends_once():
    sender = FakeMailSender()
    agent, clock, conv, _ = to_preview(sender=sender)

    reply = agent.handle_action(conv, Action.SEND)
    assert reply.kind == ReplyKind.SENDING
    assert conv.state == State.PENDING_SEND

    clock.advance(seconds=29)
    assert agent.process_due_send(conv) is None
    assert sender.sent == {}

    clock.advance(seconds=1)
    assert agent.process_due_send(conv).kind == ReplyKind.SENT
    assert conv.state == State.SENT
    # Calling again must never send a second email.
    assert agent.process_due_send(conv) is None
    assert len(sender.sent) == 1
    email = next(iter(sender.sent.values()))
    assert email.to == "s.garnier@comptable.fr"
    assert email.body.endswith("Rayane Ouali")


def test_cancel_during_delay_sends_nothing():
    sender = FakeMailSender()
    agent, clock, conv, _ = to_preview(sender=sender)
    agent.handle_action(conv, Action.SEND)
    assert agent.handle_action(conv, Action.CANCEL).kind == ReplyKind.CANCELLED
    clock.advance(seconds=60)
    assert agent.process_due_send(conv) is None
    assert sender.sent == {}


def test_asking_to_send_in_words_never_sends():
    responses = [full_request(), DRAFT, Extraction(wants_to_send=True)]
    agent, _, conv, _ = to_preview(responses)
    reply = agent.handle_text(conv, "c'est parfait envoie-le")
    assert reply.kind == ReplyKind.USE_BUTTONS
    assert conv.state == State.AWAITING_VALIDATION


def test_send_is_refused_before_a_preview():
    agent, _ = make_agent([])
    conv = agent.start()
    assert agent.handle_action(conv, Action.SEND).kind == ReplyKind.ERROR
    assert conv.state == State.COLLECTING


def test_send_failure_moves_to_failed():
    agent, clock, conv, _ = to_preview(sender=FailingSender())
    agent.handle_action(conv, Action.SEND)
    clock.advance(seconds=30)
    assert agent.process_due_send(conv).kind == ReplyKind.FAILED
    assert conv.state == State.FAILED


def test_missing_recipient_then_missing_intent():
    agent, _ = make_agent(
        [
            Extraction(),
            Extraction(recipient="Sophie Garnier"),
            Extraction(intent="Envoyer les factures"),
            DRAFT,
        ]
    )
    conv = agent.start()
    assert agent.handle_text(conv, "je veux envoyer un mail").kind == ReplyKind.ASK_RECIPIENT
    assert agent.handle_text(conv, "à Sophie Garnier").kind == ReplyKind.ASK_INTENT
    assert agent.handle_text(conv, "les factures").kind == ReplyKind.PREVIEW


def test_homonyms_ask_which_one_then_number_needs_no_llm():
    llm_responses = [Extraction(recipient="Jean", intent="Réunion avancée à 9h"), DRAFT]
    agent, _ = make_agent(llm_responses)
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Jean, réunion avancée à 9h")
    assert reply.kind == ReplyKind.ASK_CHOICE
    assert "1. Jean Dupont" in reply.text and "2. Jean Martin" in reply.text

    reply = agent.handle_text(conv, "2")
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "jmartin@gmail.com"
    assert len(agent.llm.calls) == 2  # extraction + writing, not for "2"


def test_new_address_must_be_confirmed():
    agent, _ = make_agent(
        [
            Extraction(recipient="paul@nouveau.fr", intent="Confirmer le rdv"),
            Extraction(confirmation=True),
            DRAFT,
        ]
    )
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à paul arobase nouveau point fr")
    assert reply.kind == ReplyKind.CONFIRM_EMAIL
    assert "p a u l @" in reply.text  # spelled out letter by letter
    assert conv.recipient is None
    assert agent.handle_text(conv, "oui").kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "paul@nouveau.fr"


def test_new_address_refused_then_corrected():
    agent, _ = make_agent(
        [
            Extraction(recipient="martin.b@free.fr", intent="Plans prêts"),
            Extraction(confirmation=False, recipient="martin.d@free.fr"),
        ]
    )
    conv = agent.start()
    agent.handle_text(conv, "mail à martin point b arobase free point fr")
    reply = agent.handle_text(conv, "non c'est martin point d")
    assert reply.kind == ReplyKind.CONFIRM_EMAIL
    assert conv.unconfirmed_email == "martin.d@free.fr"


def test_unknown_contact_asks_for_address_and_keeps_the_name():
    agent, _ = make_agent(
        [
            Extraction(recipient="Paul Girard", intent="Confirmer le rdv"),
            Extraction(recipient="paul.girard@gmail.com"),
            Extraction(confirmation=True),
            DRAFT,
        ]
    )
    conv = agent.start()
    assert agent.handle_text(conv, "mail à Paul Girard").kind == ReplyKind.ASK_EMAIL
    assert agent.handle_text(conv, "paul.girard@gmail.com").kind == ReplyKind.CONFIRM_EMAIL
    agent.handle_text(conv, "oui")
    assert conv.recipient.name == "Paul Girard"


def test_unclear_message_is_reformulated_and_confirmed():
    agent, _ = make_agent(
        [
            Extraction(
                unclear=True,
                reformulation="écrire à Sophie Garnier pour les factures",
                recipient="Sophie Garnier",
                intent="Envoyer les factures",
            ),
            Extraction(confirmation=True),
            DRAFT,
        ]
    )
    conv = agent.start()
    reply = agent.handle_text(conv, "euh sophie euh factures truc")
    assert reply.kind == ReplyKind.CLARIFY
    assert conv.recipient is None  # nothing guessed yet
    assert agent.handle_text(conv, "oui").kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "s.garnier@comptable.fr"


def test_edit_creates_a_new_version():
    new_draft = EmailDraft(subject="Factures", body="Bonjour,\n\nVoici les factures par virement.")
    responses = [full_request(), DRAFT, Extraction(edit_instruction="ajoute virement"), new_draft]
    agent, _, conv, _ = to_preview(responses)
    assert agent.handle_action(conv, Action.EDIT).kind == ReplyKind.ASK_EDIT
    reply = agent.handle_text(conv, "ajoute que je paie par virement")
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.draft.version == 2
    assert "virement" in conv.draft.body
    writer_prompt = agent.llm.calls[-1][1]
    assert "Previous draft" in writer_prompt and "ajoute virement" in writer_prompt


def test_change_of_recipient_at_preview():
    responses = [full_request(), DRAFT, Extraction(recipient="Jean Dupont"), DRAFT]
    agent, _, conv, _ = to_preview(responses)
    reply = agent.handle_text(conv, "envoie-le plutôt à Jean Dupont")
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "jean.dupont@btp-dupont.fr"


def test_cancel_by_text():
    agent, _ = make_agent([Extraction(cancel=True)])
    conv = agent.start()
    assert agent.handle_text(conv, "laisse tomber").kind == ReplyKind.CANCELLED
    assert conv.state == State.CANCELLED


def test_llm_failure_keeps_the_conversation():
    agent, _ = make_agent([LLMError("network")])
    conv = agent.start()
    assert agent.handle_text(conv, "mail à Sophie").kind == ReplyKind.ERROR
    assert conv.state == State.COLLECTING


def test_draft_expires_after_23_hours():
    agent, clock, conv, _ = to_preview()
    clock.advance(hours=23)
    assert agent.handle_action(conv, Action.SEND).kind == ReplyKind.EXPIRED
    assert conv.state == State.CANCELLED


def test_finished_conversation_rejects_new_text():
    agent, _ = make_agent([Extraction(cancel=True)])
    conv = agent.start()
    agent.handle_text(conv, "annule")
    with pytest.raises(ValueError):
        agent.handle_text(conv, "encore")
