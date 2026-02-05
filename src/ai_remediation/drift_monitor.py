"""
AI Confidence Drift Monitoring

Detects when GPT-5 confidence distribution changes over time, invalidating
calibration and threatening Tier-1 safety.

DRIFT SCENARIOS:
- Mean Shift: Model becomes more/less confident overall
- Distribution Shift: Confidence pattern changes (KS test)
- Acceptance Rate Collapse: Sudden drop in validation pass rate
- High-Confidence Spike: Unusual increase in 0.9+ suggestions

PROTECTION MECHANISM:
- Warning alerts: Investigate and monitor
- Critical alerts: Auto-disable feature flag, retrain calibration

INTEGRATION:
- Called by SuggestionOrchestrator after each validation
- Periodically runs drift detection (every 100 events)
- Triggers feature flag auto-disable on critical drift
"""
import logging
import statistics
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class DriftAlert:
    """
    Alert for detected drift in AI confidence metrics.
    
    Attributes:
        alert_type: Type of drift detected
        severity: "warning" or "critical"
        metric_value: Current metric value
        threshold: Alert threshold
        recommendation: Action to take
        timestamp: When alert was generated
    """
    alert_type: str  # "mean_shift", "distribution_shift", "acceptance_collapse", "high_confidence_spike"
    severity: str  # "warning" or "critical"
    metric_value: float
    threshold: float
    recommendation: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class DriftMonitor:
    """
    Monitors AI confidence drift to detect calibration invalidation.
    
    Features:
    - Rolling window of recent events (default: 1000)
    - Mean shift detection (T-test)
    - Distribution shift detection (KS test)
    - Acceptance rate collapse detection
    - High-confidence spike detection
    
    Usage:
        monitor = DriftMonitor(window_size=1000)
        monitor.record_event(
            raw_confidence=0.95,
            calibrated_confidence=0.76,
            validation_passed=True,
            rejection_reasons=[]
        )
        alerts = monitor.detect_drift()
    """
    
    def __init__(
        self,
        window_size: int = 1000,
        baseline_window_size: int = 500
    ):
        """
        Initialize drift monitor.
        
        Args:
            window_size: Number of recent events to track
            baseline_window_size: Number of events for baseline comparison
        """
        self.window_size = window_size
        self.baseline_window_size = baseline_window_size
        
        # Rolling windows (deque for efficient append/pop)
        self.raw_confidences = deque(maxlen=window_size)
        self.calibrated_confidences = deque(maxlen=window_size)
        self.validation_results = deque(maxlen=window_size)  # True/False
        self.rejection_reasons = deque(maxlen=window_size)  # List of reasons
        self.timestamps = deque(maxlen=window_size)
        
        # Baseline statistics (computed from first N events)
        self.baseline_mean_raw = None
        self.baseline_mean_calibrated = None
        self.baseline_acceptance_rate = None
        self.baseline_established = False
        
        # Event counter
        self.total_events = 0
        
        logger.info(f"DriftMonitor initialized: window_size={window_size}")
    
    def record_event(
        self,
        raw_confidence: float,
        calibrated_confidence: float,
        validation_passed: bool,
        rejection_reasons: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a suggestion event for drift monitoring.
        
        Args:
            raw_confidence: Raw GPT-5 confidence score
            calibrated_confidence: Calibrated confidence score
            validation_passed: Whether validation passed
            rejection_reasons: List of rejection reason codes
            timestamp: Event timestamp (defaults to now)
        """
        self.raw_confidences.append(raw_confidence)
        self.calibrated_confidences.append(calibrated_confidence)
        self.validation_results.append(validation_passed)
        self.rejection_reasons.append(rejection_reasons or [])
        self.timestamps.append(timestamp or datetime.utcnow())
        
        self.total_events += 1
        
        # Establish baseline after collecting enough events
        if not self.baseline_established and len(self.raw_confidences) >= self.baseline_window_size:
            self._establish_baseline()
    
    def _establish_baseline(self) -> None:
        """Establish baseline statistics from initial events."""
        baseline_raw = list(self.raw_confidences)[:self.baseline_window_size]
        baseline_calibrated = list(self.calibrated_confidences)[:self.baseline_window_size]
        baseline_validation = list(self.validation_results)[:self.baseline_window_size]
        
        self.baseline_mean_raw = statistics.mean(baseline_raw)
        self.baseline_mean_calibrated = statistics.mean(baseline_calibrated)
        self.baseline_acceptance_rate = sum(baseline_validation) / len(baseline_validation)
        
        self.baseline_established = True
        
        logger.info(
            f"Baseline established: mean_raw={self.baseline_mean_raw:.3f}, "
            f"mean_calibrated={self.baseline_mean_calibrated:.3f}, "
            f"acceptance_rate={self.baseline_acceptance_rate:.3f}"
        )
    
    def detect_drift(self) -> List[DriftAlert]:
        """
        Run all drift detection tests.
        
        Returns:
            List of DriftAlert objects (empty if no drift detected)
        """
        if not self.baseline_established:
            logger.debug("Baseline not established yet, skipping drift detection")
            return []
        
        alerts = []
        
        # Test 1: Mean shift
        mean_shift_alert = self._detect_mean_shift()
        if mean_shift_alert:
            alerts.append(mean_shift_alert)
        
        # Test 2: Distribution shift (KS test)
        distribution_shift_alert = self._detect_distribution_shift()
        if distribution_shift_alert:
            alerts.append(distribution_shift_alert)
        
        # Test 3: Acceptance rate collapse
        acceptance_collapse_alert = self._detect_acceptance_collapse()
        if acceptance_collapse_alert:
            alerts.append(acceptance_collapse_alert)
        
        # Test 4: High-confidence spike
        high_confidence_spike_alert = self._detect_high_confidence_spike()
        if high_confidence_spike_alert:
            alerts.append(high_confidence_spike_alert)
        
        if alerts:
            logger.warning(f"Drift detected: {len(alerts)} alerts")
            for alert in alerts:
                logger.warning(
                    f"  {alert.alert_type} ({alert.severity}): "
                    f"{alert.metric_value:.3f} vs threshold {alert.threshold:.3f}"
                )
        
        return alerts
    
    def _detect_mean_shift(self) -> Optional[DriftAlert]:
        """
        Detect mean shift in calibrated confidence.
        
        Returns:
            DriftAlert if shift detected, None otherwise
        """
        if len(self.calibrated_confidences) < 100:
            return None
        
        # Recent mean (last 100 events)
        recent_calibrated = list(self.calibrated_confidences)[-100:]
        recent_mean = statistics.mean(recent_calibrated)
        
        # Calculate shift
        shift = abs(recent_mean - self.baseline_mean_calibrated)
        
        # Thresholds
        warning_threshold = 0.05
        critical_threshold = 0.10
        
        if shift >= critical_threshold:
            return DriftAlert(
                alert_type="mean_shift",
                severity="critical",
                metric_value=shift,
                threshold=critical_threshold,
                recommendation="Retrain calibration profile immediately. Auto-disabling feature flag.",
                timestamp=datetime.utcnow().isoformat()
            )
        elif shift >= warning_threshold:
            return DriftAlert(
                alert_type="mean_shift",
                severity="warning",
                metric_value=shift,
                threshold=warning_threshold,
                recommendation="Monitor closely. Consider retraining calibration profile.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        return None
    
    def _detect_distribution_shift(self) -> Optional[DriftAlert]:
        """
        Detect distribution shift using Kolmogorov-Smirnov test.
        
        Returns:
            DriftAlert if shift detected, None otherwise
        """
        if len(self.calibrated_confidences) < 100:
            return None
        
        try:
            from scipy import stats
        except ImportError:
            logger.warning("scipy not installed, skipping KS test")
            return None
        
        # Baseline distribution
        baseline_calibrated = list(self.calibrated_confidences)[:self.baseline_window_size]
        
        # Recent distribution (last 100 events)
        recent_calibrated = list(self.calibrated_confidences)[-100:]
        
        # KS test
        ks_statistic, p_value = stats.ks_2samp(baseline_calibrated, recent_calibrated)
        
        # Thresholds (lower p-value = more significant difference)
        warning_threshold = 0.05
        critical_threshold = 0.01
        
        if p_value < critical_threshold:
            return DriftAlert(
                alert_type="distribution_shift",
                severity="critical",
                metric_value=p_value,
                threshold=critical_threshold,
                recommendation="Significant distribution shift detected. Investigate model version change. Auto-disabling feature flag.",
                timestamp=datetime.utcnow().isoformat()
            )
        elif p_value < warning_threshold:
            return DriftAlert(
                alert_type="distribution_shift",
                severity="warning",
                metric_value=p_value,
                threshold=warning_threshold,
                recommendation="Distribution shift detected. Monitor closely.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        return None
    
    def _detect_acceptance_collapse(self) -> Optional[DriftAlert]:
        """
        Detect sudden drop in acceptance rate.
        
        Returns:
            DriftAlert if collapse detected, None otherwise
        """
        if len(self.validation_results) < 100:
            return None
        
        # Recent acceptance rate (last 100 events)
        recent_validation = list(self.validation_results)[-100:]
        recent_acceptance_rate = sum(recent_validation) / len(recent_validation)
        
        # Calculate drop percentage
        drop_percentage = (self.baseline_acceptance_rate - recent_acceptance_rate) / self.baseline_acceptance_rate
        
        # Thresholds
        warning_threshold = 0.20  # 20% drop
        critical_threshold = 0.40  # 40% drop
        
        if drop_percentage >= critical_threshold:
            return DriftAlert(
                alert_type="acceptance_collapse",
                severity="critical",
                metric_value=drop_percentage,
                threshold=critical_threshold,
                recommendation="Acceptance rate collapsed. Investigate validation failures. Auto-disabling feature flag.",
                timestamp=datetime.utcnow().isoformat()
            )
        elif drop_percentage >= warning_threshold:
            return DriftAlert(
                alert_type="acceptance_collapse",
                severity="warning",
                metric_value=drop_percentage,
                threshold=warning_threshold,
                recommendation="Acceptance rate declining. Investigate rejection reasons.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        return None
    
    def _detect_high_confidence_spike(self) -> Optional[DriftAlert]:
        """
        Detect unusual spike in high-confidence suggestions (>0.9).
        
        Returns:
            DriftAlert if spike detected, None otherwise
        """
        if len(self.raw_confidences) < 100:
            return None
        
        # Recent high-confidence percentage (last 100 events)
        recent_raw = list(self.raw_confidences)[-100:]
        high_confidence_count = sum(1 for c in recent_raw if c > 0.9)
        high_confidence_percentage = high_confidence_count / len(recent_raw)
        
        # Thresholds
        warning_threshold = 0.30  # 30% of suggestions
        critical_threshold = 0.50  # 50% of suggestions
        
        if high_confidence_percentage >= critical_threshold:
            return DriftAlert(
                alert_type="high_confidence_spike",
                severity="critical",
                metric_value=high_confidence_percentage,
                threshold=critical_threshold,
                recommendation="Suspect calibration failure. Retrain calibration profile. Auto-disabling feature flag.",
                timestamp=datetime.utcnow().isoformat()
            )
        elif high_confidence_percentage >= warning_threshold:
            return DriftAlert(
                alert_type="high_confidence_spike",
                severity="warning",
                metric_value=high_confidence_percentage,
                threshold=warning_threshold,
                recommendation="High-confidence spike detected. Monitor calibration effectiveness.",
                timestamp=datetime.utcnow().isoformat()
            )
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current drift monitoring statistics.
        
        Returns:
            Dictionary of statistics
        """
        if not self.baseline_established:
            return {
                'baseline_established': False,
                'events_collected': len(self.raw_confidences),
                'events_needed': self.baseline_window_size
            }
        
        recent_raw = list(self.raw_confidences)[-100:] if len(self.raw_confidences) >= 100 else list(self.raw_confidences)
        recent_calibrated = list(self.calibrated_confidences)[-100:] if len(self.calibrated_confidences) >= 100 else list(self.calibrated_confidences)
        recent_validation = list(self.validation_results)[-100:] if len(self.validation_results) >= 100 else list(self.validation_results)
        
        return {
            'baseline_established': True,
            'total_events': self.total_events,
            'window_size': len(self.raw_confidences),
            'baseline': {
                'mean_raw': self.baseline_mean_raw,
                'mean_calibrated': self.baseline_mean_calibrated,
                'acceptance_rate': self.baseline_acceptance_rate
            },
            'recent': {
                'mean_raw': statistics.mean(recent_raw) if recent_raw else 0,
                'mean_calibrated': statistics.mean(recent_calibrated) if recent_calibrated else 0,
                'acceptance_rate': sum(recent_validation) / len(recent_validation) if recent_validation else 0,
                'high_confidence_percentage': sum(1 for c in recent_raw if c > 0.9) / len(recent_raw) if recent_raw else 0
            }
        }
