"""Find the right recipient in the user's contacts, without any LLM.

The result is always one of four cases (Found, Ambiguous, NotFound, NewAddress),
so the agent knows exactly whether it can continue or must ask a question.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

# Minimum similarity (0 to 1) for two names to be considered a match.
MATCH_THRESHOLD = 0.8

# Simple shape check: something@something.something, no spaces.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Contact:
    name: str
    emails: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    """One possible recipient: a contact and one of its email addresses."""

    name: str
    email: str


@dataclass(frozen=True)
class Found:
    recipient: Candidate


@dataclass(frozen=True)
class Ambiguous:
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class NotFound:
    query: str


@dataclass(frozen=True)
class NewAddress:
    """An email address never seen before: its spelling must be confirmed."""

    email: str


Resolution = Found | Ambiguous | NotFound | NewAddress


def normalize(text: str) -> str:
    """Lowercase, remove accents and extra spaces: ' Hélène  DUPONT ' -> 'helene dupont'."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def name_score(query: str, contact_name: str) -> float:
    """How well `query` matches a contact name, from 0 to 1.

    A one-word query ("Dupont", "Jean") is also compared to each part of the name.
    """
    query, name = normalize(query), normalize(contact_name)
    scores = [similarity(query, name)]
    if " " not in query:
        scores += [similarity(query, part) for part in name.split()]
    return max(scores)


def is_email(text: str) -> bool:
    return EMAIL_PATTERN.match(text.strip()) is not None


def resolve_recipient(query: str, contacts: list[Contact]) -> Resolution:
    query = query.strip()

    if is_email(query):
        email = query.lower()
        for contact in contacts:
            if email in (e.lower() for e in contact.emails):
                return Found(Candidate(contact.name, email))
        return NewAddress(email)

    scored = [(name_score(query, c.name), c) for c in contacts]
    matches = [(score, c) for score, c in scored if score >= MATCH_THRESHOLD]
    exact = [(score, c) for score, c in matches if score == 1.0]
    if exact:
        matches = exact

    matches.sort(key=lambda pair: pair[0], reverse=True)
    candidates = tuple(Candidate(c.name, email) for _, c in matches for email in c.emails)

    if not candidates:
        return NotFound(query)
    if len(candidates) == 1:
        return Found(candidates[0])
    return Ambiguous(candidates)
