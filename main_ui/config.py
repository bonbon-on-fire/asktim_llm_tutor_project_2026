"""Environment-driven configuration for main_ui."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    secret_key: str
    database_url: str
    port: int


def load_config() -> Config:
    secret_key = os.environ.get("MAIN_UI_SECRET_KEY", "dev-insecure-key")
    database_url = os.environ.get("DATABASE_URL", "sqlite:///./main_ui.db")
    port = int(os.environ.get("PORT", "5001"))
    return Config(secret_key=secret_key, database_url=database_url, port=port)
