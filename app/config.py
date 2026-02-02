"""
Application configuration using Pydantic settings.
Loads from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Authentication
    auth_token: str = "default-dev-token-change-in-production"
    
    # Database
    database_url: str = "sqlite:///./racklab.db"
    
    # Logging
    log_level: str = "INFO"
    
    # Test Configuration
    max_retries: int = 3
    timeout_seconds: int = 60
    default_test_duration_ms: int = 5000
    
    # Rate Limiting
    rate_limit_per_minute: int = 10
    
    # System Simulation
    enable_realistic_delays: bool = True
    sensor_noise_percent: float = 2.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
