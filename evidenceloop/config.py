from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str = ""
    google_api_key: str = ""
    tavily_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"
    gemini_schema_style: str = "legacy"
    gemini_fallback_mode: str = "fixture"
    research_quota_mode: str = "standard"
    database_path: str = "data/evidenceloop.sqlite3"
    max_searches: int = Field(default=4, ge=2, le=8)
    max_sources: int = Field(default=8, ge=3, le=16)
    max_claims: int = Field(default=8, ge=1, le=8)
    fetch_concurrency: int = Field(default=4, ge=1, le=8)
    run_timeout_seconds: int = Field(default=600, ge=10, le=1800)
    input_inr_per_million: float | None = None
    output_inr_per_million: float | None = None
    search_inr_per_credit: float | None = None

    @field_validator("input_inr_per_million", "output_inr_per_million", "search_inr_per_credit", mode="before")
    @classmethod
    def empty_price(cls, value):
        if value == "":
            return None
        if value is not None and float(value) < 0:
            raise ValueError("Price cannot be negative")
        return value

    @property
    def model_key(self):
        return self.gemini_api_key or self.google_api_key

    def missing(self):
        return (["GEMINI_API_KEY"] if not self.model_key else []) + (["TAVILY_API_KEY"] if not self.tavily_api_key else [])
