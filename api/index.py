"""
Vercel serverless entry point.

Vercel's Python runtime serves the WSGI ``app`` it finds in this file. We just
import the same Flask app used everywhere else (server.py) so the hosted site
and local runs share identical code against the same Supabase database.
"""

import os
import sys

# server.py lives at the repo root (one level up from this api/ folder).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app  # noqa: E402  (WSGI app Vercel will serve)
