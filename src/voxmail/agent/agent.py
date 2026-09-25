"""The agent: turns user messages into questions, drafts and (after validation) a send.

Split of responsibilities:
- the LLM only extracts information and writes text;
- this code decides what happens next, and it is the only one that can send,
  and only after an explicit Action.SEND on a draft the user has seen.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from voxmail.agent.prompts import (
    EXTRACTION_SYSTEM,
    WRITER_SYSTEM,
    extraction_input,
    writer_input,
)
from voxmail.contacts.directory import ContactDirectory
from voxmail.domain.contacts import (
    Ambiguous,
    Candidate,
    Found,
    NewAddress,
    NotFound,
    normalize,
    resolve_recipient,
)
from voxmail.domain.models import (
    Action,
    AgentReply,
    Conversation,
    Draft,
    EmailDraft,
    Extraction,
    ReplyKind,
)
from voxmail.domain.state_machine import ConversationState, is_expired, is_final
from voxmail.llm.base import LLMClient, LLMError
from voxmail.mail.sender import MailSender, MailSendError, OutgoingEmail

State = ConversationState
PREVIEW_ACTIONS = [Action.SEND, Action.EDIT, Action.CANCEL]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        contacts: ContactDirectory,
        sender: MailSender,
        signature: str,
        send_delay: timedelta = timedelta(seconds=30),
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.llm = llm
        self.contacts = contacts
        self.sender = sender
        self.signature = signature
        self.send_delay = send_delay
        self.clock = clock  # injected so tests can control time

    # ---------- entry points ----------

    def start(self) -> Conversation:
        return Conversation(state_entered_at=self.clock())

    def handle_text(self, conv: Conversation, text: str) -> AgentReply:
        """A free-text (or transcribed voice) message from the user."""
        if expired := self.expire_if_needed(conv):
            return expired
        if is_final(conv.state):
            raise ValueError("This conversation is finished, start a new one")
        if conv.state == State.PENDING_SEND:
            return self._reply(
                conv,
                ReplyKind.USE_BUTTONS,
                "Le mail part dans quelques secondes. Choisissez « Annuler » pour l'arrêter.",
                [Action.CANCEL],
            )

        try:
            extraction = self._extract(conv, text)
        except LLMError:
            return self._technical_error(conv)

        if extraction.cancel:
            return self._cancel(conv)
        try:
            if conv.state == State.AWAITING_VALIDATION:
                return self._handle_edit(conv, extraction, text)
            return self._handle_collecting(conv, extraction)
        except LLMError:
            return self._technical_error(conv)

    def handle_action(self, conv: Conversation, action: Action) -> AgentReply:
        """A button press. This is the ONLY path that can lead to a send."""
        if expired := self.expire_if_needed(conv):
            return expired
        now = self.clock()

        if action == Action.CANCEL and not is_final(conv.state):
            return self._cancel(conv)

        if conv.state != State.AWAITING_VALIDATION:
            return self._reply(conv, ReplyKind.ERROR, "Aucun mail n'attend de validation.")

        if action == Action.EDIT:
            return self._reply(conv, ReplyKind.ASK_EDIT, "Que voulez-vous modifier ?")

        # Action.SEND
        conv.idempotency_key = uuid4().hex
        conv.send_at = now + self.send_delay
        conv.move_to(State.PENDING_SEND, now)
        seconds = int(self.send_delay.total_seconds())
        return self._reply(
            conv,
            ReplyKind.SENDING,
            f"Envoi dans {seconds} secondes. Vous pouvez encore annuler.",
            [Action.CANCEL],
        )

    def process_due_send(self, conv: Conversation) -> AgentReply | None:
        """Send the email if its cancellation window is over. Safe to call many times."""
        now = self.clock()
        if conv.state != State.PENDING_SEND or conv.send_at is None or now < conv.send_at:
            return None
        assert conv.recipient and conv.draft and conv.idempotency_key
        email = OutgoingEmail(
            to=conv.recipient.email,
            subject=conv.draft.subject,
            body=self.full_body(conv.draft),
        )
        try:
            self.sender.send(email, conv.idempotency_key)
        except MailSendError:
            conv.move_to(State.FAILED, now)
            return self._reply(
                conv, ReplyKind.FAILED, "❌ Le mail n'a pas pu être envoyé. Réessayez plus tard."
            )
        conv.move_to(State.SENT, now)
        return self._reply(conv, ReplyKind.SENT, f"✅ Mail envoyé à {conv.recipient.email}.")

    def expire_if_needed(self, conv: Conversation) -> AgentReply | None:
        now = self.clock()
        if not is_expired(conv.state, conv.state_entered_at, now):
            return None
        conv.move_to(State.CANCELLED, now)
        return self._reply(
            conv,
            ReplyKind.EXPIRED,
            "Votre demande de mail est restée sans réponse trop longtemps, je l'ai abandonnée. "
            "Envoyez-moi un nouveau message pour recommencer.",
        )

    def full_body(self, draft: Draft) -> str:
        return f"{draft.body.rstrip()}\n\n{self.signature}"

    # ---------- steps ----------

    def _extract(self, conv: Conversation, text: str) -> Extraction:
        stripped = text.strip()
        # A plain number answering a list of options needs no LLM.
        if conv.choices and stripped.isdigit():
            return Extraction(choice=int(stripped))
        return self.llm.generate(EXTRACTION_SYSTEM, extraction_input(conv, text), Extraction)

    def _handle_collecting(self, conv: Conversation, extraction: Extraction) -> AgentReply:
        if conv.pending_extraction is not None:
            pending, conv.pending_extraction = conv.pending_extraction, None
            if extraction.confirmation is True:
                extraction = pending  # the user confirmed our reformulation
            elif extraction.confirmation is False and not extraction.recipient:
                return self._reply(
                    conv, ReplyKind.CLARIFY, "D'accord. Pouvez-vous reformuler votre demande ?"
                )
        elif extraction.unclear:
            conv.pending_extraction = extraction
            understood = extraction.reformulation or "rien de précis"
            return self._reply(
                conv,
                ReplyKind.CLARIFY,
                f"Je ne suis pas sûr d'avoir bien compris. J'ai compris : « {understood} ». "
                "C'est bien ça ?",
            )

        self._merge(conv, extraction)
        return self._next_step(conv)

    def _handle_edit(self, conv: Conversation, extraction: Extraction, text: str) -> AgentReply:
        """Free text while a preview is shown = a change request. It NEVER sends."""
        wants_change = extraction.edit_instruction or extraction.recipient or extraction.tone
        if extraction.wants_to_send and not wants_change:
            return self._reply(
                conv,
                ReplyKind.USE_BUTTONS,
                "Pour envoyer ce mail, choisissez « Envoyer ».",
                PREVIEW_ACTIONS,
            )
        conv.pending_edit = extraction.edit_instruction or text
        self._merge(conv, extraction)
        if conv.recipient is None:  # the user changed the recipient
            conv.move_to(State.COLLECTING, self.clock())
            return self._next_step(conv)
        return self._write_draft(conv)

    def _merge(self, conv: Conversation, e: Extraction) -> None:
        """Copy what the LLM understood into the conversation."""
        same_query = conv.recipient_query and normalize(e.recipient or "") == normalize(
            conv.recipient_query
        )
        if e.recipient and not same_query:
            conv.recipient_query = e.recipient
            conv.recipient = None
            conv.choices = []
            conv.unconfirmed_email = None
        elif conv.choices and e.choice is not None and 1 <= e.choice <= len(conv.choices):
            conv.recipient = conv.choices[e.choice - 1]
            conv.choices = []
        elif conv.unconfirmed_email and e.confirmation is not None:
            if e.confirmation:
                name = conv.recipient_name_hint or ""
                conv.recipient = Candidate(name=name, email=conv.unconfirmed_email)
            else:
                conv.recipient_query = None
            conv.unconfirmed_email = None

        if e.subject:
            conv.subject = e.subject
        if e.intent:
            conv.intent = e.intent
        if e.tone:
            conv.tone = e.tone

    def _next_step(self, conv: Conversation) -> AgentReply:
        """Deterministic decision: which question to ask, or write the draft."""
        if conv.recipient is None:
            if question := self._resolve_recipient(conv):
                return question
        if not conv.intent:
            name = conv.recipient.name if conv.recipient and conv.recipient.name else "ce contact"
            return self._reply(
                conv, ReplyKind.ASK_INTENT, f"Que voulez-vous dire à {name} dans ce mail ?"
            )
        return self._write_draft(conv)

    def _resolve_recipient(self, conv: Conversation) -> AgentReply | None:
        """Set conv.recipient, or return the question to ask."""
        if conv.choices:
            return self._ask_choice(conv)
        if conv.unconfirmed_email:
            return self._ask_confirm_email(conv)
        if not conv.recipient_query:
            return self._reply(conv, ReplyKind.ASK_RECIPIENT, "À qui voulez-vous écrire ?")

        match resolve_recipient(conv.recipient_query, self.contacts.list_contacts()):
            case Found(recipient):
                conv.recipient = recipient
                return None
            case Ambiguous(candidates):
                conv.choices = list(candidates)
                return self._ask_choice(conv)
            case NotFound(query):
                conv.recipient_name_hint = query
                conv.recipient_query = None
                return self._reply(
                    conv,
                    ReplyKind.ASK_EMAIL,
                    f"Je ne trouve pas « {query} » dans vos contacts. "
                    "Quelle est son adresse mail ?",
                )
            case NewAddress(email):
                conv.unconfirmed_email = email
                return self._ask_confirm_email(conv)
        raise AssertionError("unreachable")

    def _ask_choice(self, conv: Conversation) -> AgentReply:
        options = "\n".join(
            f"{i}. {c.name} ({c.email})" for i, c in enumerate(conv.choices, start=1)
        )
        return self._reply(conv, ReplyKind.ASK_CHOICE, f"Lequel voulez-vous ?\n{options}")

    def _ask_confirm_email(self, conv: Conversation) -> AgentReply:
        email = conv.unconfirmed_email or ""
        spelled = " ".join(email)
        return self._reply(
            conv,
            ReplyKind.CONFIRM_EMAIL,
            f"Je n'ai jamais écrit à cette adresse. Pouvez-vous confirmer qu'elle est exacte ?\n"
            f"{email}\n({spelled})\nRépondez oui, ou donnez la bonne adresse.",
        )

    def _write_draft(self, conv: Conversation) -> AgentReply:
        written = self.llm.generate(WRITER_SYSTEM, writer_input(conv), EmailDraft)
        version = conv.draft.version + 1 if conv.draft else 1
        conv.draft = Draft(subject=written.subject, body=written.body, version=version)
        conv.pending_edit = None
        now = self.clock()
        conv.move_to(State.DRAFT_READY, now)
        conv.move_to(State.AWAITING_VALIDATION, now)
        return self._reply(conv, ReplyKind.PREVIEW, self._preview(conv), PREVIEW_ACTIONS)

    def _preview(self, conv: Conversation) -> str:
        assert conv.recipient and conv.draft
        to = conv.recipient.email
        if conv.recipient.name:
            to = f"{conv.recipient.name} <{to}>"
        return f"À : {to}\nObjet : {conv.draft.subject}\n\n{self.full_body(conv.draft)}"

    def _cancel(self, conv: Conversation) -> AgentReply:
        conv.move_to(State.CANCELLED, self.clock())
        return self._reply(conv, ReplyKind.CANCELLED, "C'est annulé, aucun mail n'a été envoyé.")

    def _technical_error(self, conv: Conversation) -> AgentReply:
        return self._reply(
            conv, ReplyKind.ERROR, "Désolé, j'ai eu un problème technique. Pouvez-vous réessayer ?"
        )

    def _reply(
        self,
        conv: Conversation,
        kind: ReplyKind,
        text: str,
        actions: list[Action] | None = None,
    ) -> AgentReply:
        conv.last_agent_message = text
        return AgentReply(kind=kind, text=text, actions=actions or [])
