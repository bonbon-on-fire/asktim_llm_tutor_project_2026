"""Run the dashboard Flask app via ``python -m dashboard_ui``."""

import os

from .run_dashboard_ui import app


if __name__ == "__main__":
    # Port 5001 is reserved for main_ui; default the dashboard to 5002 (PORT overrides).
    app.run(debug=True, port=int(os.environ.get("PORT", "5002")))

