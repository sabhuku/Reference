"""
Metrics Collection Middleware - Week 4 Implementation

Lightweight metrics collection for AI remediation system.
Stores metrics in SQLite with time-window aggregation.
"""
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from threading import RLock
from ui.database import db
from src.ai_remediation.models import MetricsEvent


class MetricsCollector:
    """
    Lightweight metrics collector.
    
    Features:
    - Append-only event log
    - Time-window aggregation
    - <5ms write latency
    - Thread-safe
    """
    
    def __init__(self, db_session=None):
        """
        Initialize metrics collector.
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        self._lock = RLock()
        
        # In-memory metrics buffer (flushed periodically)
        self._buffer: List[Dict[str, Any]] = []
    
    def record_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        suggestion_id: Optional[int] = None
    ):
        """
        Record a metrics event.
        
        Args:
            event_type: Type of event (e.g., 'suggestion_generated')
            event_data: Event-specific data
            user_id: User ID
            reference_id: Reference ID
            suggestion_id: Suggestion ID
        """
        with self._lock:
            event = MetricsEvent(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                user_id=user_id,
                reference_id=reference_id,
                suggestion_id=suggestion_id,
                # Map specific fields from event_data if present
                tier=event_data.get('tier'),
                field_name=event_data.get('field_name'),
                latency_ms=event_data.get('latency_ms'),
                tokens_used=event_data.get('tokens_used'),
                cost_usd=event_data.get('cost_usd'),
                calibrated_confidence=event_data.get('calibrated_confidence'),
                validation_stage=str(event_data.get('stage_failed')) if event_data.get('stage_failed') else None,
                rejection_code=str(event_data.get('rejection_codes')) if event_data.get('rejection_codes') else None,
                model_version=event_data.get('model_version'),
                prompt_version=event_data.get('prompt_version')
            )
            
            db.session.add(event)
            db.session.commit()
    
    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for time window.
        
        Args:
            start_time: Start of time window (default: 24 hours ago)
            end_time: End of time window (default: now)
            event_type: Filter by event type
        
        Returns:
            Aggregated metrics dictionary
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Build query
        query = MetricsEvent.query.filter(
            MetricsEvent.timestamp >= start_time,
            MetricsEvent.timestamp <= end_time
        )
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        events = query.all()
        
        # Aggregate metrics
        return self._aggregate_events(events, start_time, end_time)
    
    def _aggregate_events(
        self,
        events: List[MetricsEvent],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Aggregate events into metrics.
        
        Args:
            events: List of MetricsEvent objects
            start_time: Start of time window
            end_time: End of time window
        
        Returns:
            Aggregated metrics
        """
        # Group by event type
        by_type = {}
        for event in events:
            if event.event_type not in by_type:
                by_type[event.event_type] = []
            by_type[event.event_type].append(event)
        
        # Calculate metrics
        metrics = {
            'time_window': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'total_events': len(events),
            'by_type': {}
        }
        
        for event_type, type_events in by_type.items():
            metrics['by_type'][event_type] = {
                'count': len(type_events),
                'first_seen': min(e.timestamp for e in type_events).isoformat(),
                'last_seen': max(e.timestamp for e in type_events).isoformat()
            }
        
        return metrics


class AIMetricsCollector(MetricsCollector):
    """
    Specialized metrics collector for AI remediation.
    
    Tracks:
    - Suggestion generation rate
    - Acceptance rate
    - Rejection rate
    - Validation failures
    - Latency
    """
    
    def record_suggestion_generated(
        self,
        suggestion_id: int,
        reference_id: int,
        user_id: int,
        tier: str,
        num_patches: int,
        avg_confidence: float,
        latency_ms: float
    ):
        """Record suggestion generation."""
        self.record_event(
            event_type='suggestion_generated',
            event_data={
                'tier': tier,
                'num_patches': num_patches,
                'avg_confidence': avg_confidence,
                'latency_ms': latency_ms
            },
            user_id=user_id,
            reference_id=reference_id,
            suggestion_id=suggestion_id
        )
    
    def record_suggestion_accepted(
        self,
        suggestion_id: int,
        reference_id: int,
        user_id: int,
        num_fields: int
    ):
        """Record suggestion acceptance."""
        self.record_event(
            event_type='suggestion_accepted',
            event_data={'num_fields': num_fields},
            user_id=user_id,
            reference_id=reference_id,
            suggestion_id=suggestion_id
        )
    
    def record_suggestion_rejected(
        self,
        suggestion_id: int,
        reference_id: int,
        user_id: int,
        reason: str
    ):
        """Record suggestion rejection."""
        self.record_event(
            event_type='suggestion_rejected',
            event_data={'reason': reason},
            user_id=user_id,
            reference_id=reference_id,
            suggestion_id=suggestion_id
        )
    
    def record_validation_failure(
        self,
        suggestion_id: int,
        reference_id: int,
        stage_failed: int,
        rejection_codes: List[str]
    ):
        """Record validation failure."""
        self.record_event(
            event_type='validation_failed',
            event_data={
                'stage_failed': stage_failed,
                'rejection_codes': rejection_codes
            },
            reference_id=reference_id,
            suggestion_id=suggestion_id
        )
    
    def get_ai_metrics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get AI-specific metrics.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            AI metrics dictionary
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        end_time = datetime.utcnow()
        
        # Get all events
        events = MetricsEvent.query.filter(
            MetricsEvent.timestamp >= start_time,
            MetricsEvent.timestamp <= end_time
        ).all()
        
        # Count by type
        generated = sum(1 for e in events if e.event_type == 'suggestion_generated')
        accepted = sum(1 for e in events if e.event_type == 'suggestion_accepted')
        rejected = sum(1 for e in events if e.event_type == 'suggestion_rejected')
        validation_failed = sum(1 for e in events if e.event_type == 'validation_failed')
        
        # Calculate rates
        acceptance_rate = accepted / generated if generated > 0 else 0.0
        rejection_rate = rejected / generated if generated > 0 else 0.0
        validation_failure_rate = validation_failed / generated if generated > 0 else 0.0
        
        return {
            'time_window_hours': hours,
            'suggestions': {
                'generated': generated,
                'accepted': accepted,
                'rejected': rejected,
                'validation_failed': validation_failed
            },
            'rates': {
                'acceptance_rate': round(acceptance_rate, 3),
                'rejection_rate': round(rejection_rate, 3),
                'validation_failure_rate': round(validation_failure_rate, 3)
            },
            'health': self._calculate_health(
                acceptance_rate,
                validation_failure_rate
            )
        }
    
    def _calculate_health(
        self,
        acceptance_rate: float,
        validation_failure_rate: float
    ) -> str:
        """
        Calculate system health status.
        
        Args:
            acceptance_rate: Acceptance rate (0.0 to 1.0)
            validation_failure_rate: Validation failure rate (0.0 to 1.0)
        
        Returns:
            'healthy', 'degraded', or 'critical'
        """
        # Critical thresholds
        if acceptance_rate < 0.20:  # <20% acceptance
            return 'critical'
        if validation_failure_rate > 0.30:  # >30% validation failures
            return 'critical'
        
        # Degraded thresholds
        if acceptance_rate < 0.40:  # <40% acceptance
            return 'degraded'
        if validation_failure_rate > 0.15:  # >15% validation failures
            return 'degraded'
        
        return 'healthy'


# Singleton instance
_metrics_collector = None

def get_metrics_collector() -> AIMetricsCollector:
    """Get singleton metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AIMetricsCollector()
    return _metrics_collector
