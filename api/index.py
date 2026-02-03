import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

try:
    from app.main import app as real_app
    app = real_app
except Exception:
    logging.exception("Failed to import FastAPI app from app.main")
    app = FastAPI()

    @app.get("/")
    def _startup_failed():
        return {
            "status": "startup_failed",
            "next": "Open Vercel -> Project -> Functions -> api/index.py -> Logs for traceback"
        }
