# RackLab-RTP Operations Runbook

## Quick Reference

**Service**: RackLab-RTP  
**Owners**: Meta Hardware Systems Engineering  
**Severity**: P2 (Business Critical)  
**On-Call**: hardware-rtp-oncall@meta.com

---

## Service Overview

RackLab-RTP is the automated hardware validation platform for rack-level compute systems. It runs continuous validation tests, injects failures for RCA validation, and provides automated diagnostics.

**Key Capabilities**:
- Automated system bring-up validation
- Failure injection and RCA
- Test result persistence
- Dashboard for monitoring

---

## Architecture Summary
```
┌──────────────┐
│  Dashboard   │ (Port 8000)
└──────┬───────┘
       │
┌──────▼───────────┐
│   FastAPI App    │ (Python 3.11)
└──────┬───────────┘
       │
┌──────▼───────────┐
│ SQLite Database  │ (racklab.db)
└──────────────────┘
```

**Dependencies**:
- Python 3.11+
- SQLite3
- Network access (if enabled)

---

## Deployment

### Local Development
```bash
# Clone repository
git clone https://github.com/meta/RackLab-RTP.git
cd RackLab-RTP

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run locally
python -m uvicorn app.main:app --reload

# Access dashboard
open http://localhost:8000
```

### Production Deployment (Render/Railway)

1. **Create new service**
   - Connect GitHub repository
   - Select branch: `main`

2. **Configure environment**
```bash
   AUTH_TOKEN=<generate-secure-token>
   DATABASE_URL=sqlite:///./racklab.db
   LOG_LEVEL=INFO
   MAX_RETRIES=3
   TIMEOUT_SECONDS=60
```

3. **Deploy**
   - Platform auto-detects `Procfile`
   - Builds from `requirements.txt`
   - Starts with: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Verify deployment**
```bash
   curl https://your-app.onrender.com/health
   # Expected: {"status": "healthy"}
```

---

## Monitoring

### Health Check
```bash
# Basic health
curl https://your-app.onrender.com/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "RackLab-RTP"
}
```

### Key Metrics

| Metric | Command | Healthy Range |
|--------|---------|---------------|
| Total Tests | Check dashboard | >0 |
| Pass Rate | Check dashboard | >95% |
| API Response Time | Check logs | <500ms (p95) |
| Test Execution Time | Check logs | <5s per test |

### Logs

**View structured logs**:
```bash
# JSON format with request tracing
tail -f logs/app.log | jq .

# Filter by level
tail -f logs/app.log | jq 'select(.level == "ERROR")'

# Filter by request_id
tail -f logs/app.log | jq 'select(.request_id == "abc-123")'
```

**Log Fields**:
```json
{
  "timestamp": "2026-02-02T10:30:00Z",
  "level": "INFO",
  "logger": "app.services.test_runner",
  "message": "Test execution started",
  "request_id": "abc-123",
  "test_id": "test-456",
  "test_type": "thermal_ramp"
}
```

---

## Common Operations

### Trigger a Test

**Via API**:
```bash
curl -X POST https://your-app.onrender.com/api/tests/run \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "thermal_ramp",
    "inject_failure": "none",
    "failure_probability": 0.0
  }'

# Response
{
  "test_id": "abc-123-def-456",
  "status": "running",
  "message": "Test abc-123-def-456 started successfully"
}
```

**Via Dashboard**:
1. Navigate to `/trigger`
2. Select test type
3. Configure failure injection (optional)
4. Enter auth token
5. Click "Run Test"

### Check Test Status
```bash
# Get test details
curl https://your-app.onrender.com/api/tests/{test_id}

# List recent tests
curl https://your-app.onrender.com/api/tests?limit=10

# Filter by status
curl https://your-app.onrender.com/api/tests?status=failed

# Filter by type
curl https://your-app.onrender.com/api/tests?test_type=thermal_ramp
```

### Export Test Report
```bash
# JSON format
curl -o report.json \
  https://your-app.onrender.com/api/export/{test_id}?format=json

# Markdown format
curl -o report.md \
  https://your-app.onrender.com/api/export/{test_id}?format=markdown
```

### Database Backup
```bash
# Backup SQLite database
cp racklab.db racklab.db.backup-$(date +%Y%m%d)

# Verify backup
sqlite3 racklab.db.backup-20260202 "SELECT COUNT(*) FROM test_runs;"
```

---

## Troubleshooting

### Issue: Tests Timing Out

**Symptoms**:
- Tests stuck in "running" state
- Logs show timeout errors

**Diagnosis**:
```bash
# Check timeout configuration
echo $TIMEOUT_SECONDS

# Check for stuck tests
curl https://your-app.onrender.com/api/tests?status=running

# Check logs for timeout
tail -f logs/app.log | grep -i timeout
```

**Resolution**:
1. Increase timeout: `TIMEOUT_SECONDS=120`
2. Restart application
3. Manually mark stuck tests as failed:
```python
   # In Python shell
   from app.database import SessionLocal
   from app.models import TestRun, TestStatus
   
   db = SessionLocal()
   stuck = db.query(TestRun).filter(TestRun.status == "running").all()
   for test in stuck:
       test.status = TestStatus.TIMEOUT.value
   db.commit()
```

---

### Issue: Authentication Failures

**Symptoms**:
- 401 Unauthorized responses
- "Invalid authentication token" errors

**Diagnosis**:
```bash
# Verify token configuration
echo $AUTH_TOKEN

# Test authentication
curl -X POST https://your-app.onrender.com/api/tests/run \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_type": "thermal_ramp"}'
```

**Resolution**:
1. Regenerate secure token:
```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
```
2. Update environment variable
3. Restart application
4. Update clients with new token

---

### Issue: Database Locked

**Symptoms**:
- "Database is locked" errors
- Write operations failing

**Diagnosis**:
```bash
# Check for locks
sqlite3 racklab.db "PRAGMA locking_mode;"

# Check for WAL mode
sqlite3 racklab.db "PRAGMA journal_mode;"
```

**Resolution**:
1. Enable WAL mode for better concurrency:
```sql
   sqlite3 racklab.db "PRAGMA journal_mode=WAL;"
```
2. Restart application
3. If persists, check for long-running queries

---

### Issue: RCA Confidence Too Low

**Symptoms**:
- RCA results with confidence <0.5
- Category: UNKNOWN frequently

**Diagnosis**:
```bash
# Check recent RCA results
curl https://your-app.onrender.com/api/tests?status=failed | \
  jq '.[] | select(.rca_result.confidence < 0.5)'
```

**Resolution**:
1. Review failure logs for patterns
2. Verify sensor readings are realistic
3. Check if new failure modes need classification rules
4. Update `app/services/rca_engine.py` with new rules

---

### Issue: High Failure Rate

**Symptoms**:
- Pass rate <90%
- Many tests failing unexpectedly

**Diagnosis**:
```bash
# Check failure distribution
curl https://your-app.onrender.com/api/tests?status=failed | \
  jq 'group_by(.error_code) | map({code: .[0].error_code, count: length})'

# Check for common error
tail -f logs/app.log | grep -i "error_code"
```

**Resolution**:
1. Identify most common failure mode
2. Review test parameters (may be too strict)
3. Check for environmental issues (if using real hardware)
4. Adjust test thresholds if needed

---

## Alerts and Escalation

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Pass Rate | <95% | <90% | Investigate failures |
| API Response Time | >500ms | >1000ms | Check performance |
| Test Timeouts | >5% | >10% | Increase timeout |
| Database Size | >1GB | >2GB | Archive old tests |

### Escalation Path

1. **P3 (Low)**: Self-service, check runbook
2. **P2 (Medium)**: Contact on-call via Slack
3. **P1 (High)**: Page on-call immediately
4. **P0 (Critical)**: Page on-call + manager

### On-Call Contacts

- **Primary**: hardware-rtp-oncall@meta.com
- **Secondary**: hardware-systems@meta.com
- **Manager**: rtp-manager@meta.com

---

## Maintenance

### Database Cleanup
```bash
# Archive tests older than 90 days
python -c "
from app.database import SessionLocal
from app.models import TestRun
from datetime import datetime, timedelta

db = SessionLocal()
cutoff = datetime.utcnow() - timedelta(days=90)
old_tests = db.query(TestRun).filter(TestRun.started_at < cutoff).delete()
db.commit()
print(f'Archived {old_tests} tests')
"
```

### Log Rotation
```bash
# Rotate logs (if using file logging)
logrotate -f /etc/logrotate.d/racklab-rtp
```

### Dependency Updates
```bash
# Check for updates
pip list --outdated

# Update dependencies
pip install -U fastapi uvicorn sqlalchemy pydantic

# Test after update
pytest tests/ -v

# Update requirements.txt
pip freeze > requirements.txt
```

---

## Security

### Token Management

- **Rotation**: Every 90 days
- **Generation**: Use cryptographically secure random
- **Storage**: Environment variables only, never commit
```bash
# Generate new token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Rate Limiting

- **Default**: 10 requests/minute per IP
- **Bypass**: Not available (security requirement)
- **Adjustment**: Edit `app/config.py`

### Audit Logging

All test executions are logged with:
- Request ID
- Timestamp
- User (from token context, if available)
- Test parameters
- Results

---

## Performance Tuning

### Database Optimization
```sql
-- Enable WAL mode
PRAGMA journal_mode=WAL;

-- Analyze tables
ANALYZE;

-- Create indexes
CREATE INDEX idx_test_runs_status ON test_runs(status);
CREATE INDEX idx_test_runs_type ON test_runs(test_type);
CREATE INDEX idx_test_runs_started ON test_runs(started_at);
```

### Application Tuning
```bash
# Increase timeout for long tests
TIMEOUT_SECONDS=120

# Reduce retries for faster failure
MAX_RETRIES=1

# Disable realistic delays for faster tests
ENABLE_REALISTIC_DELAYS=false
```

---

## Disaster Recovery

### Backup Strategy

1. **Database**: Daily backups to cloud storage
2. **Logs**: Retained for 30 days
3. **Code**: Git repository (single source of truth)

### Recovery Procedure

1. **Deploy fresh instance**
```bash
   # On new server
   git clone https://github.com/meta/RackLab-RTP.git
   pip install -r requirements.txt
```

2. **Restore database**
```bash
   cp racklab.db.backup racklab.db
```

3. **Configure environment**
```bash
   cp .env.example .env
   # Edit .env
```

4. **Start service**
```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. **Verify health**
```bash
   curl http://localhost:8000/health
```

---

## Change Management

### Deployment Checklist

- [ ] Code reviewed and approved
- [ ] Tests passing (`pytest tests/ -v`)
- [ ] Staging deployment validated
- [ ] Backup database before deploy
- [ ] Deploy during low-traffic window
- [ ] Monitor logs post-deployment
- [ ] Verify health check passes
- [ ] Run smoke test suite

### Rollback Procedure
```bash
# Revert to previous version
git revert HEAD
git push

# Or redeploy previous tag
git checkout v1.0.0
# Trigger deployment
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-02  
**Next Review**: 2026-05-02
