from pydantic_settings import BaseSettings, SettingsConfigDict

_settings_override: "Settings | None" = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider selection
    llm_provider: str = "anthropic"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # OpenAI-compatible (covers OpenAI, Azure OpenAI, custom endpoints)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # DeepSeek (OpenAI-compatible API, different base URL)
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # Ollama (no API key — served via OpenAI-compat endpoint)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # GitHub — required for the internal publish step used by ingest
    github_token: str = ""
    github_repo: str = ""

    # App
    frontend_origin: str = "http://localhost:7000"
    mnemo_api_token: str = ""

    # Observability — empty string disables OTel
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "mnemo-core"


settings = Settings()


def get_settings() -> Settings:
    return _settings_override or settings


def configure_settings(override: Settings | None) -> None:
    global _settings_override
    _settings_override = override
