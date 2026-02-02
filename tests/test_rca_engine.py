"""
Unit tests for RCAEngine.
"""

import pytest
from unittest.mock import MagicMock
from app.services.rca_engine import RCAEngine, RCACategory
from app.services.system_simulator import SystemSimulator


@pytest.mark.asyncio
async def test_thermal_failure_classification():
    """Test RCA correctly identifies thermal failures."""
    mock_db = MagicMock()
    rca_engine = RCAEngine(mock_db)
    
    simulator = SystemSimulator()
    simulator.cpu_temp = 95.0
    simulator.failed = True
    simulator.failure_reason = "thermal_runaway"
    
    features = rca_engine._extract_features(simulator)
    category, confidence = rca_engine._classify_failure(features)
    
    assert category == RCACategory.THERMAL
    assert confidence > 0.8


@pytest.mark.asyncio
async def test_power_failure_classification():
    """Test RCA correctly identifies power failures."""
    mock_db = MagicMock()
    rca_engine = RCAEngine(mock_db)
    
    simulator = SystemSimulator()
    simulator.voltage_12v = 10.5
    simulator.failed = True
    simulator.failure_reason = "voltage_droop"
    
    features = rca_engine._extract_features(simulator)
    category, confidence = rca_engine._classify_failure(features)
    
    assert category == RCACategory.POWER
    assert confidence > 0.5


@pytest.mark.asyncio
async def test_recommendations_generated():
    """Test that recommendations are generated for each category."""
    mock_db = MagicMock()
    rca_engine = RCAEngine(mock_db)
    
    recommendations = rca_engine._generate_recommendations(RCACategory.THERMAL)
    
    assert len(recommendations) > 0
    assert any("fan" in r.lower() for r in recommendations)
