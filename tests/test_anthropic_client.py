"""Tests AnthropicLLM without network: a fake HTTP transport answers instead of the API."""

import json

import anthropic
import httpx2
import pytest

from voxmail.domain.models import EmailDraft
from voxmail.llm.anthropic_client import AnthropicLLM
from voxmail.llm.base import LLMError


def make_llm(text: str, stop_reason: str = "end_turn", status: int = 200) -> AnthropicLLM:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        assert body["output_config"]["format"]["type"] == "json_schema"
        return httpx2.Response(
            status,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "content": [{"type": "text", "text": text}],
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    llm = AnthropicLLM(api_key="sk-test", model="claude-opus-5")
    llm._client = anthropic.Anthropic(
        api_key="sk-test",
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    return llm


def test_returns_a_validated_pydantic_object():
    llm = make_llm(json.dumps({"subject": "Factures", "body": "Bonjour"}))
    draft = llm.generate("system", "user", EmailDraft)
    assert draft == EmailDraft(subject="Factures", body="Bonjour")


def test_refusal_raises_llm_error():
    llm = make_llm("", stop_reason="refusal")
    with pytest.raises(LLMError):
        llm.generate("system", "user", EmailDraft)


def test_api_error_raises_llm_error():
    llm = make_llm("{}", status=500)
    with pytest.raises(LLMError):
        llm.generate("system", "user", EmailDraft)
