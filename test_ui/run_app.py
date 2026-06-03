"""Flask app for the test_ui tutor testing harness."""

from __future__ import annotations

from flask import Flask, Response, g, jsonify, request

from test_ui.config import load_config
from test_ui.cookies import (
    SESSION_COOKIE_NAME,
    default_cookie_kwargs,
    new_session_id,
)
from test_ui.db import SessionLocal
from test_ui.db.models import Base
from test_ui.db.session import engine
from test_ui.routes.chat import chat_bp
from test_ui.routes.embed import embed_bp
from test_ui.routes.history import history_bp
from test_ui.routes.identity import identity_bp


def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.secret_key

    # test_ui owns a separate, throwaway database and skips Alembic — the
    # schema is created directly from the models on boot.
    Base.metadata.create_all(engine)

    app.register_blueprint(embed_bp)
    app.register_blueprint(identity_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(history_bp)

    @app.before_request
    def _ensure_session_id() -> None:
        existing = request.cookies.get(SESSION_COOKIE_NAME)
        if existing:
            g.session_id = existing
            g.session_id_is_new = False
        else:
            g.session_id = new_session_id()
            g.session_id_is_new = True

    @app.before_request
    def _open_db_session() -> None:
        g.db = SessionLocal()

    @app.teardown_request
    def _close_db_session(exception: BaseException | None = None) -> None:
        # Routes that take over their own session lifecycle (the streaming
        # /api/chat endpoint) pop g.db themselves before returning; this
        # teardown then finds nothing to clean up and exits silently.
        db = g.pop("db", None)
        if db is None:
            return
        try:
            if exception is None:
                db.commit()
            else:
                db.rollback()
        finally:
            db.close()

    @app.after_request
    def _set_session_cookie(response: Response) -> Response:
        if getattr(g, "session_id_is_new", False):
            response.set_cookie(
                SESSION_COOKIE_NAME,
                g.session_id,
                **default_cookie_kwargs(),
            )
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "test_ui"})

    return app


app = create_app()
