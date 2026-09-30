"""Remembers which contact the user picked for a heard name, to rank it higher next time.

It only gives a bonus: a remembered contact is still just a suggestion.
Phase 2 will store this in PostgreSQL, per user.
"""

from collections import Counter, defaultdict
from typing import Protocol

from voxmail.domain.contacts import normalize


class ChoiceMemory(Protocol):
    def record(self, heard_name: str, email: str) -> None: ...

    def counts_for(self, heard_names: list[str]) -> dict[str, int]: ...


class InMemoryChoiceMemory:
    def __init__(self) -> None:
        self._choices: defaultdict[str, Counter[str]] = defaultdict(Counter)

    def record(self, heard_name: str, email: str) -> None:
        key = normalize(heard_name)
        if key:
            self._choices[key][email] += 1

    def counts_for(self, heard_names: list[str]) -> dict[str, int]:
        """{email: times picked} summed over all the heard names."""
        total: Counter[str] = Counter()
        for name in heard_names:
            total.update(self._choices.get(normalize(name), Counter()))
        return dict(total)
