"""The only thing the agent knows about an LLM: give it instructions and a text,
get back an object validated by Pydantic. Changing provider = one new class."""

from typing import Protocol

from pydantic import BaseModel


class LLMError(Exception):
    """The LLM call failed (network, refusal, invalid output...)."""


class LLMClient(Protocol):
    def generate[T: BaseModel](self, system: str, user: str, output_type: type[T]) -> T: ...
