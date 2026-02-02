"""
Main FastAPI application entry point.
Includes middleware, rate limiting, and router registration.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.logger import get_logger
from app.routers import tests, dashboard

logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting RackLab-RTP application", extra={
        "version": "1.0.0",
        "environment": "production"
    })
    init_db()
    yield
    logger.info("Shutting down RackLab-RTP application")


# Initialize FastAPI app
app = FastAPI(
    title="RackLab-RTP",
    description="Automated System-Level Bring-up, Validation & Failure Analysis Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
app.include_router(dashboard.router, tags=["dashboard"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with structured logging."""
    import time
    import uuid
    
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info("Incoming request", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host
    })
    
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info("Request completed", extra={
        "request_id": request_id,
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 2)
    })
    
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "RackLab-RTP"
    }
