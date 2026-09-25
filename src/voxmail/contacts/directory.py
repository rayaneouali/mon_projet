import json
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
    """Reads contacts from a JSON file: [{"name": "...", "emails": ["..."]}, ...]."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def list_contacts(self) -> list[Contact]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [Contact(name=item["name"], emails=tuple(item["emails"])) for item in raw]
