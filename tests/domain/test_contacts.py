import pytest

from voxmail.domain.contacts import (
    Ambiguous,
    Candidate,
    Contact,
    Found,
    NewAddress,
    NotFound,
    normalize,
    resolve_recipient,
)

CONTACTS = [
    Contact("Jean Dupont", ("jean.dupont@btp-dupont.fr",)),
    Contact("Jean Martin", ("jmartin@gmail.com",)),
    Contact("Jeanne Durand", ("jeanne@durand-archi.fr",)),
    Contact("Hélène Lefèvre", ("helene.lefevre@mairie.fr",)),
    Contact("Karim Benali", ("karim@benali.fr", "k.benali@gmail.com")),
]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hélène", "helene"),
        ("  JEAN   Dupont ", "jean dupont"),
        ("Lefèvre", "lefevre"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_exact_full_name():
    result = resolve_recipient("Jean Dupont", CONTACTS)
    assert result == Found(Candidate("Jean Dupont", "jean.dupont@btp-dupont.fr"))


def test_name_without_accents_and_case():
    result = resolve_recipient("helene lefevre", CONTACTS)
    assert isinstance(result, Found)
    assert result.recipient.email == "helene.lefevre@mairie.fr"


def test_transcription_typo_is_tolerated():
    # "Dupond" instead of "Dupont": a classic speech-to-text mistake.
    result = resolve_recipient("Jean Dupond", CONTACTS)
    assert isinstance(result, Found)
    assert result.recipient.name == "Jean Dupont"


def test_last_name_only():
    result = resolve_recipient("Lefèvre", CONTACTS)
    assert isinstance(result, Found)
    assert result.recipient.name == "Hélène Lefèvre"


def test_homonyms_are_ambiguous():
    result = resolve_recipient("Jean", CONTACTS)
    assert isinstance(result, Ambiguous)
    names = {c.name for c in result.candidates}
    # Exact matches win: "Jeanne" is not proposed when real "Jean"s exist.
    assert names == {"Jean Dupont", "Jean Martin"}


def test_contact_with_several_addresses_is_ambiguous():
    result = resolve_recipient("Karim", CONTACTS)
    assert isinstance(result, Ambiguous)
    assert {c.email for c in result.candidates} == {"karim@benali.fr", "k.benali@gmail.com"}


def test_unknown_name():
    assert resolve_recipient("Sophie", CONTACTS) == NotFound("Sophie")


def test_empty_contact_book():
    assert resolve_recipient("Jean", []) == NotFound("Jean")


def test_known_email_address():
    result = resolve_recipient("JMartin@gmail.com", CONTACTS)
    assert result == Found(Candidate("Jean Martin", "jmartin@gmail.com"))


def test_new_email_address_needs_confirmation():
    result = resolve_recipient("contact@nouveau-client.fr", CONTACTS)
    assert result == NewAddress("contact@nouveau-client.fr")
