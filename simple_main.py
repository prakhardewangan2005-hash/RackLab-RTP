"""
Simplified main for testing deployment.
"""

from fastapi import FastAPI

app = FastAPI(title="RackLab-RTP", version="1.0.0")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to RackLab-RTP",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "RackLab-RTP"
    }
