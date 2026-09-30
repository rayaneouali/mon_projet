"""Application settings, read from environment variables (or a local .env file)."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from voxmail.domain.recipient_search import ScoringConfig


class Settings(BaseSettings):
    """All configuration lives here. Never hardcode a secret in the code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # SecretStr hides the value when printed or logged: "**********".
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5"

    user_signature: str = "Rayane Ouali"
    contacts_file: Path = Path("data/fake_contacts.json")
    send_delay_seconds: int = 30

    # Recipient suggestions: weights (name + context + habit = 1) and limits.
    recipient_name_weight: float = 0.60
    recipient_context_weight: float = 0.25
    recipient_habit_weight: float = 0.15
    recipient_min_score: float = 50.0
    recipient_max_suggestions: int = 5

    def scoring(self) -> ScoringConfig:
        return ScoringConfig(
            name_weight=self.recipient_name_weight,
            context_weight=self.recipient_context_weight,
            habit_weight=self.recipient_habit_weight,
            min_score=self.recipient_min_score,
            max_suggestions=self.recipient_max_suggestions,
        )


def get_settings() -> Settings:
    return Settings()
