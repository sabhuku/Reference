"""
Test Suite for Audit Logger

Tests cryptographic hash chain and event logging.
"""
import pytest
from datetime import datetime
from src.ai_remediation.audit_logger import (
    AuditLogger,
    AuditEventType,
    log_suggestion_generated,
    log_validation_result,
    log_field_modified
)
from src.ai_remediation.models import AuditLog
from ui.database import db


class TestAuditLogger:
    """Test audit logging functionality."""
    
    def test_log_event_creates_entry(self, app):
        """Logging an event should create audit log entry."""
        with app.app_context():
            logger = AuditLogger()
            
            log_entry = logger.log_event(
                event_type=AuditEventType.SUGGESTION_GENERATED,
                details={'test': 'data'},
                user_id=1,
                reference_id=123
            )
            
            assert log_entry.id is not None
            assert log_entry.event_type == AuditEventType.SUGGESTION_GENERATED
            assert log_entry.user_id == 1
            assert log_entry.reference_id == 123
            assert log_entry.event_hash is not None
            assert len(log_entry.event_hash) == 64  # SHA-256 hex
    
    def test_hash_chain_first_event(self, app):
        """First event should have None as previous_hash."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            log_entry = logger.log_event(
                event_type='test_event',
                details={'first': True}
            )
            
            assert log_entry.previous_hash is None
    
    def test_hash_chain_second_event(self, app):
        """Second event should reference first event's hash."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            
            # First event
            first_entry = logger.log_event(
                event_type='first_event',
                details={'order': 1}
            )
            
            # Second event
            second_entry = logger.log_event(
                event_type='second_event',
                details={'order': 2}
            )
            
            assert second_entry.previous_hash == first_entry.event_hash
    
    def test_verify_chain_valid(self, app):
        """Valid chain should pass verification."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            
            # Create chain of events
            for i in range(5):
                logger.log_event(
                    event_type=f'event_{i}',
                    details={'index': i}
                )
            
            # Verify chain
            is_valid, message = logger.verify_chain()
            
            assert is_valid
            assert '5 events' in message
    
    def test_verify_chain_detects_tampering(self, app):
        """Tampered chain should fail verification."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            
            # Create chain
            for i in range(3):
                logger.log_event(
                    event_type=f'event_{i}',
                    details={'index': i}
                )
            
            # Tamper with middle event
            events = AuditLog.query.order_by(AuditLog.id).all()
            events[1].details = '{"tampered": true}'
            db.session.commit()
            
            # Verify chain (should fail)
            is_valid, message = logger.verify_chain()
            
            assert not is_valid
            assert 'mismatch' in message.lower()
    
    def test_get_events_by_type(self, app):
        """Should filter events by type."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            
            # Create different event types
            logger.log_event(event_type='type_a', details={})
            logger.log_event(event_type='type_b', details={})
            logger.log_event(event_type='type_a', details={})
            
            # Get type_a events
            events = logger.get_events(event_type='type_a')
            
            assert len(events) == 2
            assert all(e.event_type == 'type_a' for e in events)
    
    def test_get_events_by_reference(self, app):
        """Should filter events by reference_id."""
        with app.app_context():
            # Clear audit log
            AuditLog.query.delete()
            db.session.commit()
            
            logger = AuditLogger()
            
            # Create events for different references
            logger.log_event(event_type='test', details={}, reference_id=1)
            logger.log_event(event_type='test', details={}, reference_id=2)
            logger.log_event(event_type='test', details={}, reference_id=1)
            
            # Get events for reference 1
            events = logger.get_events(reference_id=1)
            
            assert len(events) == 2
            assert all(e.reference_id == 1 for e in events)


class TestConvenienceFunctions:
    """Test convenience logging functions."""
    
    def test_log_suggestion_generated(self, app):
        """Should log suggestion generation."""
        with app.app_context():
            log_entry = log_suggestion_generated(
                suggestion_id=1,
                reference_id=123,
                user_id=5,
                tier='tier_1',
                patches=[{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}],
                confidence_scores={'publisher': 0.95}
            )
            
            assert log_entry.event_type == AuditEventType.SUGGESTION_GENERATED
            assert log_entry.suggestion_id == 1
            assert log_entry.reference_id == 123
            assert log_entry.user_id == 5
    
    def test_log_validation_result_passed(self, app):
        """Should log validation pass."""
        with app.app_context():
            log_entry = log_validation_result(
                suggestion_id=1,
                reference_id=123,
                passed=True,
                stage_passed=7,
                rejections=[]
            )
            
            assert log_entry.event_type == AuditEventType.VALIDATION_PASSED
    
    def test_log_validation_result_failed(self, app):
        """Should log validation failure."""
        with app.app_context():
            log_entry = log_validation_result(
                suggestion_id=1,
                reference_id=123,
                passed=False,
                stage_passed=3,
                rejections=[{'code': 'immutable_field'}]
            )
            
            assert log_entry.event_type == AuditEventType.VALIDATION_FAILED
    
    def test_log_field_modified(self, app):
        """Should log field modification."""
        with app.app_context():
            log_entry = log_field_modified(
                reference_id=123,
                field_name='publisher',
                old_value='Old Publisher',
                new_value='New Publisher',
                source='tier_0',
                user_id=5
            )
            
            assert log_entry.event_type == AuditEventType.FIELD_MODIFIED
            assert log_entry.reference_id == 123





if __name__ == '__main__':
    pytest.main([__file__, '-v'])
