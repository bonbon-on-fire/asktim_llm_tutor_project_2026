"""Environment-driven configuration for test_ui."""

from __future__ import annotations

import os
from dataclasses import dataclass


_DEFAULT_COOKIE_MAX_AGE_SECONDS = 180 * 24 * 3600  # 180 days


def _parse_bool(raw: str, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class Config:
    secret_key: str
    database_url: str
    port: int
    cookie_secure: bool
    cookie_max_age_seconds: int


def load_config() -> Config:
    secret_key = os.environ.get("TEST_UI_SECRET_KEY", "dev-insecure-key")
    # Own DB, kept separate from main_ui's DATABASE_URL so test conversations
    # never land in the production student store. Defaults to a local SQLite file.
    database_url = os.environ.get("TEST_UI_DATABASE_URL", "sqlite:///./test_ui.db")
    port = int(os.environ.get("PORT", "5000"))
    # This is a local developer/TA tool, usually served over plain http on
    # localhost, so cookies must not require Secure by default or identity +
    # history wouldn't stick. Override with TEST_UI_COOKIE_SECURE=true behind HTTPS.
    cookie_secure = _parse_bool(os.environ.get("TEST_UI_COOKIE_SECURE"), default=False)
    cookie_max_age_seconds = int(
        os.environ.get("TEST_UI_COOKIE_MAX_AGE", str(_DEFAULT_COOKIE_MAX_AGE_SECONDS))
    )
    return Config(
        secret_key=secret_key,
        database_url=database_url,
        port=port,
        cookie_secure=cookie_secure,
        cookie_max_age_seconds=cookie_max_age_seconds,
    )
