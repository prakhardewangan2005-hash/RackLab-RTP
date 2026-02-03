# =========================
# FILE: api/index.py
# =========================
import os, sys

# Ensure repo root is on PYTHONPATH so `/app` imports work on Vercel
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.main import app


# =========================
# FILE: app/main.py
# =========================
from __future__ import annotations

import os
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("racklab-rtp")

app = FastAPI(
    title="RackLab-RTP",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

# CORS (safe default; tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (set during startup)
app.state.ready = False
app.state.startup_error = None
app.state.database_url = None
app.state.auth_token_present = False


def _normalize_database_url(raw: Optional[str]) -> str:
    """
    Vercel serverless FS is effectively read-only except /tmp.
    Default SQLite location -> /tmp.
    """
    if raw and raw.strip():
        return raw.strip()
    return "sqlite:////tmp/racklab.db"


def _check_env() -> None:
    auth = os.getenv("AUTH_TOKEN", "").strip()
    app.state.auth_token_present = bool(auth)


@app.on_event("startup")
async def startup() -> None:
    """
    IMPORTANT: Do not do DB/file writes at import time.
    Only do lightweight checks here.
    """
    try:
        # Config
        app.state.database_url = _normalize_database_url(os.getenv("DATABASE_URL"))
        _check_env()

        # Optional quick DB sanity check (won't create tables / write files)
        try:
            from sqlalchemy import text, create_engine

            engine = create_engine(app.state.database_url, pool_pre_ping=True, future=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning("DB check skipped/failed: %s", e)

        app.state.ready = True
        logger.info("Startup OK (ready=true)")
    except Exception as e:
        app.state.ready = False
        app.state.startup_error = str(e)
        logger.exception("Startup failed")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "Unexpected error occurred."},
    )


@app.get("/")
def root():
    return {
        "service": "RackLab-RTP",
        "status": "ok" if app.state.ready else "degraded",
        "ready": bool(app.state.ready),
    }


@app.get("/health")
def health():
    return {
        "service": "RackLab-RTP",
        "ready": bool(app.state.ready),
        "startup_error": app.state.startup_error,
        "database_url": app.state.database_url,
        "auth_token_present": bool(app.state.auth_token_present),
    }


@app.get("/metrics")
def metrics():
    return {
        "ready": int(bool(app.state.ready)),
        "auth_token_present": int(bool(app.state.auth_token_present)),
    }
