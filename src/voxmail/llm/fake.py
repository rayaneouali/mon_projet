"""Fake LLM for tests: returns pre-written answers, in order, without any network."""

from pydantic import BaseModel

from voxmail.llm.base import LLMError


class FakeLLM:
    def __init__(self, responses: list[BaseModel | Exception] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[tuple[str, str]] = []  # (system, user) of every call

    def generate[T: BaseModel](self, system: str, user: str, output_type: type[T]) -> T:
        self.calls.append((system, user))
        if not self.responses:
            raise LLMError("FakeLLM has no response left")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, output_type):
            raise AssertionError(f"Expected {output_type.__name__}, got {type(response).__name__}")
        return response
