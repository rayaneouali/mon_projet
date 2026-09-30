from datetime import UTC, datetime, timedelta

import pytest

from voxmail.agent.agent import Agent
from voxmail.contacts.directory import InMemoryContactDirectory
from voxmail.contacts.memory import InMemoryChoiceMemory
from voxmail.domain.contacts import Contact
from voxmail.domain.models import Action, EmailDraft, Extraction, ReplyKind
from voxmail.domain.recipient_search import RecipientHint as Hint
from voxmail.domain.state_machine import ConversationState as State
from voxmail.llm.base import LLMError
from voxmail.llm.fake import FakeLLM
from voxmail.mail.sender import FakeMailSender, MailSendError

CONTACTS = [
    Contact("jean.dupont@btp-dupont.fr", "Jean", "Dupont", interaction_count=5),
    Contact("jmartin@gmail.com", "Jean", "Martin"),
    Contact("s.garnier@comptable.fr", "Sophie", "Garnier"),
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


def make_agent(responses, sender=None, memory=None):
    clock = Clock()
    agent = Agent(
        llm=FakeLLM(responses),
        contacts=InMemoryContactDirectory(CONTACTS),
        sender=sender or FakeMailSender(),
        signature="Rayane Ouali",
        clock=clock,
        memory=memory,
    )
    return agent, clock


def sophie_request():
    return Extraction(recipient=Hint(heard_names=["Sophie Garnier"]), intent="Envoyer les factures")


def to_preview(responses=None, sender=None):
    agent, clock = make_agent(responses or [sophie_request(), DRAFT], sender)
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Sophie pour les factures")
    assert reply.kind == ReplyKind.ASK_CHOICE
    reply = agent.handle_text(conv, "1")
    return agent, clock, conv, reply


# ---------- choosing the recipient ----------


def test_even_a_single_obvious_match_must_be_picked_by_the_human():
    agent, _ = make_agent([sophie_request()])
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Sophie Garnier pour les factures")
    assert reply.kind == ReplyKind.ASK_CHOICE
    assert conv.recipient is None  # nothing selected automatically
    assert "1. Sophie Garnier (s.garnier@comptable.fr)" in reply.text
    assert "2. Aucun de ceux-là" in reply.text
    assert "J'ai compris : « Sophie Garnier »" in reply.text


def test_picking_by_number_needs_no_llm():
    agent, _, conv, reply = to_preview()
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "s.garnier@comptable.fr"
    assert len(agent.llm.calls) == 2  # extraction + writing, not for "1"


def test_homonyms_are_listed_most_likely_first():
    agent, _ = make_agent([Extraction(recipient=Hint(heard_names=["Jean"]), intent="Réunion à 9h")])
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Jean, réunion à 9h")
    assert [c.email for c in conv.choices] == ["jean.dupont@btp-dupont.fr", "jmartin@gmail.com"]
    assert "3. Aucun de ceux-là" in reply.text


def test_choice_is_learned_and_ranks_higher_next_time():
    memory = InMemoryChoiceMemory()
    request = Extraction(recipient=Hint(heard_names=["Jean"]), intent="Réunion à 9h")
    for _ in range(2):
        agent, _ = make_agent([request, DRAFT], memory=memory)
        conv = agent.start()
        agent.handle_text(conv, "mail à Jean")
        agent.handle_text(conv, str(1 + [c.email for c in conv.choices].index("jmartin@gmail.com")))

    agent, _ = make_agent([request], memory=memory)
    conv = agent.start()
    agent.handle_text(conv, "mail à Jean")
    assert conv.choices[0].email == "jmartin@gmail.com"
    assert conv.recipient is None  # still only a suggestion


def test_none_of_these_asks_for_more_clues_then_searches_again():
    agent, _ = make_agent(
        [
            Extraction(recipient=Hint(heard_names=["Jean"]), intent="Plans prêts"),
            Extraction(recipient=Hint(heard_names=["Martin"])),
        ]
    )
    conv = agent.start()
    agent.handle_text(conv, "mail à Jean")
    reply = agent.handle_text(conv, "3")  # "Aucun de ceux-là"
    assert reply.kind == ReplyKind.ASK_MORE_CLUES
    reply = agent.handle_text(conv, "Martin")
    assert reply.kind == ReplyKind.ASK_CHOICE
    assert conv.choices[0].email == "jmartin@gmail.com"


def test_words_instead_of_a_number_are_new_clues_not_a_choice():
    agent, _ = make_agent(
        [
            Extraction(recipient=Hint(heard_names=["Jean"]), intent="Plans prêts"),
            Extraction(recipient=Hint(heard_names=["Jean Martin"])),
        ]
    )
    conv = agent.start()
    agent.handle_text(conv, "mail à Jean")
    reply = agent.handle_text(conv, "Jean Martin")
    assert reply.kind == ReplyKind.ASK_CHOICE
    assert conv.recipient is None
    assert conv.choices[0].email == "jmartin@gmail.com"


def test_out_of_range_number_asks_again():
    agent, _ = make_agent([sophie_request()])
    conv = agent.start()
    agent.handle_text(conv, "mail à Sophie")
    assert agent.handle_text(conv, "7").kind == ReplyKind.ASK_CHOICE
    assert conv.recipient is None


def test_nobody_found_asks_for_more_clues():
    agent, _ = make_agent([Extraction(recipient=Hint(heard_names=["Zébulon"]), intent="rdv")])
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Zébulon")
    assert reply.kind == ReplyKind.ASK_MORE_CLUES
    assert "Je ne trouve personne" in reply.text


def test_known_address_is_still_proposed_for_a_choice():
    agent, _ = make_agent([Extraction(recipient=Hint(email="JMartin@gmail.com"), intent="Plans")])
    conv = agent.start()
    assert agent.handle_text(conv, "mail à jmartin@gmail.com").kind == ReplyKind.ASK_CHOICE
    assert [c.email for c in conv.choices] == ["jmartin@gmail.com"]


def test_new_address_must_be_confirmed_letter_by_letter():
    agent, _ = make_agent(
        [
            Extraction(
                recipient=Hint(heard_names=["Paul Girard"], email="paul@nouveau.fr"),
                intent="Confirmer le rdv",
            ),
            Extraction(confirmation=True),
            DRAFT,
        ]
    )
    conv = agent.start()
    reply = agent.handle_text(conv, "mail à Paul Girard, paul arobase nouveau point fr")
    assert reply.kind == ReplyKind.CONFIRM_EMAIL
    assert "p a u l @" in reply.text
    assert conv.recipient is None
    assert agent.handle_text(conv, "oui").kind == ReplyKind.PREVIEW
    assert conv.recipient.email == "paul@nouveau.fr"
    assert conv.recipient.full_name == "Paul Girard"


def test_rejected_address_is_forgotten_and_the_corrected_one_confirmed():
    agent, _ = make_agent(
        [
            Extraction(recipient=Hint(email="martin.b@free.fr"), intent="Plans prêts"),
            Extraction(confirmation=False),
            Extraction(recipient=Hint(email="martin.d@free.fr")),
        ]
    )
    conv = agent.start()
    agent.handle_text(conv, "mail à martin point b arobase free point fr")
    assert agent.handle_text(conv, "non").kind == ReplyKind.ASK_MORE_CLUES
    assert conv.recipient_hint.email is None
    reply = agent.handle_text(conv, "martin point d arobase free point fr")
    assert reply.kind == ReplyKind.CONFIRM_EMAIL
    assert conv.unconfirmed_email == "martin.d@free.fr"


def test_repeating_the_chosen_name_does_not_reset_the_choice():
    agent, _ = make_agent(
        [
            Extraction(recipient=Hint(heard_names=["Sophie Garnier"])),
            Extraction(recipient=Hint(heard_names=["Sophie"]), intent="Envoyer les factures"),
            DRAFT,
        ]
    )
    conv = agent.start()
    agent.handle_text(conv, "mail à Sophie Garnier")
    assert agent.handle_text(conv, "1").kind == ReplyKind.ASK_INTENT
    assert agent.handle_text(conv, "dis à Sophie que...").kind == ReplyKind.PREVIEW


# ---------- preview, edits, sending ----------


def test_complete_request_gives_a_preview():
    _, _, conv, reply = to_preview()
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.state == State.AWAITING_VALIDATION
    assert "Sophie Garnier <s.garnier@comptable.fr>" in reply.text
    assert "Rayane Ouali" in reply.text  # signature added by code
    assert reply.actions == [Action.SEND, Action.EDIT, Action.CANCEL]


def test_send_waits_for_the_delay_then_sends_once():
    sender = FakeMailSender()
    agent, clock, conv, _ = to_preview(sender=sender)

    assert agent.handle_action(conv, Action.SEND).kind == ReplyKind.SENDING
    assert conv.state == State.PENDING_SEND

    clock.advance(seconds=29)
    assert agent.process_due_send(conv) is None
    assert sender.sent == {}

    clock.advance(seconds=1)
    assert agent.process_due_send(conv).kind == ReplyKind.SENT
    assert agent.process_due_send(conv) is None  # never a second email
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
    agent, _, conv, _ = to_preview([sophie_request(), DRAFT, Extraction(wants_to_send=True)])
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
            Extraction(recipient=Hint(heard_names=["Sophie Garnier"])),
            Extraction(intent="Envoyer les factures"),
            DRAFT,
        ]
    )
    conv = agent.start()
    assert agent.handle_text(conv, "je veux envoyer un mail").kind == ReplyKind.ASK_RECIPIENT
    assert agent.handle_text(conv, "à Sophie Garnier").kind == ReplyKind.ASK_CHOICE
    assert agent.handle_text(conv, "1").kind == ReplyKind.ASK_INTENT
    assert agent.handle_text(conv, "les factures").kind == ReplyKind.PREVIEW


def test_unclear_message_is_reformulated_and_confirmed():
    agent, _ = make_agent(
        [
            Extraction(
                unclear=True,
                reformulation="écrire à Sophie Garnier pour les factures",
                recipient=Hint(heard_names=["Sophie Garnier"]),
                intent="Envoyer les factures",
            ),
            Extraction(confirmation=True),
        ]
    )
    conv = agent.start()
    assert agent.handle_text(conv, "euh sophie euh factures truc").kind == ReplyKind.CLARIFY
    assert conv.recipient_hint is None  # nothing used before confirmation
    assert agent.handle_text(conv, "oui").kind == ReplyKind.ASK_CHOICE


def test_edit_creates_a_new_version():
    new_draft = EmailDraft(subject="Factures", body="Bonjour,\n\nVoici les factures par virement.")
    responses = [sophie_request(), DRAFT, Extraction(edit_instruction="ajoute virement"), new_draft]
    agent, _, conv, _ = to_preview(responses)
    assert agent.handle_action(conv, Action.EDIT).kind == ReplyKind.ASK_EDIT
    reply = agent.handle_text(conv, "ajoute que je paie par virement")
    assert reply.kind == ReplyKind.PREVIEW
    assert conv.draft.version == 2
    writer_prompt = agent.llm.calls[-1][1]
    assert "Previous draft" in writer_prompt and "ajoute virement" in writer_prompt


def test_change_of_recipient_at_preview_goes_through_a_choice():
    responses = [
        sophie_request(),
        DRAFT,
        Extraction(recipient=Hint(heard_names=["Jean Dupont"])),
        DRAFT,
    ]
    agent, _, conv, _ = to_preview(responses)
    reply = agent.handle_text(conv, "envoie-le plutôt à Jean Dupont")
    assert reply.kind == ReplyKind.ASK_CHOICE
    assert conv.state == State.COLLECTING
    assert agent.handle_text(conv, "1").kind == ReplyKind.PREVIEW
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
