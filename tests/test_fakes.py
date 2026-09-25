import pytest

from voxmail.domain.models import EmailDraft, Extraction
from voxmail.llm.fake import FakeLLM
from voxmail.mail.sender import FakeMailSender, OutgoingEmail


def test_fake_sender_is_idempotent():
    sender = FakeMailSender()
    email = OutgoingEmail(to="a@b.fr", subject="s", body="b")
    sender.send(email, "key-1")
    sender.send(email, "key-1")
    sender.send(email, "key-2")
    assert list(sender.sent) == ["key-1", "key-2"]


def test_fake_llm_checks_the_requested_type():
    llm = FakeLLM([Extraction()])
    with pytest.raises(AssertionError):
        llm.generate("system", "user", EmailDraft)
