"""Run the dashboard Flask app via ``python -m dashboard_ui``."""

from .run_dashboard_ui import app


if __name__ == "__main__":
    app.run(debug=True, port=5001)

