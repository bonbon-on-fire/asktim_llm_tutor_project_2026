"""Flask app for the main_ui production-shape tutor."""

from __future__ import annotations

from flask import Flask, jsonify

from main_ui.config import load_config


def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.secret_key

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "main_ui"})

    return app


app = create_app()
