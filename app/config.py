"""Application settings, loaded from environment variables / a local .env file.

Nothing secret has a default: the app refuses to start without a real
DATABASE_URL and a strong SECRET_KEY.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values people copy out of tutorials/.env.example and forget to change.
_WEAK_SECRETS = {
    "changeme",
    "change-me",
    "secret",
    "secretkey",
    "your-secret-key",
    "replace-with-a-long-random-string",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # --- database -----------------------------------------------------
    DATABASE_URL: str
    DB_ECHO: bool = False

    # --- auth / JWT ---------------------------------------------------
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0, le=60 * 24)

    # --- login brute-force protection --------------------------------
    LOGIN_MAX_ATTEMPTS: int = Field(default=5, gt=0)
    LOGIN_LOCKOUT_SECONDS: int = Field(default=300, gt=0)

    # --- HTTP ---------------------------------------------------------
    # Comma-separated list of allowed browser origins. Empty = no CORS.
    CORS_ORIGINS: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_not_weak(cls, v: str) -> str:
        if v.strip().lower() in _WEAK_SECRETS:
            raise ValueError("SECRET_KEY is a well-known placeholder; generate a real one")
        return v

    @model_validator(mode="after")
    def _key_long_enough_for_algorithm(self) -> "Settings":
        # RFC 7518 s3.2: the HMAC key should be at least as long as the hash output.
        needed = {"HS256": 32, "HS384": 48, "HS512": 64}[self.JWT_ALGORITHM]
        if len(self.SECRET_KEY.encode()) < needed:
            raise ValueError(f"SECRET_KEY must be at least {needed} bytes for {self.JWT_ALGORITHM}")
        return self

    @model_validator(mode="after")
    def _production_rules(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if "*" in self.cors_origins_list:
                raise ValueError("CORS_ORIGINS must not contain '*' in production")
            if self.DB_ECHO:
                raise ValueError("DB_ECHO must be off in production (it logs SQL)")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def docs_enabled(self) -> bool:
        return self.ENVIRONMENT != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
