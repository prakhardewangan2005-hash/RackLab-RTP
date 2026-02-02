"""
Pydantic models for request/response validation and SQLAlchemy ORM models.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Enums
class TestType(str, Enum):
    THERMAL_RAMP = "thermal_ramp"
    POWER_STRESS = "power_stress"
    CPU_STABILITY = "cpu_stability"
    FIRMWARE_HANDOFF = "firmware_handoff"


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class FailureType(str, Enum):
    THERMAL_RUNAWAY = "thermal_runaway"
    VOLTAGE_DROOP = "voltage_droop"
    BOOT_FAILURE = "boot_failure"
    FAN_STUCK = "fan_stuck"
    NONE = "none"


class RCACategory(str, Enum):
    THERMAL = "THERMAL"
    POWER = "POWER"
    FIRMWARE = "FIRMWARE"
    OS = "OS"
    UNKNOWN = "UNKNOWN"


# Pydantic Request/Response Models
class TestRunRequest(BaseModel):
    test_type: TestType
    inject_failure: Optional[FailureType] = FailureType.NONE
    failure_probability: float = Field(0.0, ge=0.0, le=1.0)
    
    @validator('failure_probability')
    def validate_probability(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('failure_probability must be between 0.0 and 1.0')
        return v


class TestRunResponse(BaseModel):
    test_id: str
    status: TestStatus
    message: str


class TestResultResponse(BaseModel):
    test_id: str
    test_type: TestType
    status: TestStatus
    duration_ms: float
    started_at: datetime
    completed_at: Optional[datetime]
    error_code: Optional[str]
    metrics: Dict[str, Any]
    logs: List[str]
    rca_result: Optional[Dict[str, Any]]


class RCAResult(BaseModel):
    category: RCACategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    root_cause: str
    recommendations: List[str]


# SQLAlchemy ORM Models
class TestRun(Base):
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String, unique=True, index=True, nullable=False)
    test_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    duration_ms = Column(Float)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    error_code = Column(String)
    metrics = Column(JSON)
    logs = Column(JSON)
    injected_failure = Column(String)
    failure_probability = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class RCARecord(Base):
    __tablename__ = "rca_records"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    root_cause = Column(Text, nullable=False)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
