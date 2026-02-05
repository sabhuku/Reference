"""
Tests for DriftMonitor

Verifies:
- Mean shift detection
- Distribution shift detection (KS test)
- Acceptance rate collapse detection
- High-confidence spike detection
- Baseline establishment
- Alert generation
"""
import unittest
from src.ai_remediation.drift_monitor import DriftMonitor, DriftAlert


class TestDriftMonitor(unittest.TestCase):
    """Test DriftMonitor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = DriftMonitor(window_size=1000, baseline_window_size=500)
    
    def _populate_baseline(self, mean_confidence=0.75, acceptance_rate=0.80):
        """Populate baseline with synthetic data."""
        for i in range(500):
            # Simulate normal distribution around mean
            import random
            raw = max(0.0, min(1.0, random.gauss(mean_confidence, 0.1)))
            calibrated = raw * 0.8  # Simulate calibration reduction
            passed = random.random() < acceptance_rate
            
            self.monitor.record_event(
                raw_confidence=raw,
                calibrated_confidence=calibrated,
                validation_passed=passed
            )
    
    def test_baseline_establishment(self):
        """Test that baseline is established after enough events."""
        self.assertFalse(self.monitor.baseline_established)
        
        # Add 500 events
        self._populate_baseline()
        
        self.assertTrue(self.monitor.baseline_established)
        self.assertIsNotNone(self.monitor.baseline_mean_raw)
        self.assertIsNotNone(self.monitor.baseline_mean_calibrated)
        self.assertIsNotNone(self.monitor.baseline_acceptance_rate)
    
    def test_mean_shift_warning(self):
        """Test mean shift warning detection."""
        # Establish baseline with mean ~0.75
        self._populate_baseline(mean_confidence=0.75)
        
        # Add 100 events with shifted mean (0.75 + 0.06 = 0.81)
        for i in range(100):
            self.monitor.record_event(
                raw_confidence=0.85,
                calibrated_confidence=0.68,
                validation_passed=True
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have mean shift warning (shift ~0.06, threshold 0.05)
        mean_shift_alerts = [a for a in alerts if a.alert_type == "mean_shift"]
        self.assertEqual(len(mean_shift_alerts), 1)
        self.assertEqual(mean_shift_alerts[0].severity, "warning")
    
    def test_mean_shift_critical(self):
        """Test mean shift critical detection."""
        # Establish baseline with mean ~0.75
        self._populate_baseline(mean_confidence=0.75)
        
        # Add 100 events with large shift (0.75 + 0.15 = 0.90)
        for i in range(100):
            self.monitor.record_event(
                raw_confidence=0.95,
                calibrated_confidence=0.76,
                validation_passed=True
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have mean shift critical (shift ~0.15, threshold 0.10)
        mean_shift_alerts = [a for a in alerts if a.alert_type == "mean_shift"]
        self.assertEqual(len(mean_shift_alerts), 1)
        self.assertEqual(mean_shift_alerts[0].severity, "critical")
    
    def test_acceptance_collapse_warning(self):
        """Test acceptance rate collapse warning."""
        # Establish baseline with 80% acceptance
        self._populate_baseline(acceptance_rate=0.80)
        
        # Add 100 events with 60% acceptance (25% drop)
        for i in range(100):
            passed = i < 60  # 60% pass rate
            self.monitor.record_event(
                raw_confidence=0.75,
                calibrated_confidence=0.60,
                validation_passed=passed
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have acceptance collapse warning (drop ~25%, threshold 20%)
        collapse_alerts = [a for a in alerts if a.alert_type == "acceptance_collapse"]
        self.assertEqual(len(collapse_alerts), 1)
        self.assertEqual(collapse_alerts[0].severity, "warning")
    
    def test_acceptance_collapse_critical(self):
        """Test acceptance rate collapse critical."""
        # Establish baseline with 80% acceptance
        self._populate_baseline(acceptance_rate=0.80)
        
        # Add 100 events with 40% acceptance (50% drop)
        for i in range(100):
            passed = i < 40  # 40% pass rate
            self.monitor.record_event(
                raw_confidence=0.75,
                calibrated_confidence=0.60,
                validation_passed=passed
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have acceptance collapse critical (drop ~50%, threshold 40%)
        collapse_alerts = [a for a in alerts if a.alert_type == "acceptance_collapse"]
        self.assertEqual(len(collapse_alerts), 1)
        self.assertEqual(collapse_alerts[0].severity, "critical")
    
    def test_high_confidence_spike_warning(self):
        """Test high-confidence spike warning."""
        # Establish baseline with normal distribution
        self._populate_baseline(mean_confidence=0.75)
        
        # Add 100 events with 35% high-confidence (>0.9)
        for i in range(100):
            raw = 0.95 if i < 35 else 0.70
            self.monitor.record_event(
                raw_confidence=raw,
                calibrated_confidence=raw * 0.8,
                validation_passed=True
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have high-confidence spike warning (35%, threshold 30%)
        spike_alerts = [a for a in alerts if a.alert_type == "high_confidence_spike"]
        self.assertEqual(len(spike_alerts), 1)
        self.assertEqual(spike_alerts[0].severity, "warning")
    
    def test_high_confidence_spike_critical(self):
        """Test high-confidence spike critical."""
        # Establish baseline with normal distribution
        self._populate_baseline(mean_confidence=0.75)
        
        # Add 100 events with 55% high-confidence (>0.9)
        for i in range(100):
            raw = 0.95 if i < 55 else 0.70
            self.monitor.record_event(
                raw_confidence=raw,
                calibrated_confidence=raw * 0.8,
                validation_passed=True
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have high-confidence spike critical (55%, threshold 50%)
        spike_alerts = [a for a in alerts if a.alert_type == "high_confidence_spike"]
        self.assertEqual(len(spike_alerts), 1)
        self.assertEqual(spike_alerts[0].severity, "critical")
    
    def test_no_drift_detected(self):
        """Test that no drift is detected when metrics are stable."""
        # Establish baseline
        self._populate_baseline(mean_confidence=0.75, acceptance_rate=0.80)
        
        # Add 100 events with similar distribution
        for i in range(100):
            import random
            raw = max(0.0, min(1.0, random.gauss(0.75, 0.1)))
            calibrated = raw * 0.8
            passed = random.random() < 0.80
            
            self.monitor.record_event(
                raw_confidence=raw,
                calibrated_confidence=calibrated,
                validation_passed=passed
            )
        
        # Detect drift
        alerts = self.monitor.detect_drift()
        
        # Should have no alerts
        self.assertEqual(len(alerts), 0)
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        # Before baseline
        stats = self.monitor.get_statistics()
        self.assertFalse(stats['baseline_established'])
        
        # After baseline
        self._populate_baseline()
        stats = self.monitor.get_statistics()
        
        self.assertTrue(stats['baseline_established'])
        self.assertIn('baseline', stats)
        self.assertIn('recent', stats)
        self.assertIn('mean_raw', stats['baseline'])
        self.assertIn('acceptance_rate', stats['recent'])
    
    def test_drift_alert_serialization(self):
        """Test DriftAlert serialization."""
        alert = DriftAlert(
            alert_type="mean_shift",
            severity="critical",
            metric_value=0.15,
            threshold=0.10,
            recommendation="Retrain calibration",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        # Convert to dict
        alert_dict = alert.to_dict()
        
        self.assertEqual(alert_dict['alert_type'], "mean_shift")
        self.assertEqual(alert_dict['severity'], "critical")
        self.assertEqual(alert_dict['metric_value'], 0.15)


if __name__ == "__main__":
    unittest.main()
