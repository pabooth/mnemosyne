from pydantic_settings import BaseSettings, SettingsConfigDict

_settings_override: "Settings | None" = None
_settings_cache: "Settings | None" = None


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
    # Root path inside the repo where docs are written, e.g. "kb/docs".
    # Leave empty to write directly into the Diataxis folders at the repo root.
    docs_root: str = ""

    # App
    frontend_origin: str = "http://localhost:8888"
    mnemo_api_token: str = ""
    mnemo_api_tokens: str = ""
    request_timeout_seconds: float = 120
    request_rate_limit_per_minute: int = 30
    request_max_concurrency: int = 4
    request_max_body_bytes: int = 2_000_000
    state_db_path: str = "./data/mnemosyne.db"
    job_max_attempts: int = 2
    job_retry_base_seconds: float = 1

    # GitHub webhook intake
    github_webhook_secret: str = ""
    github_webhook_branch: str = "main"
    github_webhook_path_prefix: str = ""
    github_webhook_max_files: int = 20
    source_url_allowed_hosts: str = ""

    # Observability — empty string disables OTel
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "mnemo-core"
    log_level: str = "INFO"

    # Vector index (ADR-014) — embedded sqlite-vec by default; empty
    # vector_db_path reuses the same SQLite file as durable job storage.
    vector_store: str = "sqlite-vec"
    vector_db_path: str = ""
    vector_embedding_dim: int = 1536

    # Embedding provider — independent from LLM_PROVIDER since not every
    # LLM provider (e.g. Anthropic, DeepSeek) offers an embeddings API.
    embedding_provider: str = "openai"
    embedding_openai_model: str = "text-embedding-3-small"
    embedding_ollama_model: str = "nomic-embed-text"

    # Indexer (ADR-012/ADR-014)
    index_max_files: int = 2000


def get_settings() -> Settings:
    global _settings_cache
    if _settings_override is not None:
        return _settings_override
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache


def configure_settings(override: Settings | None) -> None:
    global _settings_override
    _settings_override = override
