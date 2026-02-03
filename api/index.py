import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

try:
    # your real app
    from app.main import app as real_app
    app = real_app
except Exception:
    logging.exception("Failed to import FastAPI app from app.main")
    app = FastAPI()

    @app.get("/")
    def _startup_failed():
        return {
            "status": "startup_failed",
            "hint": "Open Vercel -> Project -> Functions -> api/index.py -> Logs to see the traceback."
        }
