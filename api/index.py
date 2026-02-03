import os
import sys
import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

# Ensure repo root is on PYTHONPATH (so we can import /app)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from app.main import app as real_app
    app = real_app
except Exception as e:
    logging.exception("Failed to import app.main:app")
    app = FastAPI()

    @app.get("/")
    def _import_failed():
        return {
            "status": "import_failed",
            "error": str(e),
            "fix": "Check that app/main.py exists and exports `app = FastAPI()`"
        }
