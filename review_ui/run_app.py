"""Flask app for review_ui — read-only conversation review.

Phase 1 establishes the app factory, per-request read-only DB session, and a
health check. Routes (the conversation list, transcript view, image serving) are
registered in Phase 2. This app intentionally does NOT create or migrate any
schema — the live apps own it; we only read.
"""

from __future__ import annotations

from datetime import timedelta

from flask import Flask, g, jsonify

from review_ui.auth import init_auth
from review_ui.config import load_config
from review_ui.db import SessionLocal
from review_ui.routes.review import review_bp


def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.secret_key
    # Surfaced to templates: title + accent (matches main_ui).
    app.config["REVIEW_TITLE"] = config.title
    app.config["REVIEW_ACCENT"] = config.accent
    # Read by the auth gate; None => open (local dev only).
    app.config["REVIEW_PASSWORD"] = config.password
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        seconds=config.cookie_max_age_seconds
    )

    # NOTE: deliberately no Base.metadata.create_all / migrations. read-only.

    @app.before_request
    def _open_db_session() -> None:
        g.db = SessionLocal()

    @app.teardown_request
    def _close_db_session(exception: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is None:
            return
        # Always roll back — this app never writes. Then close.
        db.rollback()
        db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "review_ui"})

    init_auth(app)
    app.register_blueprint(review_bp)

    return app


app = create_app()
