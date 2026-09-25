"""LLMClient implementation using the Anthropic API (Claude) with structured outputs."""

import anthropic
from pydantic import BaseModel, ValidationError

from voxmail.llm.base import LLMError


class AnthropicLLM:
    def __init__(self, api_key: str, model: str, max_tokens: int = 16000) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def generate[T: BaseModel](self, system: str, user: str, output_type: type[T]) -> T:
        try:
            # messages.parse asks Claude for JSON matching output_type
            # and validates it with Pydantic.
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=output_type,
            )
        except anthropic.APIError as error:
            raise LLMError(f"Anthropic API error: {error}") from error
        except ValidationError as error:
            # Invalid or truncated JSON (e.g. refusal or max_tokens reached).
            raise LLMError(f"Invalid structured output: {error}") from error

        if response.stop_reason == "refusal":
            raise LLMError("The model refused the request")
        if response.parsed_output is None:
            raise LLMError(f"No structured output (stop_reason={response.stop_reason})")
        return response.parsed_output
