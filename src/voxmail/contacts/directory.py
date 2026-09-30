import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

from voxmail.domain.contacts import Contact


class ContactDirectory(Protocol):
    def list_contacts(self) -> list[Contact]: ...


class InMemoryContactDirectory:
    def __init__(self, contacts: list[Contact]) -> None:
        self._contacts = contacts

    def list_contacts(self) -> list[Contact]:
        return list(self._contacts)


class JsonContactDirectory:
    """Reads contacts from a JSON file (phase 1 fake address book)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def list_contacts(self) -> list[Contact]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [
            Contact(
                email=item["email"],
                first_name=item.get("first_name", ""),
                last_name=item.get("last_name", ""),
                company=item.get("company"),
                interaction_count=item.get("interaction_count", 0),
                last_interaction_at=(
                    datetime.fromisoformat(item["last_interaction_at"])
                    if item.get("last_interaction_at")
                    else None
                ),
            )
            for item in raw
        ]
