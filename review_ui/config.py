"""Environment-driven configuration for review_ui.

One codebase, deployed twice. Everything that differs between the Sandbox and
normal deployments is an env var: which database to read, the title shown in the
header / browser tab, and the color theme. See ``docs/review_ui_plan.md``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


_DEFAULT_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 3600  # 30 days


@dataclass(frozen=True)
class Config:
    database_url: str
    title: str
    theme: str
    accent: str | None
    password: str | None
    secret_key: str
    port: int
    cookie_max_age_seconds: int


def load_config() -> Config:
    # Resolution order: REVIEW_DATABASE_URL (explicit, wins) -> DATABASE_URL
    # (shared name; on Railway each service resolves it to its own referenced DB)
    # -> local SQLite for offline dev. For local runs against a Railway DB, point
    # REVIEW_DATABASE_URL at the *public* proxy URL (DATABASE_PUBLIC_URL) — the
    # internal *.railway.internal host only resolves inside Railway.
    database_url = (
        os.environ.get("REVIEW_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "sqlite:///./review_ui.db"
    )
    # Title is shown in the header and the browser tab; it carries the
    # Sandbox-vs-normal distinction (e.g. "AskTIM · Sandbox Database").
    title = os.environ.get("REVIEW_TITLE", "AskTIM · Database")
    # Named palette preset; REVIEW_ACCENT optionally overrides with raw hex.
    theme = (os.environ.get("REVIEW_THEME") or "production").strip().lower()
    accent = os.environ.get("REVIEW_ACCENT") or None
    # Shared-password gate. None = no gate (local dev only); deployments MUST set
    # this since the tool exposes every student's conversations and images.
    password = os.environ.get("REVIEW_PASSWORD") or None
    secret_key = os.environ.get("REVIEW_SECRET_KEY", "dev-insecure-review-key")
    port = int(os.environ.get("PORT", "5003"))
    cookie_max_age_seconds = int(
        os.environ.get("REVIEW_COOKIE_MAX_AGE", str(_DEFAULT_COOKIE_MAX_AGE_SECONDS))
    )
    return Config(
        database_url=database_url,
        title=title,
        theme=theme,
        accent=accent,
        password=password,
        secret_key=secret_key,
        port=port,
        cookie_max_age_seconds=cookie_max_age_seconds,
    )
