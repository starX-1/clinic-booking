import re
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOCAL_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/clinic_db"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinic Booking API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database settings - Loaded dynamically from .env or system environment
    DATABASE_URL: str = DEFAULT_LOCAL_DB_URL

    # Business constraints
    SLOT_DURATION_MINUTES: int = 30
    MIN_ADVANCE_BOOKING_HOURS: int = 1

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if not v or not isinstance(v, str) or v.strip() == "":
            v = DEFAULT_LOCAL_DB_URL

        if isinstance(v, str):
            # Normalize Neon DB / standard postgres URL scheme for SQLAlchemy + asyncpg
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

            # Strip libpq-specific parameters like channel_binding that asyncpg does not support
            v = re.sub(r"[?&]channel_binding=[^&]*", "", v)

            # Convert sslmode query param to ssl parameter for asyncpg compatibility
            if "sslmode=" in v:
                v = v.replace("sslmode=require", "ssl=require")
                v = v.replace("sslmode=prefer", "ssl=require")
                v = v.replace("sslmode=disable", "ssl=disable")
                v = v.replace("sslmode=verify-full", "ssl=require")
                v = v.replace("sslmode=verify-ca", "ssl=require")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
