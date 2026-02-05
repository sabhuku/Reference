"""
Database models for AI Remediation System.

Extends existing database with AI-specific tables:
- ai_suggestions: Stores AI-generated suggestions (separate from canonical references)
- applied_suggestions: Audit trail of applied suggestions
- field_provenance: Tracks modification sources for each field
- audit_log: Cryptographic hash chain for tamper detection
- feature_flags: Global feature flags for rollout control
- user_feature_flags: Per-user feature flag overrides
- rollout_cohorts: Deterministic user cohort assignments
"""
from datetime import datetime
from ui.database import db
import json
import hashlib


class AISuggestion(db.Model):
    """
    AI-generated remediation suggestions (NEVER auto-applied).
    
    Stored separately from canonical references table.
    """
    __tablename__ = 'ai_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_id = db.Column(db.Integer, db.ForeignKey('references.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Suggestion metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime)  # Suggestions expire after 7 days
    
    # AI response
    patches = db.Column(db.Text, nullable=False)  # JSON patch operations (RFC 6902)
    rationale = db.Column(db.Text)  # AI explanation
    confidence_scores = db.Column(db.Text)  # JSON: {field: confidence}
    calibrated_confidences = db.Column(db.Text)  # JSON: {field: calibrated_confidence}
    
    # Tier assignment
    tier = db.Column(db.String(20), nullable=False)  # 'tier_0', 'tier_1', 'tier_2', 'tier_3'
    
    # Validation
    validation_passed = db.Column(db.Boolean, nullable=False)
    validation_errors = db.Column(db.Text)  # JSON: [{"stage": "...", "code": "...", "message": "..."}]
    
    # External verification
    has_doi_verification = db.Column(db.Boolean, default=False)
    has_isbn_verification = db.Column(db.Boolean, default=False)
    external_metadata = db.Column(db.Text)  # JSON: external API data
    
    # User action
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected', 'expired'
    reviewed_at = db.Column(db.DateTime)
    
    # AI model metadata
    model_version = db.Column(db.String(50))  # 'gpt-5-turbo-2024-01'
    prompt_version = db.Column(db.String(50))  # 'v1.2.3'
    tokens_used = db.Column(db.Integer)
    cost_usd = db.Column(db.Float)
    latency_ms = db.Column(db.Float)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'patches': json.loads(self.patches) if self.patches else [],
            'rationale': self.rationale,
            'confidence_scores': json.loads(self.confidence_scores) if self.confidence_scores else {},
            'calibrated_confidences': json.loads(self.calibrated_confidences) if self.calibrated_confidences else {},
            'tier': self.tier,
            'validation_passed': self.validation_passed,
            'status': self.status,
            'has_doi_verification': self.has_doi_verification,
            'has_isbn_verification': self.has_isbn_verification
        }


class AppliedSuggestion(db.Model):
    """
    Audit trail of applied suggestions.
    
    Records every suggestion that was accepted and applied to canonical references.
    """
    __tablename__ = 'applied_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('ai_suggestions.id'), nullable=False, index=True)
    reference_id = db.Column(db.Integer, db.ForeignKey('references.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Application metadata
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    applied_by = db.Column(db.String(50), nullable=False)  # 'user', 'tier_0_auto', 'tier_1_auto'
    
    # What was changed
    patches_applied = db.Column(db.Text, nullable=False)  # JSON patch operations
    fields_modified = db.Column(db.Text, nullable=False)  # JSON: ['publisher', 'location']
    
    # Snapshot before/after
    reference_before = db.Column(db.Text, nullable=False)  # JSON: full reference state
    reference_after = db.Column(db.Text, nullable=False)  # JSON: full reference state
    
    # Rollback capability
    can_rollback = db.Column(db.Boolean, default=True)
    rolled_back_at = db.Column(db.DateTime)


class FieldProvenance(db.Model):
    """
    Tracks the source of each field modification.
    
    Enables field-level audit trail (who/what modified each field).
    """
    __tablename__ = 'field_provenance'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_id = db.Column(db.Integer, db.ForeignKey('references.id'), nullable=False, index=True)
    field_name = db.Column(db.String(50), nullable=False, index=True)
    
    # Modification metadata
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    modified_by = db.Column(db.String(50), nullable=False)  # 'user', 'tier_0', 'tier_1', 'ai_suggestion'
    
    # Source tracking
    source_type = db.Column(db.String(50), nullable=False)  # 'manual', 'api_lookup', 'ai_inference', 'deterministic'
    source_id = db.Column(db.Integer)  # suggestion_id if from AI
    
    # Values
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    
    # Confidence
    confidence = db.Column(db.Float)  # Calibrated confidence if from AI


class AuditLog(db.Model):
    """
    Cryptographic audit log with hash chain.
    
    Tamper-evident log of all AI remediation actions.
    """
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Event details
    event_type = db.Column(db.String(50), nullable=False, index=True)  # 'suggestion_generated', 'suggestion_accepted', etc.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    reference_id = db.Column(db.Integer, db.ForeignKey('references.id'), index=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('ai_suggestions.id'), index=True)
    
    # Event payload
    details = db.Column(db.Text, nullable=False)  # JSON: event-specific data
    
    # Cryptographic hash chain
    event_hash = db.Column(db.String(64), nullable=False, unique=True)  # SHA-256 of this event
    previous_hash = db.Column(db.String(64))  # Hash of previous event (chain)
    
    # Metadata
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    
    @staticmethod
    def compute_hash(timestamp, event_type, details, previous_hash):
        """Compute SHA-256 hash for event."""
        data = f"{timestamp.isoformat()}|{event_type}|{details}|{previous_hash or ''}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def verify_chain(limit=1000):
        """Verify integrity of hash chain."""
        events = AuditLog.query.order_by(AuditLog.id).limit(limit).all()
        
        for i, event in enumerate(events):
            # Recompute hash
            expected_hash = AuditLog.compute_hash(
                event.timestamp,
                event.event_type,
                event.details,
                event.previous_hash
            )
            
            if event.event_hash != expected_hash:
                return False, f"Hash mismatch at event {event.id}"
            
            # Check chain
            if i > 0:
                if event.previous_hash != events[i-1].event_hash:
                    return False, f"Chain broken at event {event.id}"
        
        return True, "Chain verified"


class FeatureFlag(db.Model):
    """
    Global feature flags for rollout control.
    """
    __tablename__ = 'feature_flags'
    
    flag_name = db.Column(db.String(50), primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    
    # Rollout configuration
    rollout_percentage = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    rollout_strategy = db.Column(db.String(20), default='percentage')  # 'percentage', 'whitelist', 'blacklist'
    
    # Metadata
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(50))


class UserFeatureFlag(db.Model):
    """
    Per-user feature flag overrides.
    """
    __tablename__ = 'user_feature_flags'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    flag_name = db.Column(db.String(50), db.ForeignKey('feature_flags.flag_name'), primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False)
    
    # Reason for override
    reason = db.Column(db.String(100))  # 'beta_tester', 'early_access', 'excluded'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RolloutCohort(db.Model):
    """
    Deterministic user cohort assignments.
    """
    __tablename__ = 'rollout_cohorts'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    cohort_hash = db.Column(db.String(8), nullable=False)  # First 8 chars of SHA-256
    cohort_percentage = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def assign_cohort(user_id):
        """Deterministically assign user to cohort."""
        hash_value = hashlib.sha256(str(user_id).encode()).hexdigest()
        cohort_hash = hash_value[:8]
        cohort_percentage = int(hash_value[:8], 16) / 0xFFFFFFFF
        
        return RolloutCohort(
            user_id=user_id,
            cohort_hash=cohort_hash,
            cohort_percentage=cohort_percentage
        )


class RolloutHistory(db.Model):
    """
    Audit trail of feature flag changes.
    """
    __tablename__ = 'rollout_history'
    
    id = db.Column(db.Integer, primary_key=True)
    flag_name = db.Column(db.String(50), db.ForeignKey('feature_flags.flag_name'), nullable=False, index=True)
    
    event_type = db.Column(db.String(50), nullable=False)  # 'enabled', 'disabled', 'percentage_changed', 'rollback'
    
    old_value = db.Column(db.Text)  # JSON
    new_value = db.Column(db.Text)  # JSON
    
    reason = db.Column(db.Text)
    triggered_by = db.Column(db.String(50))  # 'manual', 'automatic_rollback', 'scheduled'
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class MetricsEvent(db.Model):
    """
    Raw metrics events (append-only log).
    """
    __tablename__ = 'metrics_events'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Event type
    event_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Context
    suggestion_id = db.Column(db.Integer, db.ForeignKey('ai_suggestions.id'), index=True)
    reference_id = db.Column(db.Integer, db.ForeignKey('references.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    
    # Metrics payload
    tier = db.Column(db.String(20))
    field_name = db.Column(db.String(50))
    latency_ms = db.Column(db.Float)
    tokens_used = db.Column(db.Integer)
    cost_usd = db.Column(db.Float)
    calibrated_confidence = db.Column(db.Float)
    validation_stage = db.Column(db.String(50))
    rejection_code = db.Column(db.String(50))
    
    # Metadata
    model_version = db.Column(db.String(50))
    prompt_version = db.Column(db.String(50))


# Initialize all tables
def init_ai_tables(app):
    """Initialize AI remediation tables."""
    with app.app_context():
        db.create_all()
        
        # Create default feature flag
        if not FeatureFlag.query.filter_by(flag_name='ai_suggestions').first():
            flag = FeatureFlag(
                flag_name='ai_suggestions',
                enabled=False,
                rollout_percentage=0.0,
                description='AI-powered remediation suggestions'
            )
            db.session.add(flag)
            db.session.commit()
            print("✓ Created 'ai_suggestions' feature flag (disabled)")
