"""
Unit tests for SystemSimulator.
"""

import pytest
from app.services.system_simulator import SystemSimulator, BootStage


def test_system_boot_sequence():
    """Test complete boot sequence executes successfully."""
    simulator = SystemSimulator()
    
    success = simulator.full_boot_sequence()
    
    assert success is True
    assert simulator.boot_stage == BootStage.COMPLETE
    assert len(simulator.logs) > 0
    assert not simulator.failed


def test_thermal_load_application():
    """Test thermal load increases temperature correctly."""
    simulator = SystemSimulator()
    initial_temp = simulator.cpu_temp
    
    simulator.apply_thermal_load(target_temp=85.0, duration_ms=1000)
    
    assert simulator.cpu_temp > initial_temp
    assert simulator.cpu_temp >= 80.0  # Should reach near target
    assert len(simulator.sensor_history) > 0


def test_voltage_droop_detection():
    """Test voltage droop causes failure."""
    simulator = SystemSimulator()
    simulator.voltage_12v = 10.0  # Below tolerance
    
    success = simulator.boot_firmware()
    
    assert success is False
    assert simulator.failed is True
    assert simulator.failure_reason == "voltage_droop"


def test_sensor_readings_recorded():
    """Test sensor readings are properly recorded."""
    simulator = SystemSimulator()
    
    reading = simulator.read_sensor("test_sensor", 42.0, "units")
    
    assert reading.name == "test_sensor"
    assert reading.value == pytest.approx(42.0, abs=1.0)  # Allow for noise
    assert reading.unit == "units"
    assert len(simulator.sensor_history) == 1


def test_reset_clears_state():
    """Test reset returns simulator to initial state."""
    simulator = SystemSimulator()
    simulator.full_boot_sequence()
    simulator.failed = True
    
    simulator.reset()
    
    assert simulator.boot_stage == BootStage.FIRMWARE
    assert len(simulator.logs) == 0
    assert not simulator.failed
