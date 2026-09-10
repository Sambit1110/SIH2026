"""Vercel Python serverless entrypoint.

Vercel's Python runtime detects an ASGI-compatible `app` object exported from
a file under `api/` and wraps it to serve every request routed to it (see
`vercel.json`, which routes all paths here). This file exists purely to
re-export the real FastAPI app defined in `app.main` -- no logic lives here.
"""
from app.main import app  # noqa: F401
