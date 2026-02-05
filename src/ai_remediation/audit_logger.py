"""
Audit Logger - Week 3 Implementation

Cryptographic hash chain for tamper-evident audit logging.
Every AI remediation action is logged with SHA-256 hash chain.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import hashlib
import json
from flask import request
from ui.database import db
from src.ai_remediation.models import AuditLog


class AuditLogger:
    """
    Tamper-evident audit logger with cryptographic hash chain.
    
    Each event is hashed with SHA-256, including the previous event's hash.
    This creates an immutable chain where any tampering is detectable.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize audit logger.
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        self._lock = None  # Thread safety handled by SQLAlchemy
    
    @staticmethod
    def _compute_hash(
        timestamp: datetime,
        event_type: str,
        details: str,
        previous_hash: Optional[str]
    ) -> str:
        """
        Compute SHA-256 hash for event.
        
        Args:
            timestamp: Event timestamp
            event_type: Type of event
            details: JSON-encoded event details
            previous_hash: Hash of previous event (None for first event)
        
        Returns:
            64-character hex hash
        """
        data = f"{timestamp.isoformat()}|{event_type}|{details}|{previous_hash or ''}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        suggestion_id: Optional[int] = None
    ) -> AuditLog:
        """
        Log an event to the audit trail.
        
        Args:
            event_type: Type of event (e.g., 'suggestion_generated', 'suggestion_accepted')
            details: Event-specific data (will be JSON-encoded)
            user_id: User who triggered the event
            reference_id: Reference being modified
            suggestion_id: AI suggestion ID
        
        Returns:
            Created AuditLog entry
        """
        # Get previous event's hash
        previous_event = AuditLog.query.order_by(AuditLog.id.desc()).first()
        previous_hash = previous_event.event_hash if previous_event else None
        
        # Create timestamp
        timestamp = datetime.utcnow()
        
        # Encode details as JSON
        details_json = json.dumps(details, sort_keys=True)
        
        # Compute hash
        event_hash = self._compute_hash(timestamp, event_type, details_json, previous_hash)
        
        # Get request context (if available)
        ip_address = None
        user_agent = None
        try:
            if request:
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent', '')[:200]
        except RuntimeError:
            # No request context (e.g., background job)
            pass
        
        # Create audit log entry
        log_entry = AuditLog(
            timestamp=timestamp,
            event_type=event_type,
            user_id=user_id,
            reference_id=reference_id,
            suggestion_id=suggestion_id,
            details=details_json,
            event_hash=event_hash,
            previous_hash=previous_hash,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    
    def verify_chain(self, limit: int = 1000) -> Tuple[bool, str]:
        """
        Verify integrity of audit log hash chain.
        
        Args:
            limit: Maximum number of events to verify
        
        Returns:
            (is_valid, message)
        """
        events = AuditLog.query.order_by(AuditLog.id).limit(limit).all()
        
        if not events:
            return True, "No events to verify"
        
        for i, event in enumerate(events):
            # Recompute hash
            expected_hash = self._compute_hash(
                event.timestamp,
                event.event_type,
                event.details,
                event.previous_hash
            )
            
            # Check hash matches
            if event.event_hash != expected_hash:
                return False, f"Hash mismatch at event {event.id} (expected {expected_hash}, got {event.event_hash})"
            
            # Check chain continuity
            if i > 0:
                if event.previous_hash != events[i-1].event_hash:
                    return False, f"Chain broken at event {event.id} (previous_hash doesn't match)"
        
        return True, f"Chain verified ({len(events)} events)"
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        suggestion_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Retrieve audit log events.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user
            reference_id: Filter by reference
            suggestion_id: Filter by suggestion
            limit: Maximum number of events
        
        Returns:
            List of AuditLog entries
        """
        query = AuditLog.query
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if reference_id:
            query = query.filter_by(reference_id=reference_id)
        if suggestion_id:
            query = query.filter_by(suggestion_id=suggestion_id)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()


# Event type constants
class AuditEventType:
    """Standard audit event types."""
    
    # Suggestion lifecycle
    SUGGESTION_GENERATED = "suggestion_generated"
    SUGGESTION_VALIDATED = "suggestion_validated"
    SUGGESTION_REJECTED = "suggestion_rejected"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_APPLIED = "suggestion_applied"
    
    # Validation
    VALIDATION_FAILED = "validation_failed"
    VALIDATION_PASSED = "validation_passed"
    
    # Field modifications
    FIELD_MODIFIED = "field_modified"
    FIELD_ENRICHED = "field_enriched"
    
    # Feature flags
    FEATURE_FLAG_ENABLED = "feature_flag_enabled"
    FEATURE_FLAG_DISABLED = "feature_flag_disabled"
    ROLLBACK_TRIGGERED = "rollback_triggered"
    
    # Security
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    IMMUTABLE_FIELD_VIOLATION = "immutable_field_violation"


# Convenience functions
def log_suggestion_generated(
    suggestion_id: int,
    reference_id: int,
    user_id: int,
    tier: str,
    patches: List[dict],
    confidence_scores: Dict[str, float]
):
    """Log AI suggestion generation."""
    logger = AuditLogger()
    return logger.log_event(
        event_type=AuditEventType.SUGGESTION_GENERATED,
        details={
            'tier': tier,
            'num_patches': len(patches),
            'fields_modified': [p['path'][1:] for p in patches],
            'avg_confidence': sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
        },
        user_id=user_id,
        reference_id=reference_id,
        suggestion_id=suggestion_id
    )


def log_validation_result(
    suggestion_id: int,
    reference_id: int,
    passed: bool,
    stage_passed: int,
    rejections: List[dict]
):
    """Log validation result."""
    logger = AuditLogger()
    event_type = AuditEventType.VALIDATION_PASSED if passed else AuditEventType.VALIDATION_FAILED
    
    return logger.log_event(
        event_type=event_type,
        details={
            'passed': passed,
            'stage_passed': stage_passed,
            'num_rejections': len(rejections),
            'rejection_codes': [r['code'] for r in rejections]
        },
        reference_id=reference_id,
        suggestion_id=suggestion_id
    )


def log_suggestion_accepted(
    suggestion_id: int,
    reference_id: int,
    user_id: int,
    fields_modified: List[str]
):
    """Log user acceptance of suggestion."""
    logger = AuditLogger()
    return logger.log_event(
        event_type=AuditEventType.SUGGESTION_ACCEPTED,
        details={
            'fields_modified': fields_modified,
            'num_fields': len(fields_modified)
        },
        user_id=user_id,
        reference_id=reference_id,
        suggestion_id=suggestion_id
    )


def log_field_modified(
    reference_id: int,
    field_name: str,
    old_value: Any,
    new_value: Any,
    source: str,
    user_id: Optional[int] = None
):
    """Log field modification."""
    logger = AuditLogger()
    return logger.log_event(
        event_type=AuditEventType.FIELD_MODIFIED,
        details={
            'field': field_name,
            'old_value': str(old_value)[:200] if old_value else None,
            'new_value': str(new_value)[:200] if new_value else None,
            'source': source  # 'user', 'tier_0', 'tier_1', 'ai_suggestion'
        },
        user_id=user_id,
        reference_id=reference_id
    )


def log_unauthorized_access(
    event_type: str,
    details: Dict[str, Any],
    user_id: Optional[int] = None
):
    """Log unauthorized access attempt."""
    logger = AuditLogger()
    return logger.log_event(
        event_type=AuditEventType.UNAUTHORIZED_ACCESS,
        details=details,
        user_id=user_id
    )
