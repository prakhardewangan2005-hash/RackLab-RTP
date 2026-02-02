"""
Dashboard UI routes using Jinja2 templates.
Provides web interface for test management and visualization.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import TestRun, RCARecord, TestStatus, TestType
from app.logger import get_logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = get_logger(__name__)


@router.get("/")
async def dashboard(
    request: Request,
    status: Optional[str] = None,
    test_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Main dashboard showing test history with filters."""
    query = db.query(TestRun)
    
    if status:
        query = query.filter(TestRun.status == status)
    
    if test_type:
        query = query.filter(TestRun.test_type == test_type)
    
    test_runs = query.order_by(TestRun.started_at.desc()).limit(100).all()
    
    # Calculate summary stats
    total_tests = db.query(TestRun).count()
    passed_tests = db.query(TestRun).filter(TestRun.status == TestStatus.PASSED.value).count()
    failed_tests = db.query(TestRun).filter(TestRun.status == TestStatus.FAILED.value).count()
    
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "test_runs": test_runs,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "pass_rate": round(pass_rate, 1),
        "current_status": status,
        "current_test_type": test_type,
        "test_types": [t.value for t in TestType],
        "test_statuses": [s.value for s in TestStatus]
    })


@router.get("/trigger")
async def trigger_page(request: Request):
    """Test trigger UI page."""
    return templates.TemplateResponse("trigger.html", {
        "request": request,
        "test_types": [t.value for t in TestType],
        "failure_types": ["none", "thermal_runaway", "voltage_droop", "boot_failure", "fan_stuck"]
    })


@router.get("/test/{test_id}")
async def test_detail(
    request: Request,
    test_id: str,
    db: Session = Depends(get_db)
):
    """Detailed view of a single test run."""
    test_run = db.query(TestRun).filter(TestRun.test_id == test_id).first()
    
    if not test_run:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "error": f"Test {test_id} not found"
        })
    
    rca = db.query(RCARecord).filter(RCARecord.test_id == test_id).first()
    
    return templates.TemplateResponse("test_detail.html", {
        "request": request,
        "test": test_run,
        "rca": rca
    })


@router.get("/api/export/{test_id}")
async def export_report(
    test_id: str,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """Export test report in JSON or Markdown format."""
    test_run = db.query(TestRun).filter(TestRun.test_id == test_id).first()
    
    if not test_run:
        return JSONResponse(
            status_code=404,
            content={"error": f"Test {test_id} not found"}
        )
    
    rca = db.query(RCARecord).filter(RCARecord.test_id == test_id).first()
    
    if format == "markdown":
        md_content = f"""# Test Report: {test_id}

## Summary
- **Test Type**: {test_run.test_type}
- **Status**: {test_run.status}
- **Duration**: {test_run.duration_ms}ms
- **Started**: {test_run.started_at}
- **Completed**: {test_run.completed_at}

## Metrics
```json
{test_run.metrics}
```

## Logs
```
{chr(10).join(test_run.logs or [])}
```
"""
        
        if rca:
            md_content += f"""
## Root Cause Analysis
- **Category**: {rca.category}
- **Confidence**: {rca.confidence * 100}%
- **Root Cause**: {rca.root_cause}

### Recommendations
{chr(10).join(f"- {r}" for r in rca.recommendations or [])}
"""
        
        return PlainTextResponse(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=test-{test_id}.md"}
        )
    
    else:  # JSON format
        report = {
            "test_id": test_run.test_id,
            "test_type": test_run.test_type,
            "status": test_run.status,
            "duration_ms": test_run.duration_ms,
            "started_at": test_run.started_at.isoformat() if test_run.started_at else None,
            "completed_at": test_run.completed_at.isoformat() if test_run.completed_at else None,
            "error_code": test_run.error_code,
            "metrics": test_run.metrics,
            "logs": test_run.logs
        }
        
        if rca:
            report["rca"] = {
                "category": rca.category,
                "confidence": rca.confidence,
                "root_cause": rca.root_cause,
                "recommendations": rca.recommendations
            }
        
        return JSONResponse(
            content=report,
            headers={"Content-Disposition": f"attachment; filename=test-{test_id}.json"}
        )
