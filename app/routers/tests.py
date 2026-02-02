"""
Test execution API endpoints.
Handles test triggering, status queries, and result retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import verify_token
from app.database import get_db
from app.models import (
    TestRunRequest, TestRunResponse, TestResultResponse,
    TestRun, TestStatus, TestType
)
from app.services.test_runner import TestRunner
from app.logger import get_logger
from app.config import settings

router = APIRouter()
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/run", response_model=TestRunResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def run_test(
    request: TestRunRequest,
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_token)
):
    """
    Trigger a new test run with optional failure injection.
    Requires authentication token.
    """
    logger.info("Test run requested", extra={
        "test_type": request.test_type,
        "inject_failure": request.inject_failure
    })
    
    runner = TestRunner(db)
    
    try:
        test_id = await runner.execute_test(
            test_type=request.test_type,
            inject_failure=request.inject_failure,
            failure_probability=request.failure_probability
        )
        
        return TestRunResponse(
            test_id=test_id,
            status=TestStatus.RUNNING,
            message=f"Test {test_id} started successfully"
        )
    
    except Exception as e:
        logger.error("Test execution failed", extra={
            "error": str(e),
            "test_type": request.test_type
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test execution failed: {str(e)}"
        )


@router.get("/{test_id}", response_model=TestResultResponse)
async def get_test_result(
    test_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve test results by test_id."""
    test_run = db.query(TestRun).filter(TestRun.test_id == test_id).first()
    
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test {test_id} not found"
        )
    
    # Get RCA result if available
    from app.models import RCARecord
    rca = db.query(RCARecord).filter(RCARecord.test_id == test_id).first()
    rca_result = None
    if rca:
        rca_result = {
            "category": rca.category,
            "confidence": rca.confidence,
            "root_cause": rca.root_cause,
            "recommendations": rca.recommendations
        }
    
    return TestResultResponse(
        test_id=test_run.test_id,
        test_type=test_run.test_type,
        status=test_run.status,
        duration_ms=test_run.duration_ms or 0.0,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        error_code=test_run.error_code,
        metrics=test_run.metrics or {},
        logs=test_run.logs or [],
        rca_result=rca_result
    )


@router.get("", response_model=List[TestResultResponse])
async def list_tests(
    status: Optional[TestStatus] = None,
    test_type: Optional[TestType] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List test runs with optional filters."""
    query = db.query(TestRun)
    
    if status:
        query = query.filter(TestRun.status == status.value)
    
    if test_type:
        query = query.filter(TestRun.test_type == test_type.value)
    
    test_runs = query.order_by(TestRun.started_at.desc()).limit(limit).all()
    
    # Get RCA results for all tests
    from app.models import RCARecord
    rca_map = {}
    for rca in db.query(RCARecord).filter(
        RCARecord.test_id.in_([t.test_id for t in test_runs])
    ).all():
        rca_map[rca.test_id] = {
            "category": rca.category,
            "confidence": rca.confidence,
            "root_cause": rca.root_cause,
            "recommendations": rca.recommendations
        }
    
    results = []
    for test_run in test_runs:
        results.append(TestResultResponse(
            test_id=test_run.test_id,
            test_type=test_run.test_type,
            status=test_run.status,
            duration_ms=test_run.duration_ms or 0.0,
            started_at=test_run.started_at,
            completed_at=test_run.completed_at,
            error_code=test_run.error_code,
            metrics=test_run.metrics or {},
            logs=test_run.logs or [],
            rca_result=rca_map.get(test_run.test_id)
        ))
    
    return results
