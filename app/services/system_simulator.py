"""
System simulation layer for hardware bring-up.
Simulates boot stages, subsystems, and sensor readings.
"""

import random
import time
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from app.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class BootStage(Enum):
    """Boot sequence stages."""
    FIRMWARE = "firmware"
    BOOTLOADER = "bootloader"
    OS_INIT = "os_init"
    COMPLETE = "complete"


@dataclass
class SensorReading:
    """Sensor reading with timestamp."""
    name: str
    value: float
    unit: str
    timestamp: float
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": self.timestamp
        }


class SystemSimulator:
    """
    Simulates a complete rack system with realistic hardware behavior.
    Deterministic boot sequence with configurable failure injection.
    """
    
    def __init__(self):
        self.boot_stage = BootStage.FIRMWARE
        self.cpu_temp = 25.0  # Celsius
        self.cpu_frequency = 2400  # MHz
        self.voltage_12v = 12.0
        self.voltage_5v = 5.0
        self.voltage_3v3 = 3.3
        self.fan_rpm = 2000
        self.power_draw = 150  # Watts
        
        self.logs: List[str] = []
        self.sensor_history: List[SensorReading] = []
        self.failed = False
        self.failure_reason = None
    
    def reset(self):
        """Reset system to initial state."""
        self.__init__()
    
    def add_log(self, message: str):
        """Add timestamped log entry."""
        timestamp = time.time()
        log_entry = f"[{timestamp:.3f}] {message}"
        self.logs.append(log_entry)
        logger.debug("Simulator log", extra={"message": message})
    
    def read_sensor(self, name: str, value: float, unit: str) -> SensorReading:
        """
        Record sensor reading with realistic noise.
        """
        if settings.sensor_noise_percent > 0:
            noise = random.uniform(
                -settings.sensor_noise_percent / 100,
                settings.sensor_noise_percent / 100
            )
            value = value * (1 + noise)
        
        reading = SensorReading(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time()
        )
        self.sensor_history.append(reading)
        return reading
    
    def boot_firmware(self) -> bool:
        """Execute firmware boot stage."""
        self.add_log("Starting firmware initialization")
        
        if settings.enable_realistic_delays:
            time.sleep(0.1)
        
        # POST checks
        self.add_log("Running POST checks")
        self.read_sensor("cpu_temp", self.cpu_temp, "°C")
        self.read_sensor("voltage_12v", self.voltage_12v, "V")
        
        if self.voltage_12v < 11.5:
            self.add_log("ERROR: Voltage rail 12V out of spec")
            self.failed = True
            self.failure_reason = "voltage_droop"
            return False
        
        self.add_log("Firmware initialized successfully")
        self.boot_stage = BootStage.BOOTLOADER
        return True
    
    def boot_bootloader(self) -> bool:
        """Execute bootloader stage."""
        self.add_log("Loading bootloader")
        
        if settings.enable_realistic_delays:
            time.sleep(0.05)
        
        self.cpu_frequency = 3200  # Increase frequency
        self.add_log(f"CPU frequency set to {self.cpu_frequency} MHz")
        
        self.read_sensor("cpu_freq", self.cpu_frequency, "MHz")
        self.read_sensor("fan_rpm", self.fan_rpm, "RPM")
        
        if self.fan_rpm < 500:
            self.add_log("ERROR: Fan not spinning")
            self.failed = True
            self.failure_reason = "fan_stuck"
            return False
        
        self.add_log("Bootloader loaded successfully")
        self.boot_stage = BootStage.OS_INIT
        return True
    
    def boot_os(self) -> bool:
        """Execute OS initialization."""
        self.add_log("Initializing operating system")
        
        if settings.enable_realistic_delays:
            time.sleep(0.15)
        
        # Simulate OS load increasing power draw
        self.power_draw = 250
        self.cpu_temp = 45.0
        
        self.read_sensor("power_draw", self.power_draw, "W")
        self.read_sensor("cpu_temp", self.cpu_temp, "°C")
        
        self.add_log("OS initialized successfully")
        self.boot_stage = BootStage.COMPLETE
        return True
    
    def full_boot_sequence(self) -> bool:
        """Execute complete boot sequence."""
        stages = [
            ("Firmware", self.boot_firmware),
            ("Bootloader", self.boot_bootloader),
            ("OS", self.boot_os)
        ]
        
        for stage_name, stage_func in stages:
            if not stage_func():
                self.add_log(f"Boot failed at {stage_name} stage")
                return False
        
        self.add_log("System boot complete")
        return True
    
    def apply_thermal_load(self, target_temp: float, duration_ms: int):
        """
        Simulate thermal ramp by gradually increasing temperature.
        """
        steps = 10
        temp_delta = target_temp - self.cpu_temp
        step_size = temp_delta / steps
        
        for i in range(steps):
            self.cpu_temp += step_size
            self.read_sensor("cpu_temp", self.cpu_temp, "°C")
            
            # Simulate thermal throttling
            if self.cpu_temp > 85:
                self.cpu_frequency = max(1200, self.cpu_frequency - 200)
                self.add_log(f"Thermal throttling: CPU freq reduced to {self.cpu_frequency} MHz")
            
            if settings.enable_realistic_delays:
                time.sleep(duration_ms / steps / 1000)
        
        self.add_log(f"Thermal load complete: {self.cpu_temp:.1f}°C")
    
    def apply_power_stress(self, load_percent: float):
        """
        Simulate high power load on all rails.
        """
        self.power_draw = 400 * (load_percent / 100)
        
        # Voltage droop under load
        droop_factor = load_percent / 100 * 0.1
        self.voltage_12v = 12.0 * (1 - droop_factor)
        self.voltage_5v = 5.0 * (1 - droop_factor)
        self.voltage_3v3 = 3.3 * (1 - droop_factor)
        
        self.read_sensor("power_draw", self.power_draw, "W")
        self.read_sensor("voltage_12v", self.voltage_12v, "V")
        self.read_sensor("voltage_5v", self.voltage_5v, "V")
        self.read_sensor("voltage_3v3", self.voltage_3v3, "V")
        
        if self.voltage_12v < 10.8:  # 10% tolerance
            self.add_log("CRITICAL: Voltage droop exceeds tolerance")
            self.failed = True
            self.failure_reason = "voltage_droop"
            return False
        
        self.add_log(f"Power stress applied: {self.power_draw:.1f}W")
        return True
    
    def get_metrics(self) -> Dict:
        """Get current system metrics."""
        return {
            "boot_stage": self.boot_stage.value,
            "cpu_temp_c": round(self.cpu_temp, 2),
            "cpu_freq_mhz": self.cpu_frequency,
            "voltage_12v": round(self.voltage_12v, 3),
            "voltage_5v": round(self.voltage_5v, 3),
            "voltage_3v3": round(self.voltage_3v3, 3),
            "fan_rpm": self.fan_rpm,
            "power_draw_w": round(self.power_draw, 2),
            "sensor_readings": len(self.sensor_history)
        }
