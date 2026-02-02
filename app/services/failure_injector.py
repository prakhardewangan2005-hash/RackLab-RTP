"""
Deterministic failure injection for testing RCA capabilities.
Supports thermal, power, firmware, and mechanical failures.
"""

import random
from app.models import FailureType
from app.services.system_simulator import SystemSimulator
from app.logger import get_logger

logger = get_logger(__name__)


class FailureInjector:
    """
    Injects realistic hardware failures into the system simulator.
    Failures are deterministic based on probability.
    """
    
    def __init__(self, simulator: SystemSimulator):
        self.simulator = simulator
    
    def inject_failure(self, failure_type: FailureType, probability: float = 1.0):
        """
        Inject a specific failure with given probability.
        
        Args:
            failure_type: Type of failure to inject
            probability: Probability of injection (0.0 to 1.0)
        """
        if random.random() > probability:
            logger.info("Failure injection skipped based on probability", extra={
                "failure_type": failure_type.value,
                "probability": probability
            })
            return
        
        logger.info("Injecting failure", extra={
            "failure_type": failure_type.value
        })
        
        if failure_type == FailureType.THERMAL_RUNAWAY:
            self._inject_thermal_runaway()
        elif failure_type == FailureType.VOLTAGE_DROOP:
            self._inject_voltage_droop()
        elif failure_type == FailureType.BOOT_FAILURE:
            self._inject_boot_failure()
        elif failure_type == FailureType.FAN_STUCK:
            self._inject_fan_stuck()
    
    def _inject_thermal_runaway(self):
        """Simulate thermal runaway condition."""
        self.simulator.add_log("INJECTED FAILURE: Thermal runaway")
        self.simulator.cpu_temp = 95.0  # Critical temperature
        self.simulator.failed = True
        self.simulator.failure_reason = "thermal_runaway"
        
        logger.warning("Thermal runaway injected", extra={
            "cpu_temp": self.simulator.cpu_temp
        })
    
    def _inject_voltage_droop(self):
        """Simulate excessive voltage droop."""
        self.simulator.add_log("INJECTED FAILURE: Voltage droop")
        self.simulator.voltage_12v = 10.5  # Below tolerance
        self.simulator.voltage_5v = 4.5
        self.simulator.failed = True
        self.simulator.failure_reason = "voltage_droop"
        
        logger.warning("Voltage droop injected", extra={
            "voltage_12v": self.simulator.voltage_12v
        })
    
    def _inject_boot_failure(self):
        """Simulate boot failure."""
        self.simulator.add_log("INJECTED FAILURE: Boot failure")
        # Will cause boot sequence to fail
        self.simulator.failed = True
        self.simulator.failure_reason = "boot_failure"
        
        logger.warning("Boot failure injected")
    
    def _inject_fan_stuck(self):
        """Simulate stuck fan."""
        self.simulator.add_log("INJECTED FAILURE: Fan stuck")
        self.simulator.fan_rpm = 0  # Fan not spinning
        self.simulator.failed = True
        self.simulator.failure_reason = "fan_stuck"
        
        logger.warning("Fan stuck injected", extra={
            "fan_rpm": self.simulator.fan_rpm
        })
