from datetime import UTC, datetime
from pathlib import Path

import pytest
from recipient_cases import CASES, NO_MATCH

from voxmail.contacts.directory import JsonContactDirectory
from voxmail.domain.contacts import Contact
from voxmail.domain.recipient_search import (
    RecipientHint,
    ScoringConfig,
    suggest_recipients,
)

NOW = datetime(2026, 3, 2, tzinfo=UTC)
CONTACTS = JsonContactDirectory(
    Path(__file__).parents[2] / "data" / "fake_contacts.json"
).list_contacts()


def emails(hint, **kwargs):
    return [s.contact.email for s in suggest_recipients(hint, CONTACTS, NOW, **kwargs)]


def test_address_book_is_big_enough():
    assert len(CONTACTS) >= 30


def test_success_criteria_on_all_cases():
    """Spec: right contact proposed in >= 95 % of cases, ranked first in >= 80 %."""
    results = [emails(hint) for _, hint, _ in CASES]
    proposed = sum(expected in r for r, (_, _, expected) in zip(results, CASES, strict=True))
    first = sum(r[:1] == [expected] for r, (_, _, expected) in zip(results, CASES, strict=True))
    assert proposed / len(CASES) >= 0.95, f"proposed {proposed}/{len(CASES)}"
    assert first / len(CASES) >= 0.80, f"first {first}/{len(CASES)}"


@pytest.mark.parametrize(("description", "hint", "expected"), CASES, ids=[c[0] for c in CASES])
def test_expected_contact_is_proposed(description, hint, expected):
    assert expected in emails(hint)


@pytest.mark.parametrize(("description", "hint"), NO_MATCH, ids=[c[0] for c in NO_MATCH])
def test_no_relevant_contact_gives_no_suggestion(description, hint):
    assert emails(hint) == []


def test_homonyms_are_all_proposed():
    result = emails(RecipientHint(heard_names=["Jacques"], company="Mecalux"))
    assert result[:2] == ["jacques.mauger@mecalux.fr", "j.bertin@mecalux.fr"]


def test_company_only_proposes_the_company_contacts():
    result = emails(RecipientHint(company="Mecalux"))
    assert set(result) == {
        "jacques.mauger@mecalux.fr",
        "j.bertin@mecalux.fr",
        "s.colas@mecalux.fr",
        "compta@mecalux.fr",
    }


def test_at_most_max_suggestions_sorted_by_score():
    suggestions = suggest_recipients(
        RecipientHint(heard_names=["Jean"]), CONTACTS, NOW, ScoringConfig(max_suggestions=2)
    )
    assert len(suggestions) == 2
    assert suggestions[0].score >= suggestions[1].score


def test_learned_choice_moves_a_contact_up():
    hint = RecipientHint(heard_names=["Jean"])
    assert emails(hint)[0] == "jean.dupont@btp-dupont.fr"
    learned = {"jmartin@gmail.com": 2}
    assert emails(hint, learned_choices=learned)[0] == "jmartin@gmail.com"


def test_learned_choice_alone_never_qualifies_a_contact():
    learned = {"lucas.bernard@gmail.com": 50}
    assert emails(RecipientHint(heard_names=["Zébulon"]), learned_choices=learned) == []


def test_email_hint_only_matches_that_exact_address():
    assert emails(RecipientHint(email="JMartin@gmail.com")) == ["jmartin@gmail.com"]
    assert emails(RecipientHint(email="new@unknown.fr")) == []


def test_empty_hint_gives_nothing():
    assert emails(RecipientHint()) == []


def test_contact_without_name_is_found_by_email_local_part():
    contacts = [Contact(email="compta@mecalux.fr")]
    result = suggest_recipients(RecipientHint(heard_names=["compta"]), contacts, NOW)
    assert [s.contact.email for s in result] == ["compta@mecalux.fr"]
