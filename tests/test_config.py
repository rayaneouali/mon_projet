from voxmail.config import Settings


def test_settings_have_safe_defaults(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_env == "local"
    assert settings.anthropic_api_key is None


def test_settings_read_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-fake"


def test_secret_is_hidden_when_printed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    settings = Settings(_env_file=None)
    assert "sk-fake" not in str(settings)
