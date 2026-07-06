"""
Admissions Ledger backend entry point.

Exposes the WSGI ``app`` that hosts import (Vercel via ``api/index.py``, or
``gunicorn server:app``), and a small local dev runner. The whole application is
assembled by the factory in ``app/__init__.py``.

Run locally (DATABASE_URL must point at the Supabase Postgres):
    DATABASE_URL="postgresql://...:6543/postgres" python3 server.py
"""

import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    # Local development server only. Binds localhost and keeps the debugger OFF
    # by default — never expose Flask's dev server (or its debugger) publicly.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host=host, port=port, debug=debug)
