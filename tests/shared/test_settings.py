"""Roadmap 0.5: env-driven Settings.

Approved behaviours: required app/admin DSN, JWT secret, username, argon2 hash; 72 h TTL and
Asia/Dhaka defaults; MESL_ prefix plus .env file; unprefixed lookalikes ignored; secrets masked.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from mesl_finance.shared.settings import Settings

HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0c2FsdA$aGFzaGhhc2hoYXNoaGFzaGhhc2g"

REQUIRED_ENV: dict[str, str] = {
    "MESL_DATABASE_URL": "postgresql+asyncpg://labapp:app-secret@localhost:5432/mesl",
    "MESL_ADMIN_DATABASE_URL": "postgresql://postgres:admin-secret@localhost:5432/mesl",
    "MESL_JWT_SECRET": "s" * 32,
    "MESL_AUTH_USERNAME": "treasurer",
    "MESL_AUTH_PASSWORD_HASH": HASH,
}

NAME: list[tuple[str, str]] = [
    ("MESL_DATABASE_URL", "database_url"),
    ("MESL_ADMIN_DATABASE_URL", "admin_database_url"),
    ("MESL_JWT_SECRET", "jwt_secret"),
    ("MESL_AUTH_USERNAME", "auth_username"),
    ("MESL_AUTH_PASSWORD_HASH", "auth_password_hash"),
]


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ambient MESL_* or unprefixed DATABASE_URL env var can leak into a test."""
    for key in list(os.environ):
        if key.startswith("MESL_") or key == "DATABASE_URL":
            monkeypatch.delenv(key, raising=False)


def _set_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def _settings(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> Settings:
    _set_env(monkeypatch, REQUIRED_ENV)
    return Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_defaults(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(clean_env, monkeypatch)
    assert settings.jwt_ttl_hours == 72
    assert settings.timezone == "Asia/Dhaka"


def test_env_file_read_and_unprefixed_ignored(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text(
        "MESL_DATABASE_URL=postgresql+asyncpg://file:file-secret@localhost:5432/mesl\n"
        f"MESL_ADMIN_DATABASE_URL={REQUIRED_ENV['MESL_ADMIN_DATABASE_URL']}\n"
        f"MESL_JWT_SECRET={REQUIRED_ENV['MESL_JWT_SECRET']}\n"
        f"MESL_AUTH_USERNAME={REQUIRED_ENV['MESL_AUTH_USERNAME']}\n"
        f"MESL_AUTH_PASSWORD_HASH={HASH}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://no-prefix@localhost:5432/other")
    monkeypatch.chdir(tmp_path)
    settings = Settings()  # pyright: ignore[reportCallIssue]
    assert settings.database_url == "postgresql+asyncpg://file:file-secret@localhost:5432/mesl"
    assert settings.jwt_ttl_hours == 72


@pytest.mark.parametrize(("env_key", "field"), NAME)
def test_missing_required_field_raises(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, env_key: str, field: str
) -> None:
    _set_env(monkeypatch, {k: v for k, v in REQUIRED_ENV.items() if k != env_key})
    with pytest.raises(
        ValidationError,
    ) as info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert any(err["loc"] == (field,) and err["type"] == "missing" for err in info.value.errors())


def test_short_jwt_secret_rejected(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, {**REQUIRED_ENV, "MESL_JWT_SECRET": "too-short"})
    with pytest.raises(ValidationError) as info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert any(err["loc"] == ("jwt_secret",) for err in info.value.errors())
    assert "at least 32" in str(info.value)


CORS_ORIGINS_ENV = '["http://localhost:5173", "https://mesl.example"]'
CORS_ORIGINS = ["http://localhost:5173", "https://mesl.example"]


def test_cors_origins_defaults_to_an_empty_list(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved brief: without MESL_CORS_ORIGINS the origin list is [] — no CORS by default."""
    settings = _settings(clean_env, monkeypatch)
    assert settings.cors_origins == []


def test_cors_origins_parses_from_the_env(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Approved brief Q2=a: MESL_CORS_ORIGINS is a JSON list (pydantic-settings complex-field
    parsing, sources/base.py:212 json.loads) -> the origins list."""
    _set_env(monkeypatch, {**REQUIRED_ENV, "MESL_CORS_ORIGINS": CORS_ORIGINS_ENV})
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.cors_origins == CORS_ORIGINS


def test_secrets_masked_in_repr_and_recoverable(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(clean_env, monkeypatch)
    text = repr(settings)
    assert "SecretStr('**********')" in text
    assert "s" * 32 not in text
    assert "admin-secret" not in text
    assert HASH not in text
    assert settings.jwt_secret.get_secret_value() == REQUIRED_ENV["MESL_JWT_SECRET"]
    assert settings.admin_database_url.get_secret_value() == REQUIRED_ENV["MESL_ADMIN_DATABASE_URL"]
    assert settings.database_url == REQUIRED_ENV["MESL_DATABASE_URL"]
    assert settings.auth_password_hash.get_secret_value() == REQUIRED_ENV["MESL_AUTH_PASSWORD_HASH"]
