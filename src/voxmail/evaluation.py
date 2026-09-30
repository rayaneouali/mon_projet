"""Replay realistic scenarios (YAML files) against the agent and check its behavior."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from voxmail.agent.agent import Agent
from voxmail.contacts.directory import ContactDirectory
from voxmail.domain.contacts import normalize
from voxmail.domain.models import Action, AgentReply, Conversation, ReplyKind
from voxmail.domain.recipient_search import DEFAULT_SCORING, ScoringConfig
from voxmail.domain.state_machine import ConversationState
from voxmail.llm.base import LLMClient
from voxmail.mail.sender import FakeMailSender


class Expect(BaseModel):
    """What must be true after a turn. Text checks ignore case and accents.
    In body_contains, "a|b" means "a or b"."""

    model_config = ConfigDict(extra="forbid")

    state: ConversationState | None = None
    reply_kind: list[ReplyKind] = []
    recipient_email: str | None = None
    pending_email: str | None = None
    choices_count: int | None = None
    proposals_include: list[str] = []
    top_proposal: str | None = None
    tone: Literal["vous", "tu"] | None = None
    subject_contains: list[str] = []
    body_contains: list[str] = []
    body_not_contains: list[str] = []

    @field_validator("reply_kind", mode="before")
    @classmethod
    def accept_single_kind(cls, value: object) -> object:
        return [value] if isinstance(value, str) else value


class Turn(BaseModel):
    """Exactly one of: a user message, a button press, picking the contact with this
    email in the proposed list (like a human tapping it), or waiting some seconds."""

    model_config = ConfigDict(extra="forbid")

    user: str | None = None
    action: Action | None = None
    choose: str | None = None
    wait: int | None = None
    expect: Expect = Expect()

    @model_validator(mode="after")
    def exactly_one_step(self) -> "Turn":
        steps = (self.user, self.action, self.choose, self.wait)
        if sum(x is not None for x in steps) != 1:
            raise ValueError("a turn needs exactly one of: user, action, choose, wait")
        return self


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    description: str
    turns: list[Turn]


@dataclass
class ScenarioResult:
    scenario: Scenario
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 3, 2, 8, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def load_scenarios(directory: Path) -> list[Scenario]:
    scenarios = []
    for path in sorted(directory.glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")):
            scenarios.append(Scenario.model_validate(raw))
    return scenarios


def _contains(text: str, pattern: str) -> bool:
    haystack = normalize(text)
    return any(normalize(option) in haystack for option in pattern.split("|"))


def check(expect: Expect, conv: Conversation, reply: AgentReply | None) -> list[str]:
    """Return the list of broken expectations (empty = all good)."""
    errors = []
    if expect.state and conv.state != expect.state:
        errors.append(f"state: expected {expect.state}, got {conv.state}")
    if expect.reply_kind and (reply is None or reply.kind not in expect.reply_kind):
        got = reply.kind if reply else None
        errors.append(f"reply_kind: expected {expect.reply_kind}, got {got}")
    if expect.recipient_email:
        got = conv.recipient.email if conv.recipient else None
        if got != expect.recipient_email:
            errors.append(f"recipient: expected {expect.recipient_email}, got {got}")
    if expect.pending_email and conv.unconfirmed_email != expect.pending_email:
        errors.append(
            f"pending_email: expected {expect.pending_email}, got {conv.unconfirmed_email}"
        )
    proposed = [c.email for c in conv.choices]
    if expect.choices_count is not None and len(proposed) != expect.choices_count:
        errors.append(f"choices: expected {expect.choices_count}, got {len(proposed)}")
    for email in expect.proposals_include:
        if email not in proposed:
            errors.append(f"proposals: {email} missing from {proposed}")
    if expect.top_proposal and proposed[:1] != [expect.top_proposal]:
        errors.append(f"top proposal: expected {expect.top_proposal}, got {proposed[:1]}")
    if expect.tone and conv.tone != expect.tone:
        errors.append(f"tone: expected {expect.tone}, got {conv.tone}")

    subject = conv.draft.subject if conv.draft else ""
    body = conv.draft.body if conv.draft else ""
    errors += [f"subject lacks '{p}'" for p in expect.subject_contains if not _contains(subject, p)]
    errors += [f"body lacks '{p}'" for p in expect.body_contains if not _contains(body, p)]
    errors += [f"body contains '{p}'" for p in expect.body_not_contains if _contains(body, p)]
    return errors


def run_scenario(
    scenario: Scenario,
    llm: LLMClient,
    contacts: ContactDirectory,
    scoring: ScoringConfig = DEFAULT_SCORING,
) -> ScenarioResult:
    clock = FakeClock()
    agent = Agent(llm, contacts, FakeMailSender(), "Rayane Ouali", clock=clock, scoring=scoring)
    conv = agent.start()
    result = ScenarioResult(scenario)

    for number, turn in enumerate(scenario.turns, start=1):
        reply: AgentReply | None
        try:
            if turn.user is not None:
                reply = agent.handle_text(conv, turn.user)
            elif turn.action is not None:
                reply = agent.handle_action(conv, turn.action)
            elif turn.choose is not None:
                proposed = [c.email for c in conv.choices]
                if turn.choose not in proposed:
                    result.failures.append(f"turn {number}: {turn.choose} not in {proposed}")
                    break
                reply = agent.handle_choice(conv, proposed.index(turn.choose) + 1)
            else:
                clock.now += timedelta(seconds=turn.wait or 0)
                reply = agent.process_due_send(conv)
        except Exception as error:  # a crash is a failed scenario, not a crashed run
            result.failures.append(f"turn {number}: crashed with {error!r}")
            break
        result.failures += [f"turn {number}: {e}" for e in check(turn.expect, conv, reply)]
        if result.failures:
            break  # later turns make no sense once the conversation went off track
    return result
