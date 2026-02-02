"""
Unit tests for TestRunner.
"""

import pytest
from unittest.mock import MagicMock
from app.services.test_runner import TestRunner
from app.models import TestType, FailureType


@pytest.mark.asyncio
async def test_execute_test_creates_record():
    """Test that execute_test creates a database record."""
    mock_db = MagicMock()
    runner = TestRunner(mock_db)
    
    test_id = await runner.execute_test(
        test_type=TestType.THERMAL_RAMP,
        inject_failure=FailureType.NONE,
        failure_probability=0.0
    )
    
    assert test_id is not None
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_thermal_ramp_test_passes():
    """Test thermal ramp test execution."""
    mock_db = MagicMock()
    runner = TestRunner(mock_db)
    
    from app.services.system_simulator import SystemSimulator
    simulator = SystemSimulator()
    
    success = await runner._thermal_ramp_test(simulator)
    
    assert success is True
    assert simulator.cpu_temp > 25.0  # Temperature increased
    assert not simulator.failed


@pytest.mark.asyncio
async def test_firmware_handoff_validates_stages():
    """Test firmware handoff validates each boot stage."""
    mock_db = MagicMock()
    runner = TestRunner(mock_db)
    
    from app.services.system_simulator import SystemSimulator
    simulator = SystemSimulator()
    
    success = await runner._firmware_handoff_test(simulator)
    
    assert success is True
    assert simulator.boot_stage.value == "complete"
