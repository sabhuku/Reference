"""
Test Suite for Metrics Collection

Tests metrics recording, aggregation, and health status calculation.
"""
import pytest
from datetime import datetime, timedelta
from src.ai_remediation.metrics import AIMetricsCollector
from src.ai_remediation.models import MetricsEvent
from ui.database import db


class TestMetricsCollector:
    """Test metrics collection."""
    
    def test_record_event(self, app):
        """Should record metrics event."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            collector.record_event(
                event_type='test_event',
                event_data={'key': 'value'},
                user_id=1,
                reference_id=123
            )
            
            event = MetricsEvent.query.first()
            assert event is not None
            assert event.event_type == 'test_event'
            assert event.user_id == 1
            assert event.reference_id == 123
    
    def test_record_suggestion_generated(self, app):
        """Should record suggestion generation."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            collector.record_suggestion_generated(
                suggestion_id=1,
                reference_id=123,
                user_id=5,
                tier='tier_1',
                num_patches=2,
                avg_confidence=0.95,
                latency_ms=150.0
            )
            
            event = MetricsEvent.query.first()
            assert event.event_type == 'suggestion_generated'
    
    def test_get_ai_metrics_empty(self, app):
        """Should handle empty metrics."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            metrics = collector.get_ai_metrics(hours=24)
            
            assert metrics['suggestions']['generated'] == 0
            assert metrics['suggestions']['accepted'] == 0
            assert metrics['rates']['acceptance_rate'] == 0.0
    
    def test_get_ai_metrics_with_data(self, app):
        """Should calculate metrics correctly."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            # Record events
            for i in range(10):
                collector.record_suggestion_generated(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    tier='tier_1',
                    num_patches=1,
                    avg_confidence=0.95,
                    latency_ms=100.0
                )
            
            # Accept 7 out of 10
            for i in range(7):
                collector.record_suggestion_accepted(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    num_fields=1
                )
            
            # Reject 3 out of 10
            for i in range(7, 10):
                collector.record_suggestion_rejected(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    reason='user_rejected'
                )
            
            metrics = collector.get_ai_metrics(hours=24)
            
            assert metrics['suggestions']['generated'] == 10
            assert metrics['suggestions']['accepted'] == 7
            assert metrics['suggestions']['rejected'] == 3
            assert metrics['rates']['acceptance_rate'] == 0.7
            assert metrics['rates']['rejection_rate'] == 0.3
    
    def test_health_status_healthy(self, app):
        """Should report healthy status."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            # Record good metrics (70% acceptance, 5% validation failures)
            for i in range(100):
                collector.record_suggestion_generated(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    tier='tier_1',
                    num_patches=1,
                    avg_confidence=0.95,
                    latency_ms=100.0
                )
            
            for i in range(70):
                collector.record_suggestion_accepted(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    num_fields=1
                )
            
            for i in range(5):
                collector.record_validation_failure(
                    suggestion_id=i,
                    reference_id=i,
                    stage_failed=3,
                    rejection_codes=['immutable_field']
                )
            
            metrics = collector.get_ai_metrics(hours=24)
            
            assert metrics['health'] == 'healthy'
    
    def test_health_status_degraded(self, app):
        """Should report degraded status."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            # Record degraded metrics (35% acceptance)
            for i in range(100):
                collector.record_suggestion_generated(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    tier='tier_1',
                    num_patches=1,
                    avg_confidence=0.95,
                    latency_ms=100.0
                )
            
            for i in range(35):
                collector.record_suggestion_accepted(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    num_fields=1
                )
            
            metrics = collector.get_ai_metrics(hours=24)
            
            assert metrics['health'] == 'degraded'
    
    def test_health_status_critical(self, app):
        """Should report critical status."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            # Record critical metrics (15% acceptance)
            for i in range(100):
                collector.record_suggestion_generated(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    tier='tier_1',
                    num_patches=1,
                    avg_confidence=0.95,
                    latency_ms=100.0
                )
            
            for i in range(15):
                collector.record_suggestion_accepted(
                    suggestion_id=i,
                    reference_id=i,
                    user_id=1,
                    num_fields=1
                )
            
            metrics = collector.get_ai_metrics(hours=24)
            
            assert metrics['health'] == 'critical'
    
    def test_time_window_filtering(self, app):
        """Should filter events by time window."""
        with app.app_context():
            collector = AIMetricsCollector()
            
            # Record old event (2 days ago)
            old_event = MetricsEvent(
                timestamp=datetime.utcnow() - timedelta(days=2),
                event_type='suggestion_generated',
                event_data='{}'
            )
            db.session.add(old_event)
            
            # Record recent event (1 hour ago)
            recent_event = MetricsEvent(
                timestamp=datetime.utcnow() - timedelta(hours=1),
                event_type='suggestion_generated',
                event_data='{}'
            )
            db.session.add(recent_event)
            
            db.session.commit()
            
            # Get metrics for last 24 hours
            metrics = collector.get_ai_metrics(hours=24)
            
            # Should only count recent event
            assert metrics['suggestions']['generated'] == 1





if __name__ == '__main__':
    pytest.main([__file__, '-v'])
