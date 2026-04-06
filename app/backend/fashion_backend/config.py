from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = Path(__file__).resolve().parents[3]
# Single env file for local dev, Vite, and Docker Compose (see deploy/.env.example).
_ENV_FILE = _REPO_ROOT / "deploy" / ".env"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(_ROOT / 'data' / 'library.db').as_posix()}",
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    upload_dir: Path = Field(default=_ROOT / "uploads")
    data_dir: Path = Field(default=_ROOT / "data")

    api_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("API_HOST"))
    api_port: int = Field(default=8000, ge=1, le=65535, validation_alias=AliasChoices("API_PORT"))

    max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        ge=1024,
        validation_alias=AliasChoices("MAX_UPLOAD_BYTES"),
    )

    # OpenRouter (preferred when set): OpenAI-compatible API at openrouter.ai
    openrouter_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENROUTER_API_KEY"))
    # Direct OpenAI (when OpenRouter key is unset)
    openai_api_key: str | None = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY"))
    # Override base URL for any OpenAI-compatible provider (e.g. Azure). If unset, OpenRouter uses default base.
    # Use https://openrouter.ai/api/v1 — not .../chat/completions (the SDK adds that path). OPENROUTER_URL is accepted
    # and normalized the same way if you paste the full chat URL.
    llm_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENROUTER_URL"),
    )
    # Vision model id. Unset = fast default per provider (Gemini 2.0 Flash on OpenRouter, gpt-4o-mini on OpenAI).
    vision_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VISION_MODEL", "OPENAI_MODEL"),
    )
    openrouter_site_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_SITE_URL"),
        description="Optional site URL for OpenRouter rankings (HTTP-Referer).",
    )
    openrouter_app_name: str = Field(
        default="Fashion Inspiration Library",
        validation_alias=AliasChoices("OPENROUTER_APP_NAME"),
    )

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )

    # httpx (LLM SDK). These are read from deploy/.env via pydantic — not only os.environ.
    httpx_trust_env: bool = Field(default=True, validation_alias=AliasChoices("HTTPX_TRUST_ENV"))
    httpx_no_keepalive: bool = Field(default=False, validation_alias=AliasChoices("HTTPX_NO_KEEPALIVE"))
    eval_import_delay_sec: float = Field(default=0.0, ge=0.0, validation_alias=AliasChoices("EVAL_IMPORT_DELAY_SEC"))

    @field_validator("httpx_trust_env", mode="before")
    @classmethod
    def _coerce_httpx_trust_env(cls, v: object) -> bool:
        if v is None or (isinstance(v, str) and not v.strip()):
            return True
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("0", "false", "no", "off"):
            return False
        return True

    @field_validator("llm_base_url", mode="after")
    @classmethod
    def _normalize_llm_base_url(cls, v: str | None) -> str | None:
        if not v or not str(v).strip():
            return None
        s = str(v).strip().rstrip("/")
        if s.endswith("/chat/completions"):
            s = s[: -len("/chat/completions")].rstrip("/")
        return s or None

    @field_validator("httpx_no_keepalive", mode="before")
    @classmethod
    def _coerce_httpx_no_keepalive(cls, v: object) -> bool:
        if v is None or (isinstance(v, str) and not v.strip()):
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator("upload_dir", "data_dir", mode="before")
    @classmethod
    def _anchor_relative_paths(cls, v: Path | str) -> Path:
        p = Path(v) if not isinstance(v, Path) else v
        if not p.is_absolute():
            return (_ROOT / p).resolve()
        return p

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_api_key(self) -> str | None:
        return self.openrouter_api_key or self.openai_api_key

    @property
    def llm_base_url_resolved(self) -> str | None:
        """None means OpenAI SDK default (https://api.openai.com/v1)."""
        if self.llm_base_url:
            return self.llm_base_url.rstrip("/")
        if self.openrouter_api_key:
            return _OPENROUTER_BASE
        return None

    @property
    def uses_openrouter(self) -> bool:
        base = (self.llm_base_url or "").lower()
        return bool(self.openrouter_api_key) or "openrouter.ai" in base

    @property
    def vision_model_resolved(self) -> str:
        if self.vision_model:
            return self.vision_model
        if self.uses_openrouter:
            return "google/gemini-2.0-flash-001"
        return "gpt-4o-mini"

    embedding_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_MODEL"),
    )

    @property
    def embedding_model_resolved(self) -> str:
        if self.embedding_model:
            return self.embedding_model
        if self.uses_openrouter:
            return "openai/text-embedding-3-small"
        return "text-embedding-3-small"

    @property
    def max_upload_mb(self) -> int:
        return max(1, self.max_upload_bytes // (1024 * 1024))


settings = Settings()
