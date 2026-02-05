"""
Tests for CalibrationService

Verifies:
- Platt scaling calibration
- Isotonic regression calibration
- Clamping to [0, 1]
- Fail-closed behavior (missing profile)
- Never increases confidence without empirical basis
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path
from src.ai_remediation.calibration_service import (
    CalibrationService,
    CalibrationProfile,
    create_default_profile
)


class TestCalibrationProfile(unittest.TestCase):
    """Test CalibrationProfile data class."""
    
    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        profile = CalibrationProfile(
            model_version="test-model",
            method="platt",
            parameters={"A": 1.0, "B": 0.5},
            created_at="2024-01-01T00:00:00Z",
            sample_size=100,
            description="Test profile"
        )
        
        # Convert to dict and back
        data = profile.to_dict()
        restored = CalibrationProfile.from_dict(data)
        
        self.assertEqual(profile.model_version, restored.model_version)
        self.assertEqual(profile.method, restored.method)
        self.assertEqual(profile.parameters, restored.parameters)


class TestCalibrationService(unittest.TestCase):
    """Test CalibrationService functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test profiles
        self.temp_dir = tempfile.mkdtemp()
        self.service = CalibrationService(profiles_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_platt_scaling(self):
        """Test Platt scaling calibration."""
        # Create a profile with known parameters
        # A=1.0, B=0.9 should reduce confidence
        profile = CalibrationProfile(
            model_version="test-platt",
            method="platt",
            parameters={"A": 1.0, "B": 0.9},
            created_at="2024-01-01T00:00:00Z",
            sample_size=100,
            description="Test Platt profile"
        )
        
        self.service.save_profile(profile)
        
        # Test calibration
        raw = 0.9
        calibrated = self.service.calibrate(raw, "test-platt")
        
        # Should reduce confidence
        self.assertLess(calibrated, raw)
        self.assertGreaterEqual(calibrated, 0.0)
        self.assertLessEqual(calibrated, 1.0)
    
    def test_isotonic_regression(self):
        """Test isotonic regression calibration."""
        # Create isotonic profile with bins
        profile = CalibrationProfile(
            model_version="test-isotonic",
            method="isotonic",
            parameters={
                "bins": [
                    [0.5, 0.3],  # raw <= 0.5 → 0.3
                    [0.7, 0.5],  # raw <= 0.7 → 0.5
                    [0.9, 0.7],  # raw <= 0.9 → 0.7
                    [1.0, 0.85]  # raw <= 1.0 → 0.85
                ]
            },
            created_at="2024-01-01T00:00:00Z",
            sample_size=100,
            description="Test isotonic profile"
        )
        
        self.service.save_profile(profile)
        
        # Test calibration
        self.assertAlmostEqual(self.service.calibrate(0.4, "test-isotonic"), 0.3)
        self.assertAlmostEqual(self.service.calibrate(0.6, "test-isotonic"), 0.5)
        self.assertAlmostEqual(self.service.calibrate(0.8, "test-isotonic"), 0.7)
        self.assertAlmostEqual(self.service.calibrate(0.95, "test-isotonic"), 0.85)
    
    def test_clamping(self):
        """Test that output is clamped to [0, 1]."""
        # Create a profile that might produce out-of-range values
        profile = CalibrationProfile(
            model_version="test-clamp",
            method="platt",
            parameters={"A": -10.0, "B": -5.0},  # Extreme parameters
            created_at="2024-01-01T00:00:00Z",
            sample_size=100,
            description="Test clamping"
        )
        
        self.service.save_profile(profile)
        
        # Test various inputs
        for raw in [0.0, 0.5, 1.0]:
            calibrated = self.service.calibrate(raw, "test-clamp")
            self.assertGreaterEqual(calibrated, 0.0)
            self.assertLessEqual(calibrated, 1.0)
    
    def test_fail_closed_missing_profile(self):
        """Test fail-closed behavior when profile is missing."""
        raw = 0.9
        
        # With fail_closed=True (default), should use conservative fallback
        calibrated = self.service.calibrate(raw, "nonexistent-model", fail_closed=True)
        
        # Should reduce confidence by ~20%
        expected = raw * 0.8
        self.assertAlmostEqual(calibrated, expected)
        self.assertLess(calibrated, raw)
    
    def test_fail_open_missing_profile(self):
        """Test fail-open behavior (not recommended for production)."""
        raw = 0.9
        
        # With fail_closed=False, should return raw score
        calibrated = self.service.calibrate(raw, "nonexistent-model", fail_closed=False)
        
        self.assertEqual(calibrated, raw)
    
    def test_never_increases_without_basis(self):
        """Test that calibration never increases confidence without empirical basis."""
        # Default conservative profile should always reduce or maintain confidence
        profile = create_default_profile("test-conservative")
        self.service.save_profile(profile)
        
        # Test various raw scores
        for raw in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]:
            calibrated = self.service.calibrate(raw, "test-conservative")
            
            # Calibrated should be <= raw (never increase)
            self.assertLessEqual(
                calibrated, raw,
                f"Calibration increased confidence: {raw} → {calibrated}"
            )
    
    def test_invalid_confidence_range(self):
        """Test that invalid confidence values raise errors."""
        with self.assertRaises(ValueError):
            self.service.calibrate(1.5, "test-model")
        
        with self.assertRaises(ValueError):
            self.service.calibrate(-0.1, "test-model")
    
    def test_profile_caching(self):
        """Test that profiles are cached after first load."""
        profile = create_default_profile("test-cache")
        self.service.save_profile(profile)
        
        # Load profile twice
        profile1 = self.service.load_profile("test-cache")
        profile2 = self.service.load_profile("test-cache")
        
        # Should be the same object (cached)
        self.assertIs(profile1, profile2)
    
    def test_create_default_profile(self):
        """Test default profile creation."""
        profile = create_default_profile("gpt-4-default")
        
        self.assertEqual(profile.model_version, "gpt-4-default")
        self.assertEqual(profile.method, "platt")
        self.assertIn("A", profile.parameters)
        self.assertIn("B", profile.parameters)
        self.assertEqual(profile.sample_size, 0)


if __name__ == "__main__":
    unittest.main()
