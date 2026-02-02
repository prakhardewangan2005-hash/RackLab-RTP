"""
Test execution engine with retry logic, timeout enforcement, and idempotency.
Orchestrates test runs and coordinates with other services.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import TestRun, TestType, TestStatus, FailureType
from app.services.system_simulator import SystemSimulator
from app.services.failure_injector import FailureInjector
from app.services.rca_engine import RCAEngine
from app.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class TestRunner:
    """
    Orchestrates test execution with production-grade reliability features:
    - Timeout enforcement
    - Exponential backoff retry
    - Idempotent execution
    - Structured logging
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def execute_test(
        self,
        test_type: TestType,
        inject_failure: FailureType = FailureType.NONE,
        failure_probability: float = 0.0
    ) -> str:
        """
        Execute a test with retry logic and timeout enforcement.
        Returns test_id for tracking.
        """
        test_id = str(uuid.uuid4())
        
        # Check idempotency - if test with same params exists and is running, return that
        existing = self.db.query(TestRun).filter(
            TestRun.test_type == test_type.value,
            TestRun.status == TestStatus.RUNNING.value
        ).first()
        
        if existing:
            logger.info("Idempotent test execution - returning existing run", extra={
                "test_id": existing.test_id
            })
            return existing.test_id
        
        # Create test run record
        test_run = TestRun(
            test_id=test_id,
            test_type=test_type.value,
            status=TestStatus.RUNNING.value,
            started_at=datetime.utcnow(),
            injected_failure=inject_failure.value,
            failure_probability=failure_probability,
            logs=[],
            metrics={}
        )
        self.db.add(test_run)
        self.db.commit()
        
        logger.info("Test execution started", extra={
            "test_id": test_id,
            "test_type": test_type.value
        })
        
        # Execute with retry logic
        for attempt in range(settings.max_retries):
            try:
                result = await asyncio.wait_for(
                    self._run_test(test_id, test_type, inject_failure, failure_probability),
                    timeout=settings.timeout_seconds
                )
                
                # Update test run with results
                test_run.status = result["status"]
                test_run.duration_ms = result["duration_ms"]
                test_run.completed_at = datetime.utcnow()
                test_run.metrics = result["metrics"]
                test_run.logs = result["logs"]
                test_run.error_code = result.get("error_code")
                
                self.db.commit()
                
                logger.info("Test execution completed", extra={
                    "test_id": test_id,
                    "status": result["status"],
                    "attempt": attempt + 1
                })
                
                return test_id
            
            except asyncio.TimeoutError:
                logger.warning("Test execution timeout", extra={
                    "test_id": test_id,
                    "attempt": attempt + 1,
                    "timeout_seconds": settings.timeout_seconds
                })
                
                if attempt < settings.max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    # Final timeout failure
                    test_run.status = TestStatus.TIMEOUT.value
                    test_run.completed_at = datetime.utcnow()
                    test_run.error_code = "TIMEOUT"
                    self.db.commit()
                    return test_id
            
            except Exception as e:
                logger.error("Test execution error", extra={
                    "test_id": test_id,
                    "attempt": attempt + 1,
                    "error": str(e)
                })
                
                if attempt < settings.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    test_run.status = TestStatus.FAILED.value
                    test_run.completed_at = datetime.utcnow()
                    test_run.error_code = "EXECUTION_ERROR"
                    test_run.logs = [str(e)]
                    self.db.commit()
                    return test_id
        
        return test_id
    
    async def _run_test(
        self,
        test_id: str,
        test_type: TestType,
        inject_failure: FailureType,
        failure_probability: float
    ) -> dict:
        """Execute the actual test logic."""
        start_time = time.time()
        
        simulator = SystemSimulator()
        injector = FailureInjector(simulator)
        
        # Inject failure if requested
        if inject_failure != FailureType.NONE:
            injector.inject_failure(inject_failure, failure_probability)
        
        # Run test based on type
        if test_type == TestType.THERMAL_RAMP:
            success = await self._thermal_ramp_test(simulator)
        elif test_type == TestType.POWER_STRESS:
            success = await self._power_stress_test(simulator)
        elif test_type == TestType.CPU_STABILITY:
            success = await self._cpu_stability_test(simulator)
        elif test_type == TestType.FIRMWARE_HANDOFF:
            success = await self._firmware_handoff_test(simulator)
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Determine status
        if success and not simulator.failed:
            status = TestStatus.PASSED.value
            error_code = None
        else:
            status = TestStatus.FAILED.value
            error_code = simulator.failure_reason or "UNKNOWN"
        
        # Run RCA if test failed
        if status == TestStatus.FAILED.value:
            rca_engine = RCAEngine(self.db)
            await rca_engine.analyze_failure(test_id, simulator)
        
        return {
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "metrics": simulator.get_metrics(),
            "logs": simulator.logs,
            "error_code": error_code
        }
    
    async def _thermal_ramp_test(self, simulator: SystemSimulator) -> bool:
        """Thermal ramp test: 25°C → 85°C gradual increase."""
        simulator.add_log("Starting thermal ramp test")
        
        # Boot system first
        if not simulator.full_boot_sequence():
            return False
        
        # Apply thermal load
        simulator.apply_thermal_load(target_temp=85.0, duration_ms=2000)
        
        # Check for thermal runaway
        if simulator.cpu_temp > 90:
            simulator.add_log("FAILURE: Thermal runaway detected")
            simulator.failed = True
            simulator.failure_reason = "thermal_runaway"
            return False
        
        simulator.add_log("Thermal ramp test completed successfully")
        return True
    
    async def _power_stress_test(self, simulator: SystemSimulator) -> bool:
        """Power stress test: Load all rails to 90%."""
        simulator.add_log("Starting power stress test")
        
        if not simulator.full_boot_sequence():
            return False
        
        # Apply 90% power load
        success = simulator.apply_power_stress(load_percent=90)
        
        if success:
            simulator.add_log("Power stress test completed successfully")
        
        return success
    
    async def _cpu_stability_test(self, simulator: SystemSimulator) -> bool:
        """CPU stability soak: sustained load."""
        simulator.add_log("Starting CPU stability soak test")
        
        if not simulator.full_boot_sequence():
            return False
        
        # Simulate 10-minute soak (compressed for demo)
        simulator.cpu_frequency = 3600  # Max frequency
        simulator.cpu_temp = 75.0
        
        for i in range(5):
            simulator.read_sensor("cpu_temp", simulator.cpu_temp, "°C")
            simulator.read_sensor("cpu_freq", simulator.cpu_frequency, "MHz")
            
            if settings.enable_realistic_delays:
                await asyncio.sleep(0.2)
        
        simulator.add_log("CPU stability test completed successfully")
        return True
    
    async def _firmware_handoff_test(self, simulator: SystemSimulator) -> bool:
        """Firmware-to-OS handoff validation."""
        simulator.add_log("Starting firmware handoff test")
        
        # Boot and verify each stage transition
        if not simulator.boot_firmware():
            return False
        
        if simulator.boot_stage.value != "bootloader":
            simulator.add_log("FAILURE: Firmware did not transition to bootloader")
            simulator.failed = True
            simulator.failure_reason = "boot_failure"
            return False
        
        if not simulator.boot_bootloader():
            return False
        
        if simulator.boot_stage.value != "os_init":
            simulator.add_log("FAILURE: Bootloader did not transition to OS")
            simulator.failed = True
            simulator.failure_reason = "boot_failure"
            return False
        
        if not simulator.boot_os():
            return False
        
        simulator.add_log("Firmware handoff test completed successfully")
        return True
