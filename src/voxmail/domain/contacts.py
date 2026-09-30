"""Contacts of the user and text normalization. One Contact = one email address."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

# Simple shape check: something@something.something, no spaces.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Consumer email providers: their domain says nothing about the company.
PUBLIC_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.fr",
        "outlook.com",
        "outlook.fr",
        "live.com",
        "live.fr",
        "msn.com",
        "yahoo.com",
        "yahoo.fr",
        "icloud.com",
        "me.com",
        "orange.fr",
        "wanadoo.fr",
        "free.fr",
        "sfr.fr",
        "neuf.fr",
        "laposte.net",
        "bbox.fr",
        "aol.com",
        "proton.me",
        "protonmail.com",
    }
)


def normalize(text: str) -> str:
    """Lowercase, no accents, hyphens/apostrophes/dots removed, single spaces.

    'Jacques-Édouard  LEFÈVRE' -> 'jacques edouard lefevre'
    """
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = without_accents.lower().replace("'", "").replace("’", "")
    return " ".join(re.sub(r"[-_.]", " ", lowered).split())


def is_email(text: str) -> bool:
    return EMAIL_PATTERN.match(text.strip()) is not None


def company_from_email(email: str) -> str | None:
    """'j.bertin@mecalux.fr' -> 'mecalux'; None for gmail.com, orange.fr..."""
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in PUBLIC_EMAIL_DOMAINS:
        return None
    name = domain.rsplit(".", 1)[0]  # drop the extension (.fr, .com...)
    return normalize(name) or None


@dataclass(frozen=True)
class Contact:
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str | None = None
    interaction_count: int = 0
    last_interaction_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        return self.full_name or self.email

    @property
    def effective_company(self) -> str | None:
        """The company given in the contact, or else the one guessed from the domain."""
        return self.company or company_from_email(self.email)
