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
    describe_hint,
    extraction_input,
    writer_input,
)
from voxmail.contacts.directory import ContactDirectory
from voxmail.contacts.memory import ChoiceMemory, InMemoryChoiceMemory
from voxmail.domain.contacts import Contact, is_email
from voxmail.domain.models import (
    Action,
    AgentReply,
    Conversation,
    Draft,
    EmailDraft,
    Extraction,
    ReplyKind,
)
from voxmail.domain.recipient_search import (
    DEFAULT_SCORING,
    RecipientHint,
    ScoringConfig,
    context_similarity,
    name_similarity,
    suggest_recipients,
)
from voxmail.domain.state_machine import ConversationState, is_expired, is_final
from voxmail.llm.base import LLMClient, LLMError
from voxmail.mail.sender import MailSender, MailSendError, OutgoingEmail

State = ConversationState
PREVIEW_ACTIONS = [Action.SEND, Action.EDIT, Action.CANCEL]
# A new hint "is" the chosen recipient above these similarities (no reset needed).
SAME_RECIPIENT_NAME = 0.85
SAME_RECIPIENT_CONTEXT = 0.75


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
        memory: ChoiceMemory | None = None,
        scoring: ScoringConfig = DEFAULT_SCORING,
    ) -> None:
        self.llm = llm
        self.contacts = contacts
        self.sender = sender
        self.signature = signature
        self.send_delay = send_delay
        self.clock = clock  # injected so tests can control time
        self.memory = memory if memory is not None else InMemoryChoiceMemory()
        self.scoring = scoring

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

        # A plain number answering the list of contacts: a human choice, no LLM.
        if conv.choices and text.strip().isdigit():
            return self.handle_choice(conv, int(text.strip()))

        try:
            extraction = self.llm.generate(
                EXTRACTION_SYSTEM, extraction_input(conv, text), Extraction
            )
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

    def handle_choice(self, conv: Conversation, number: int) -> AgentReply:
        """The human picked a line of the contact list (1-based). The ONLY way to
        select a contact from the address book: neither the LLM nor the score can."""
        if expired := self.expire_if_needed(conv):
            return expired
        if not conv.choices:
            return self._reply(conv, ReplyKind.ERROR, "Aucune liste de contacts en attente.")
        if number == len(conv.choices) + 1:  # "Aucun de ceux-là"
            conv.choices = []
            conv.needs_more_clues = True
            return self._ask_more_clues(conv, "D'accord.")
        if not 1 <= number <= len(conv.choices):
            return self._ask_choice(conv)

        chosen = conv.choices[number - 1]
        conv.recipient = chosen
        conv.choices = []
        if conv.recipient_hint:
            for heard in conv.recipient_hint.heard_names:
                self.memory.record(heard, chosen.email)
        try:
            return self._next_step(conv)
        except LLMError:
            return self._technical_error(conv)

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
        hint = e.recipient
        if hint and not hint.is_empty() and not self._is_current_recipient(conv, hint):
            previous = conv.recipient_hint
            if conv.recipient is None and previous is not None:
                hint = _combine_hints(previous, hint)  # new clues for the same search
            conv.recipient_hint = hint
            conv.recipient = None
            conv.choices = []
            conv.needs_more_clues = False
            conv.unconfirmed_email = None
        elif conv.unconfirmed_email and e.confirmation is not None:
            if e.confirmation:
                conv.recipient = _contact_for_new_address(
                    conv.unconfirmed_email, conv.recipient_hint
                )
            elif conv.recipient_hint:
                # Forget the rejected address, keep the other clues.
                conv.recipient_hint = conv.recipient_hint.model_copy(update={"email": None})
                conv.needs_more_clues = True
            conv.unconfirmed_email = None

        if e.subject:
            conv.subject = e.subject
        if e.intent:
            conv.intent = e.intent
        if e.tone:
            conv.tone = e.tone

    def _is_current_recipient(self, conv: Conversation, hint: RecipientHint) -> bool:
        """True if the hint just describes the recipient already chosen (no change)."""
        chosen = conv.recipient
        if chosen is None:
            return False
        if hint.email:
            return hint.email.strip().lower() == chosen.email.lower()
        if hint.heard_names:
            return any(
                name_similarity(name, chosen) >= SAME_RECIPIENT_NAME for name in hint.heard_names
            )
        return context_similarity(hint, chosen) >= SAME_RECIPIENT_CONTEXT

    def _next_step(self, conv: Conversation) -> AgentReply:
        """Deterministic decision: which question to ask, or write the draft."""
        if conv.recipient is None:
            return self._ask_about_recipient(conv)
        if not conv.intent:
            name = conv.recipient.display_name if conv.recipient else "ce contact"
            return self._reply(
                conv, ReplyKind.ASK_INTENT, f"Que voulez-vous dire à {name} dans ce mail ?"
            )
        return self._write_draft(conv)

    def _ask_about_recipient(self, conv: Conversation) -> AgentReply:
        """The question that leads the human to pick the recipient (never picked for them)."""
        if conv.choices:
            return self._ask_choice(conv)
        if conv.unconfirmed_email:
            return self._ask_confirm_email(conv)
        hint = conv.recipient_hint
        if conv.needs_more_clues:
            return self._ask_more_clues(conv, "")
        if hint is None or hint.is_empty():
            return self._reply(conv, ReplyKind.ASK_RECIPIENT, "À qui voulez-vous écrire ?")

        suggestions = suggest_recipients(
            hint,
            self.contacts.list_contacts(),
            self.clock(),
            self.scoring,
            self.memory.counts_for(hint.heard_names),
        )
        if suggestions:
            conv.choices = [s.contact for s in suggestions]
            return self._ask_choice(conv)
        if hint.email and is_email(hint.email):
            conv.unconfirmed_email = hint.email.strip().lower()
            return self._ask_confirm_email(conv)

        conv.needs_more_clues = True
        return self._ask_more_clues(
            conv, f"J'ai compris : {describe_hint(hint)}. Je ne trouve personne dans vos contacts."
        )

    def _ask_choice(self, conv: Conversation) -> AgentReply:
        lines = [
            f"{i}. {c.full_name} ({c.email})" if c.full_name else f"{i}. {c.email}"
            for i, c in enumerate(conv.choices, start=1)
        ]
        lines.append(f"{len(conv.choices) + 1}. Aucun de ceux-là")
        understood = describe_hint(conv.recipient_hint)
        return self._reply(
            conv,
            ReplyKind.ASK_CHOICE,
            f"J'ai compris : {understood}.\nÀ qui voulez-vous écrire ?\n" + "\n".join(lines),
        )

    def _ask_more_clues(self, conv: Conversation, intro: str) -> AgentReply:
        question = (
            "Pouvez-vous me donner son nom de famille, son entreprise, "
            "ou directement son adresse mail ?"
        )
        return self._reply(conv, ReplyKind.ASK_MORE_CLUES, f"{intro} {question}".strip())

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
        if conv.recipient.full_name:
            to = f"{conv.recipient.full_name} <{to}>"
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


def _combine_hints(previous: RecipientHint, new: RecipientHint) -> RecipientHint:
    """New clues complete the previous ones; what is repeated replaces the old value."""
    return RecipientHint(
        heard_names=new.heard_names or previous.heard_names,
        company=new.company or previous.company,
        other_clues=new.other_clues or previous.other_clues,
        email=new.email or previous.email,
    )


def _contact_for_new_address(email: str, hint: RecipientHint | None) -> Contact:
    """A confirmed address that is not in the contacts, named with what was heard."""
    name = hint.heard_names[0] if hint and hint.heard_names else ""
    first, _, last = name.partition(" ")
    return Contact(email=email, first_name=first, last_name=last)
