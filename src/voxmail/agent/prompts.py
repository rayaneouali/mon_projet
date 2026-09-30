"""Instructions given to the LLM, and the text describing the current conversation."""

from voxmail.domain.models import Conversation
from voxmail.domain.recipient_search import RecipientHint

EXTRACTION_SYSTEM = """\
You help French small-business owners (craftsmen, site managers) send emails by \
voice or text. You receive the current state of an email request and ONE new \
message from the user (often a voice transcription, with mistakes).

Your only job: extract what this message says, as structured data. You never \
send anything and you never write the email here.

Rules:
- recipient: fill it ONLY if this message mentions who to write to. You never \
choose a contact and never invent an address: you report what you heard.
  - heard_names: the names heard. If the sound is ambiguous or the transcription \
looks wrong, give several hypotheses (e.g. ["Jacques", "Jack"], ["Mauger", "Mojé"]).
  - company: a company mentioned ("de chez Mecalux" -> "Mecalux").
  - other_clues: any other clue ("mon comptable", "le client de Tours").
  - email: an address given or dictated, converted to a real address \
("jean point dupont arobase gmail point com" -> "jean.dupont@gmail.com", letters \
spelled one by one, "tiret" = "-", "tiret du bas" = "_").
  If the last question offered a numbered list of contacts and the user answers \
with words instead of a number, report their words as new clues in recipient.
- subject: only if the user explicitly gives a subject.
- intent: the full, up-to-date content the email must convey, in French, merging \
the intent already known with this message. Keep every concrete fact (dates, \
times, quantities, places, amounts). Leave null if what to say is still unknown \
or too vague to write an email ("préviens-le", "écris-lui").
- tone: "tu" only if the user asks to tutoyer or the relationship is clearly \
familiar; "vous" if the user asks to vouvoyer; otherwise null.
- confirmation: if the last question was a yes/no question, true for yes, false for no.
- cancel: true if the user wants to abandon this email.
- wants_to_send: true if the user asks in words to send the email ("envoie", "c'est bon").
- edit_instruction: only when a draft exists: what the user wants changed, in French.
- unclear: true ONLY if the message is garbled or incoherent, not merely \
incomplete. Then put in reformulation what you think the user meant, in French.
"""

WRITER_SYSTEM = """\
You write professional emails in French on behalf of a French small-business \
owner (often a craftsman or site manager).

Rules:
- Use "vous" unless the requested tone is "tu".
- Start with a greeting using the recipient's name when known \
("Bonjour Monsieur Dupont," or "Bonjour Jean," when using "tu"; \
"Bonjour," when the name is unknown).
- Say exactly what the intent says: keep every date, time, quantity, place and \
amount. Never invent facts, prices, dates or promises that are not in the intent.
- Be clear and concise: short paragraphs, no jargon, polite closing formula.
- Do NOT add a signature or the sender's name: it is added automatically.
- If a subject is given, keep it (you may only fix spelling or capitalization). \
Otherwise write a short, specific subject.
- If a previous draft and a change request are given, apply the change to the \
previous draft and keep the rest as it was.
"""


def describe_hint(hint: RecipientHint | None) -> str:
    """'« Jacques » ou « Jack », de chez Mecalux' — what was understood about the recipient."""
    if hint is None or hint.is_empty():
        return "personne"
    parts = []
    if hint.heard_names:
        parts.append(" ou ".join(f"« {name} »" for name in hint.heard_names))
    if hint.email:
        parts.append(f"l'adresse {hint.email}")
    if hint.company:
        parts.append(f"de chez {hint.company}")
    if hint.other_clues:
        parts.append(f"({hint.other_clues})")
    return ", ".join(parts)


def describe_conversation(conversation: Conversation) -> str:
    """Summarize what is already known, so the LLM has the context of the message."""
    recipient = conversation.recipient
    chosen = f"{recipient.display_name} <{recipient.email}>" if recipient else "not yet"
    lines = [
        f"- recipient heard so far: {describe_hint(conversation.recipient_hint)}",
        f"- recipient chosen by the user: {chosen}",
        f"- subject: {conversation.subject or 'unknown'}",
        f"- intent: {conversation.intent or 'unknown'}",
        f"- tone: {conversation.tone}",
    ]
    if conversation.draft:
        lines.append(
            f"- current draft (waiting for validation):\n"
            f"  subject: {conversation.draft.subject}\n  body: {conversation.draft.body}"
        )
    lines.append(f"- last question asked to the user: {conversation.last_agent_message or 'none'}")
    return "Current state of the email request:\n" + "\n".join(lines)


def extraction_input(conversation: Conversation, message: str) -> str:
    return f'{describe_conversation(conversation)}\n\nNew user message:\n"""{message}"""'


def writer_input(conversation: Conversation) -> str:
    recipient = conversation.recipient
    name = recipient.full_name if recipient and recipient.full_name else "unknown"
    lines = [
        f"Recipient name: {name}",
        f"Tone: {conversation.tone}",
        f"Subject: {conversation.subject or 'none given'}",
        f"Intent: {conversation.intent}",
    ]
    if conversation.draft and conversation.pending_edit:
        lines += [
            "",
            "Previous draft:",
            f"subject: {conversation.draft.subject}",
            f"body: {conversation.draft.body}",
            "",
            f"Change requested by the user: {conversation.pending_edit}",
        ]
    return "\n".join(lines)
