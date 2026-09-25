"""Instructions given to the LLM, and the text describing the current conversation."""

from voxmail.domain.models import Conversation

EXTRACTION_SYSTEM = """\
You help French small-business owners (craftsmen, site managers) send emails by \
voice or text. You receive the current state of an email request and ONE new \
message from the user (often a voice transcription, with mistakes).

Your only job: extract what this message says, as structured data. You never \
send anything and you never write the email here.

Rules:
- recipient: the name or email address the user wants to write to, as given. \
Only fill it if the message names a recipient (or a different one than before). \
If the user dictates an address ("jean point dupont arobase gmail point com", \
letters spelled one by one, "tiret" = "-", "tiret du bas" = "_"), convert it to \
a real address. Never invent an address.
- subject: only if the user explicitly gives a subject.
- intent: the full, up-to-date content the email must convey, in French, merging \
the intent already known with this message. Keep every concrete fact (dates, \
times, quantities, places, amounts). Leave null if what to say is still unknown \
or too vague to write an email ("préviens-le", "écris-lui").
- tone: "tu" only if the user asks to tutoyer or the relationship is clearly \
familiar; "vous" if the user asks to vouvoyer; otherwise null.
- choice: if the last question offered numbered options and the user picks one \
(by number, name, address or description), its number (1-based).
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


def describe_conversation(conversation: Conversation) -> str:
    """Summarize what is already known, so the LLM has the context of the message."""
    recipient = conversation.recipient
    lines = [
        f"- recipient requested: {conversation.recipient_query or 'unknown'}",
        f"- recipient resolved: {f'{recipient.name} <{recipient.email}>' if recipient else 'no'}",
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
    lines = [
        f"Recipient name: {recipient.name if recipient and recipient.name else 'unknown'}",
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
