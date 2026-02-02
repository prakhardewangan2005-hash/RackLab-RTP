# RackLab-RTP Test Plan

## Overview

This document defines the comprehensive test suite for hardware system validation. Each test is designed to stress specific subsystems and validate proper operation under various load conditions.

## Test Suite

### 1. Thermal Ramp Test

**Objective**: Validate thermal management system under gradual temperature increase.

**Test ID**: `thermal_ramp`

**Procedure**:
1. Boot system to completion
2. Gradually increase CPU temperature from 25°C to 85°C
3. Monitor thermal throttling behavior
4. Verify temperature stays within safe limits

**Expected Behavior**:
- System boots successfully
- Temperature ramps smoothly (no sudden spikes)
- Thermal throttling engages at >85°C
- CPU frequency reduces proportionally to temperature
- No thermal runaway (temp stays <90°C)

**Success Criteria**:
- ✅ Boot completes successfully
- ✅ Final temperature: 80-85°C
- ✅ Thermal throttling detected in logs
- ✅ No thermal runaway

**Failure Modes**:
- Thermal runaway (temp >90°C) → RCA: THERMAL
- Fan failure → RCA: THERMAL
- Inadequate cooling → RCA: THERMAL

**Typical Duration**: 2-3 seconds

**Metrics Collected**:
```json
{
  "cpu_temp_c": 85.2,
  "cpu_freq_mhz": 2400,
  "fan_rpm": 2000,
  "thermal_throttle_events": 2
}
```

---

### 2. Power Stress Test

**Objective**: Validate power delivery system under maximum load.

**Test ID**: `power_stress`

**Procedure**:
1. Boot system to completion
2. Apply 90% load to all power rails (12V, 5V, 3.3V)
3. Measure voltage droop under load
4. Verify all rails stay within tolerance

**Expected Behavior**:
- System boots successfully
- Power draw increases to ~360W
- Voltage droop: <10% from nominal
- All rails remain stable under load

**Success Criteria**:
- ✅ 12V rail: 10.8V - 12.6V
- ✅ 5V rail: 4.5V - 5.25V
- ✅ 3.3V rail: 3.0V - 3.6V
- ✅ No undervoltage shutdowns

**Failure Modes**:
- Excessive voltage droop → RCA: POWER
- PSU overload → RCA: POWER
- Power rail instability → RCA: POWER

**Typical Duration**: 1-2 seconds

**Metrics Collected**:
```json
{
  "power_draw_w": 360.0,
  "voltage_12v": 11.4,
  "voltage_5v": 4.8,
  "voltage_3v3": 3.15,
  "voltage_droop_percent": 8.5
}
```

---

### 3. CPU Stability Soak

**Objective**: Validate CPU stability under sustained maximum load.

**Test ID**: `cpu_stability`

**Procedure**:
1. Boot system to completion
2. Set CPU to maximum frequency (3.6 GHz)
3. Apply sustained computational load
4. Monitor for crashes, hangs, or instability
5. Run for extended duration (10 minutes, compressed for demo)

**Expected Behavior**:
- System boots successfully
- CPU maintains maximum frequency
- Temperature stabilizes at ~75°C
- No crashes or kernel panics
- No frequency downclocking (except thermal throttle)

**Success Criteria**:
- ✅ Boot completes successfully
- ✅ CPU frequency stable at 3600 MHz
- ✅ No crashes or hangs
- ✅ Temperature remains <80°C

**Failure Modes**:
- CPU crash → RCA: FIRMWARE or OS
- Frequency instability → RCA: POWER
- Thermal shutdown → RCA: THERMAL

**Typical Duration**: 1-2 seconds (compressed from 10 minutes)

**Metrics Collected**:
```json
{
  "cpu_freq_mhz": 3600,
  "cpu_temp_c": 75.0,
  "uptime_seconds": 600,
  "stability_events": 0
}
```

---

### 4. Firmware-to-OS Handoff Validation

**Objective**: Validate proper state transfer through each boot stage.

**Test ID**: `firmware_handoff`

**Procedure**:
1. Execute firmware initialization
2. Verify transition to bootloader stage
3. Execute bootloader initialization
4. Verify transition to OS init stage
5. Execute OS initialization
6. Verify complete boot

**Expected Behavior**:
- Each stage completes successfully
- State transitions occur in correct order
- No data loss between stages
- All subsystems initialized properly

**Success Criteria**:
- ✅ Firmware → Bootloader transition clean
- ✅ Bootloader → OS transition clean
- ✅ Final boot stage: "complete"
- ✅ All POST checks pass

**Failure Modes**:
- Firmware corruption → RCA: FIRMWARE
- Bootloader failure → RCA: FIRMWARE
- OS kernel panic → RCA: OS
- State transfer error → RCA: FIRMWARE

**Typical Duration**: 0.5-1 second

**Metrics Collected**:
```json
{
  "boot_stage": "complete",
  "firmware_time_ms": 100,
  "bootloader_time_ms": 50,
  "os_init_time_ms": 150,
  "total_boot_time_ms": 300
}
```

---

## Failure Injection

### Purpose
Validate RCA engine's ability to correctly identify and classify hardware failures.

### Supported Failure Types

#### 1. Thermal Runaway
- **Trigger**: Set CPU temp to 95°C
- **Expected RCA**: THERMAL category, confidence >0.8
- **Detection**: Temperature sensor reading >90°C

#### 2. Voltage Droop
- **Trigger**: Set 12V rail to 10.5V
- **Expected RCA**: POWER category, confidence >0.5
- **Detection**: Voltage reading <10.8V (10% tolerance)

#### 3. Boot Failure
- **Trigger**: Force boot stage transition failure
- **Expected RCA**: FIRMWARE or OS category, confidence >0.9
- **Detection**: Boot sequence halts before completion

#### 4. Fan Stuck
- **Trigger**: Set fan RPM to 0
- **Expected RCA**: THERMAL category, confidence >0.8
- **Detection**: Tachometer reading <500 RPM

### Injection Parameters
```python
{
  "inject_failure": "thermal_runaway",  # or voltage_droop, boot_failure, fan_stuck
  "failure_probability": 0.8            # 0.0 - 1.0
}
```

---

## Test Execution

### Manual Execution (API)
```bash
curl -X POST http://localhost:8000/api/tests/run \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "thermal_ramp",
    "inject_failure": "none",
    "failure_probability": 0.0
  }'
```

### Manual Execution (Dashboard)

1. Navigate to `/trigger`
2. Select test type
3. Optionally configure failure injection
4. Enter auth token
5. Click "Run Test"

### Automated Execution (CI/CD)
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_system_simulator.py::test_thermal_load_application
```

---

## Acceptance Criteria

### Test Pass Criteria
A test is considered **PASSED** if:
1. All boot stages complete successfully
2. All sensor readings within specifications
3. No critical errors in logs
4. Test duration within expected range
5. No unexpected failures

### Test Fail Criteria
A test is considered **FAILED** if:
1. Boot sequence fails at any stage
2. Sensor readings exceed safe limits
3. Critical errors detected
4. Timeout exceeded
5. System crash or hang

---

## RCA Validation

### RCA Accuracy Metrics

| Injected Failure | Expected Category | Min Confidence |
|------------------|-------------------|----------------|
| thermal_runaway  | THERMAL           | 0.80           |
| voltage_droop    | POWER             | 0.50           |
| boot_failure     | FIRMWARE or OS    | 0.90           |
| fan_stuck        | THERMAL           | 0.80           |

### RCA Quality Checks
```python
def validate_rca(rca_result, expected_category, min_confidence):
    assert rca_result.category == expected_category
    assert rca_result.confidence >= min_confidence
    assert len(rca_result.recommendations) >= 3
    assert rca_result.root_cause is not None
```

---

## Performance Targets

| Test Type | Target Duration | Max Duration |
|-----------|-----------------|--------------|
| thermal_ramp | 2-3s | 5s |
| power_stress | 1-2s | 4s |
| cpu_stability | 1-2s (compressed) | 3s |
| firmware_handoff | 0.5-1s | 2s |

---

## Reporting

### Test Report Contents

1. **Summary**
   - Test ID, type, status
   - Start/end timestamps
   - Total duration

2. **Metrics**
   - All sensor readings
   - Performance counters
   - Resource utilization

3. **Logs**
   - Timestamped event log
   - Error messages
   - Boot sequence trace

4. **RCA Results** (if failed)
   - Category and confidence
   - Root cause description
   - Actionable recommendations

### Export Formats

- **JSON**: Machine-readable, full data
- **Markdown**: Human-readable, formatted report

---

## Continuous Improvement

### Feedback Loop

1. Run tests regularly (daily/weekly)
2. Collect failure data
3. Analyze RCA accuracy
4. Retrain classifier (future ML integration)
5. Update test parameters based on findings

### Metrics to Track

- Test pass rate (target: >95%)
- RCA accuracy (target: >95%)
- Mean time to diagnosis (target: <30s)
- False positive rate (target: <5%)

---

## Safety Considerations

⚠️ **Important**: While this is a simulator, in production with real hardware:

1. Never exceed thermal limits (>100°C CPU)
2. Always monitor voltage rails actively
3. Implement emergency shutdown for critical failures
4. Use watchdog timers for hang detection
5. Log all safety events for audit trail

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-02  
**Owner**: Meta Hardware Systems Engineering
