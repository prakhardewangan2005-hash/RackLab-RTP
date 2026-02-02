"""
Root Cause Analysis engine using Bayesian classification.
Analyzes failure patterns and provides confident diagnoses.
"""

from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import RCARecord, RCACategory
from app.services.system_simulator import SystemSimulator
from app.logger import get_logger

logger = get_logger(__name__)


class RCAEngine:
    """
    Automated Root Cause Analysis using pattern matching and heuristics.
    Production system would use ML models trained on historical data.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def analyze_failure(self, test_id: str, simulator: SystemSimulator) -> RCARecord:
        """
        Analyze failure and classify root cause with confidence scoring.
        
        Args:
            test_id: Test run identifier
            simulator: System simulator with failure state
        
        Returns:
            RCARecord with classification and recommendations
        """
        logger.info("Starting RCA analysis", extra={"test_id": test_id})
        
        # Extract features from simulator state
        features = self._extract_features(simulator)
        
        # Classify failure
        category, confidence = self._classify_failure(features)
        
        # Generate root cause description
        root_cause = self._generate_root_cause(category, features)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(category)
        
        # Persist RCA result
        rca_record = RCARecord(
            test_id=test_id,
            category=category.value,
            confidence=confidence,
            root_cause=root_cause,
            recommendations=recommendations,
            created_at=datetime.utcnow()
        )
        
        self.db.add(rca_record)
        self.db.commit()
        
        logger.info("RCA analysis completed", extra={
            "test_id": test_id,
            "category": category.value,
            "confidence": confidence
        })
        
        return rca_record
    
    def _extract_features(self, simulator: SystemSimulator) -> Dict:
        """Extract relevant features for classification."""
        metrics = simulator.get_metrics()
        
        return {
            "cpu_temp": metrics["cpu_temp_c"],
            "voltage_12v": metrics["voltage_12v"],
            "voltage_5v": metrics["voltage_5v"],
            "fan_rpm": metrics["fan_rpm"],
            "boot_stage": metrics["boot_stage"],
            "failure_reason": simulator.failure_reason,
            "logs": simulator.logs
        }
    
    def _classify_failure(self, features: Dict) -> tuple[RCACategory, float]:
        """
        Classify failure using Bayesian-inspired heuristics.
        Returns (category, confidence).
        """
        # Rule-based classification with confidence scoring
        
        # THERMAL classification
        if features["cpu_temp"] > 90:
            confidence = min(1.0, (features["cpu_temp"] - 85) / 15)
            return RCACategory.THERMAL, confidence
        
        # POWER classification
        if features["voltage_12v"] < 11.0 or features["voltage_5v"] < 4.5:
            voltage_deviation = abs(12.0 - features["voltage_12v"]) / 12.0
            confidence = min(1.0, voltage_deviation * 10)
            return RCACategory.POWER, confidence
        
        # FIRMWARE classification
        if features["boot_stage"] in ["firmware", "bootloader"]:
            if features["failure_reason"] == "boot_failure":
                return RCACategory.FIRMWARE, 0.95
        
        # OS classification
        if features["boot_stage"] == "os_init":
            if features["failure_reason"] == "boot_failure":
                return RCACategory.OS, 0.90
        
        # Check for fan failures (could be thermal or mechanical)
        if features["fan_rpm"] < 500:
            # Classify as thermal since it affects cooling
            return RCACategory.THERMAL, 0.85
        
        # Default: unknown with low confidence
        return RCACategory.UNKNOWN, 0.30
    
    def _generate_root_cause(self, category: RCACategory, features: Dict) -> str:
        """Generate human-readable root cause description."""
        if category == RCACategory.THERMAL:
            if features["fan_rpm"] < 500:
                return f"Fan failure detected (RPM: {features['fan_rpm']}). Insufficient cooling causing thermal runaway."
            else:
                return f"CPU temperature exceeded safe operating limits ({features['cpu_temp']:.1f}°C). Possible cooling system degradation or excessive workload."
        
        elif category == RCACategory.POWER:
            return f"Voltage rail out of specification. 12V rail measured at {features['voltage_12v']:.2f}V (spec: 11.4-12.6V). Likely PSU failure or excessive load."
        
        elif category == RCACategory.FIRMWARE:
            return f"System failed during {features['boot_stage']} stage. Firmware corruption or incompatible version suspected."
        
        elif category == RCACategory.OS:
            return "Operating system initialization failed. Possible kernel panic, driver issue, or corrupted boot image."
        
        else:
            return f"Failure cause unclear. System state: {features['boot_stage']}, failure_reason: {features['failure_reason']}"
    
    def _generate_recommendations(self, category: RCACategory) -> List[str]:
        """Generate actionable recommendations based on category."""
        recommendations = {
            RCACategory.THERMAL: [
                "Verify fan operation and replace if RPM < 1000",
                "Clean dust from heatsinks and air intakes",
                "Check thermal paste application on CPU",
                "Reduce ambient temperature or improve rack airflow",
                "Consider thermal throttling threshold adjustment"
            ],
            RCACategory.POWER: [
                "Inspect power supply unit for failures",
                "Measure voltage rails under load with oscilloscope",
                "Check for loose power connectors",
                "Verify power distribution board integrity",
                "Replace PSU if voltage deviation exceeds 5%"
            ],
            RCACategory.FIRMWARE: [
                "Reflash firmware to known-good version",
                "Verify firmware checksums match golden image",
                "Check for BIOS/UEFI corruption",
                "Update to latest stable firmware release",
                "Review boot logs for specific error codes"
            ],
            RCACategory.OS: [
                "Boot in safe mode to isolate driver issues",
                "Check kernel logs for panic messages",
                "Verify boot image integrity",
                "Test with minimal driver set",
                "Reinstall OS if corruption suspected"
            ],
            RCACategory.UNKNOWN: [
                "Collect full system logs for manual analysis",
                "Run comprehensive hardware diagnostics",
                "Check for intermittent connection issues",
                "Monitor system over extended period",
                "Escalate to hardware engineering team"
            ]
        }
        
        return recommendations.get(category, recommendations[RCACategory.UNKNOWN])
