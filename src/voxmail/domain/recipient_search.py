"""Rank the user's contacts by how well they match what the LLM heard.

Pure code, no AI. The result is a list of SUGGESTIONS: a human always picks one,
even when there is a single suggestion with a score of 99.

Score from 0 to 100 = weighted mix of:
- name: heard name vs first name, last name, full name, email local part
        (string similarity + French phonetic similarity);
- context: company or other clues vs the contact's company or email domain;
- habit: how often and how recently the user wrote to this contact;
plus a bonus for contacts the user already picked for the same heard name.
"""

import math
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from voxmail.domain.contacts import Contact, company_from_email, normalize
from voxmail.domain.phonetic import phonetic_key


class RecipientHint(BaseModel):
    """What the LLM thinks it heard about the recipient. It never contains a choice."""

    heard_names: list[str] = Field(
        default=[],
        description="Names heard, several hypotheses if the sound is ambiguous "
        "(e.g. ['Jacques', 'Jack']): first name only, last name only or full name.",
    )
    company: str | None = Field(default=None, description="Company mentioned, e.g. 'Mecalux'.")
    other_clues: str | None = Field(
        default=None,
        description="Any other clue, e.g. 'mon comptable', 'le client de Tours'.",
    )
    email: str | None = Field(
        default=None,
        description="Email address if the user gave one. Dictated addresses must be "
        "converted ('jean point dupont arobase gmail point com' -> 'jean.dupont@gmail.com').",
    )

    def is_empty(self) -> bool:
        return not (self.heard_names or self.company or self.other_clues or self.email)


@dataclass(frozen=True)
class ScoringConfig:
    """Tuning knobs, adjusted with the evaluation scenarios."""

    name_weight: float = 0.60
    context_weight: float = 0.25
    habit_weight: float = 0.15
    min_score: float = 50.0
    max_suggestions: int = 5
    learned_bonus_per_choice: float = 8.0
    learned_bonus_max: float = 20.0
    # A contact is only proposed if its NAME or its COMPANY really matches.
    # Habit and learned choices reorder contacts, they never qualify one alone.
    name_min_match: float = 0.75
    context_min_match: float = 0.75


DEFAULT_SCORING = ScoringConfig()


@dataclass(frozen=True)
class Suggestion:
    contact: Contact
    score: float


def _similarity(a: str, b: str) -> float:
    """0..1. Half spelling (Jaro-Winkler favors identical beginnings), half sound."""
    spelling = JaroWinkler.normalized_similarity(a, b)
    sound = JaroWinkler.normalized_similarity(phonetic_key(a), phonetic_key(b))
    return 0.5 * spelling + 0.5 * sound


def _local_part(email: str) -> str:
    return normalize(email.split("@", 1)[0])


def name_similarity(heard: str, contact: Contact) -> float:
    """0..1: how well ONE heard name matches the contact."""
    heard = normalize(heard)
    if not heard:
        return 0.0
    first, last = normalize(contact.first_name), normalize(contact.last_name)
    local = _local_part(contact.email)
    if " " not in heard:
        # One word: compare with each part of the name and of the email local part.
        targets = [first, last, *first.split(), *last.split(), *local.split()]
        targets.append(local.replace(" ", ""))  # "annesophie.dasilva" -> "annesophiedasilva"
        targets.append(last.replace(" ", ""))  # "da silva" -> "dasilva"
    else:
        # Several words: compare with whole names only, in both orders, and with
        # compound first or last names ("jacques edouard", "da silva").
        targets = [f"{first} {last}", f"{last} {first}", local]
        targets += [part for part in (first, last) if " " in part]
    return max((_similarity(heard, t) for t in targets if t), default=0.0)


def context_similarity(hint: RecipientHint, contact: Contact) -> float:
    """0..1: does the company or the clue match the contact's company or domain?"""
    clues = [normalize(c) for c in (hint.company, hint.other_clues) if c]
    targets = {normalize(t) for t in (contact.company, company_from_email(contact.email)) if t}
    targets = {t for t in targets if len(t) >= 3}
    if not clues or not targets:
        return 0.0
    return max(fuzz.token_set_ratio(t, clue) / 100 for t in targets for clue in clues)


def habit_score(contact: Contact, now: datetime) -> float:
    """0..1: frequent and recent exchanges score higher."""
    frequency = min(1.0, math.log1p(contact.interaction_count) / math.log1p(20))
    recency = 0.0
    if contact.last_interaction_at is not None:
        days = max(0.0, (now - contact.last_interaction_at).total_seconds() / 86400)
        recency = math.exp(-days / 60)
    return 0.6 * frequency + 0.4 * recency


def suggest_recipients(
    hint: RecipientHint,
    contacts: list[Contact],
    now: datetime,
    config: ScoringConfig = DEFAULT_SCORING,
    learned_choices: dict[str, int] | None = None,
) -> list[Suggestion]:
    """Best contacts first, at most `max_suggestions`, all above `min_score`.

    learned_choices: {email: number of times the user picked it for these heard names}.
    """
    learned_choices = learned_choices or {}
    if hint.email:
        wanted = hint.email.strip().lower()
        return [Suggestion(c, 100.0) for c in contacts if c.email.lower() == wanted]
    if not (hint.heard_names or hint.company or hint.other_clues):
        return []

    contexts = [context_similarity(hint, c) for c in contacts]
    use_context = bool(contexts) and max(contexts) >= config.context_min_match
    use_names = bool(hint.heard_names)
    if not (use_names or use_context):
        return []  # only a clue that matches nobody: nothing to propose

    # When one part is missing, its weight goes to the other one.
    name_weight = config.name_weight + (0 if use_context else config.context_weight)
    context_weight = config.context_weight + (0 if use_names else config.name_weight)

    suggestions = []
    for contact, context in zip(contacts, contexts, strict=True):
        name = 0.0
        if use_names:
            name = max(name_similarity(heard, contact) for heard in hint.heard_names)
        name_ok = use_names and name >= config.name_min_match
        context_ok = use_context and context >= config.context_min_match
        if not (name_ok or context_ok):
            continue

        score = config.habit_weight * habit_score(contact, now)
        if use_names:
            score += name_weight * name
        if use_context:
            score += context_weight * context
        score *= 100
        times_chosen = learned_choices.get(contact.email, 0)
        score += min(config.learned_bonus_max, config.learned_bonus_per_choice * times_chosen)
        suggestions.append(Suggestion(contact, min(100.0, score)))

    suggestions = [s for s in suggestions if s.score >= config.min_score]
    suggestions.sort(key=lambda s: s.score, reverse=True)
    return suggestions[: config.max_suggestions]
