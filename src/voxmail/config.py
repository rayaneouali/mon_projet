"""Application settings, read from environment variables (or a local .env file)."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration lives here. Never hardcode a secret in the code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # SecretStr hides the value when printed or logged: "**********".
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-5"

    user_signature: str = "Rayane Ouali"


def get_settings() -> Settings:
    return Settings()
