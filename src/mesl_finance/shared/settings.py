from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings (prefix MESL_). Secrets never have defaults."""

    model_config = SettingsConfigDict(env_prefix="MESL_", env_file=".env", extra="ignore")

    database_url: str  # postgresql+asyncpg://labapp:...@host:5432/dbname  (the limited app role)
    admin_database_url: SecretStr  # owner/superuser DSN; migrations, bootstrap and tests only
    jwt_secret: SecretStr
    jwt_ttl_hours: int = 72
    auth_username: str
    auth_password_hash: (
        SecretStr  # argon2 hash; make one with: python -m mesl_finance.auth.infrastructure.hash_cli
    )
    timezone: str = "Asia/Dhaka"
    cors_origins: list[str] = []  # MESL_CORS_ORIGINS: JSON list; allowed browser origins

    @field_validator("jwt_secret")
    @classmethod
    def _secret_is_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("MESL_JWT_SECRET must be at least 32 characters")
        return value
