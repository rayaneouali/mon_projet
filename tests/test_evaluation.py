from pathlib import Path

import pytest
from pydantic import ValidationError

from voxmail.contacts.directory import JsonContactDirectory
from voxmail.domain.models import EmailDraft, Extraction
from voxmail.domain.recipient_search import RecipientHint
from voxmail.evaluation import Scenario, Turn, load_scenarios, run_scenario
from voxmail.llm.fake import FakeLLM

ROOT = Path(__file__).parent.parent
CONTACTS = JsonContactDirectory(ROOT / "data" / "fake_contacts.json")


def test_all_scenario_files_are_valid():
    scenarios = load_scenarios(ROOT / "evals" / "scenarios")
    assert len(scenarios) >= 30
    ids = [s.id for s in scenarios]
    assert len(ids) == len(set(ids)), "scenario ids must be unique"


def test_a_turn_needs_exactly_one_step():
    with pytest.raises(ValidationError):
        Turn(user="bonjour", wait=3)


def make_scenario(expect):
    return Scenario.model_validate(
        {
            "id": "t",
            "category": "test",
            "description": "test",
            "turns": [
                {
                    "user": "mail à Sophie Garnier pour les factures",
                    "expect": {
                        "reply_kind": "ask_choice",
                        "top_proposal": "s.garnier@comptable-garnier.fr",
                        "proposals_include": ["s.garnier@comptable-garnier.fr"],
                    },
                },
                {"choose": "s.garnier@comptable-garnier.fr", "expect": expect},
                {"action": "send", "expect": {"state": "pending_send"}},
                {"wait": 31, "expect": {"state": "sent", "reply_kind": "sent"}},
            ],
        }
    )


def fake_llm():
    return FakeLLM(
        [
            Extraction(
                recipient=RecipientHint(heard_names=["Sophie Garnier"]),
                intent="envoyer les factures",
            ),
            EmailDraft(subject="Factures", body="Bonjour Madame Garnier, voici les factures."),
        ]
    )


def test_runner_passes_a_correct_scenario():
    expect = {
        "state": "awaiting_validation",
        "recipient_email": "s.garnier@comptable-garnier.fr",
        "body_contains": ["FACTURES", "garnier|dupont"],
    }
    result = run_scenario(make_scenario(expect), fake_llm(), CONTACTS)
    assert result.passed, result.failures


def test_runner_fails_when_the_contact_to_choose_is_not_proposed():
    scenario = Scenario.model_validate(
        {
            "id": "t",
            "category": "test",
            "description": "test",
            "turns": [
                {"user": "mail à Sophie Garnier"},
                {"choose": "someone@else.fr"},
            ],
        }
    )
    result = run_scenario(scenario, fake_llm(), CONTACTS)
    assert not result.passed
    assert "not in" in result.failures[0]


def test_runner_reports_failures():
    expect = {"recipient_email": "someone@else.fr", "body_contains": ["virement"]}
    result = run_scenario(make_scenario(expect), fake_llm(), CONTACTS)
    assert not result.passed
    assert len(result.failures) == 2
