"""
Feature Flag Service - Week 4 Implementation

Thread-safe feature flag service with deterministic cohort assignment.
Supports per-user overrides and percentage-based rollout.
"""
from typing import Optional, Dict
from threading import RLock
from datetime import datetime
import hashlib
from ui.database import db
from src.ai_remediation.models import (
    FeatureFlag,
    UserFeatureFlag,
    RolloutCohort,
    RolloutHistory
)


class FeatureFlagService:
    """
    Thread-safe feature flag service.
    
    Features:
    - Per-user feature flags
    - Percentage-based rollout
    - Deterministic cohort assignment
    - <1ms flag check latency
    - 60-second cache
    """
    
    def __init__(self, cache_ttl_seconds: int = 60):
        """
        Initialize feature flag service.
        
        Args:
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self._lock = RLock()
        self._cache: Dict[str, Dict] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = cache_ttl_seconds
    
    def _refresh_cache(self):
        """Refresh feature flag cache."""
        with self._lock:
            # Check if cache is still valid
            if self._cache_timestamp:
                elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if elapsed < self._cache_ttl_seconds:
                    return  # Cache still valid
            
            # Refresh cache
            flags = FeatureFlag.query.all()
            self._cache = {
                flag.flag_name: {
                    'enabled': flag.enabled,
                    'rollout_percentage': flag.rollout_percentage,
                    'rollout_strategy': flag.rollout_strategy
                }
                for flag in flags
            }
            self._cache_timestamp = datetime.utcnow()
    
    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[int] = None,
        default: bool = False
    ) -> bool:
        """
        Check if feature flag is enabled for user.
        
        Args:
            flag_name: Name of feature flag
            user_id: User ID (None for global check)
            default: Default value if flag doesn't exist
        
        Returns:
            True if enabled, False otherwise
        """
        with self._lock:
            # Refresh cache if needed
            self._refresh_cache()
            
            # Check if flag exists
            if flag_name not in self._cache:
                return default
            
            flag_config = self._cache[flag_name]
            
            # Check global enabled status
            if not flag_config['enabled']:
                return False
            
            # If no user_id, return global status
            if user_id is None:
                return True
            
            # Check per-user override
            user_override = UserFeatureFlag.query.filter_by(
                user_id=user_id,
                flag_name=flag_name
            ).first()
            
            if user_override:
                return user_override.enabled
            
            # Check rollout percentage
            rollout_percentage = flag_config['rollout_percentage']
            
            if rollout_percentage >= 1.0:
                return True  # 100% rollout
            elif rollout_percentage <= 0.0:
                return False  # 0% rollout
            
            # Deterministic cohort assignment
            user_cohort_percentage = self._get_user_cohort_percentage(user_id)
            
            return user_cohort_percentage <= rollout_percentage
    
    def _get_user_cohort_percentage(self, user_id: int) -> float:
        """
        Get user's cohort percentage (deterministic).
        
        Args:
            user_id: User ID
        
        Returns:
            Float between 0.0 and 1.0
        """
        # Check if cohort already assigned
        cohort = RolloutCohort.query.filter_by(user_id=user_id).first()
        
        if cohort:
            return cohort.cohort_percentage
        
        # Assign new cohort (deterministic hash)
        hash_value = hashlib.sha256(str(user_id).encode()).hexdigest()
        cohort_percentage = int(hash_value[:8], 16) / 0xFFFFFFFF
        
        # Store cohort assignment
        new_cohort = RolloutCohort(
            user_id=user_id,
            cohort_hash=hash_value[:8],
            cohort_percentage=cohort_percentage
        )
        db.session.add(new_cohort)
        db.session.commit()
        
        return cohort_percentage
    
    def auto_disable_on_drift(
        self,
        flag_name: str,
        reason: str
    ) -> bool:
        """
        Auto-disable feature flag due to drift detection.
        
        Args:
            flag_name: Name of feature flag to disable
            reason: Reason for auto-disable (drift alert details)
        
        Returns:
            True if disabled successfully, False otherwise
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            with self._lock:
                # Find flag
                flag = FeatureFlag.query.filter_by(flag_name=flag_name).first()
                
                if not flag:
                    logger.error(f"Feature flag not found: {flag_name}")
                    return False
                
                # Disable flag
                previous_percentage = flag.rollout_percentage
                flag.enabled = False
                flag.rollout_percentage = 0.0
                flag.updated_at = datetime.utcnow()
                
                # Log to rollout history
                history = RolloutHistory(
                    flag_name=flag_name,
                    event_type='auto_disabled_drift',
                    old_value=str({'enabled': True, 'rollout_percentage': previous_percentage}),
                    new_value=str({'enabled': False, 'rollout_percentage': 0.0}),
                    reason=reason,
                    triggered_by='drift_monitor'
                )
                db.session.add(history)
                db.session.commit()
                
                # Invalidate cache
                self._cache_timestamp = None
                
                logger.critical(
                    f"AUTO-DISABLED feature flag '{flag_name}' due to drift: {reason}"
                )
                
                return True
        
        except Exception as e:
            logger.error(f"Failed to auto-disable feature flag: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    def enable_flag(
        self,
        flag_name: str,
        rollout_percentage: float = 1.0,
        reason: str = "manual_enable"
    ):
        """
        Enable a feature flag.
        
        Args:
            flag_name: Name of feature flag
            rollout_percentage: Percentage of users (0.0 to 1.0)
            reason: Reason for enabling
        """
        with self._lock:
            flag = FeatureFlag.query.filter_by(flag_name=flag_name).first()
            
            if not flag:
                # Create new flag
                flag = FeatureFlag(
                    flag_name=flag_name,
                    enabled=True,
                    rollout_percentage=rollout_percentage
                )
                db.session.add(flag)
            else:
                # Update existing flag
                old_value = {
                    'enabled': flag.enabled,
                    'rollout_percentage': flag.rollout_percentage
                }
                
                flag.enabled = True
                flag.rollout_percentage = rollout_percentage
                flag.updated_at = datetime.utcnow()
                
                # Log change
                history = RolloutHistory(
                    flag_name=flag_name,
                    event_type='enabled',
                    old_value=str(old_value),
                    new_value=str({
                        'enabled': True,
                        'rollout_percentage': rollout_percentage
                    }),
                    reason=reason,
                    triggered_by='manual'
                )
                db.session.add(history)
            
            db.session.commit()
            
            # Invalidate cache
            self._cache_timestamp = None
    
    def disable_flag(
        self,
        flag_name: str,
        reason: str = "manual_disable"
    ):
        """
        Disable a feature flag (kill-switch).
        
        Args:
            flag_name: Name of feature flag
            reason: Reason for disabling
        """
        with self._lock:
            flag = FeatureFlag.query.filter_by(flag_name=flag_name).first()
            
            if not flag:
                return  # Flag doesn't exist
            
            old_value = {
                'enabled': flag.enabled,
                'rollout_percentage': flag.rollout_percentage
            }
            
            flag.enabled = False
            flag.updated_at = datetime.utcnow()
            
            # Log change
            history = RolloutHistory(
                flag_name=flag_name,
                event_type='disabled',
                old_value=str(old_value),
                new_value=str({'enabled': False}),
                reason=reason,
                triggered_by='manual'
            )
            db.session.add(history)
            
            db.session.commit()
            
            # Invalidate cache
            self._cache_timestamp = None
    
    def set_user_override(
        self,
        user_id: int,
        flag_name: str,
        enabled: bool,
        reason: str = "beta_tester"
    ):
        """
        Set per-user feature flag override.
        
        Args:
            user_id: User ID
            flag_name: Name of feature flag
            enabled: Enable or disable for this user
            reason: Reason for override
        """
        with self._lock:
            override = UserFeatureFlag.query.filter_by(
                user_id=user_id,
                flag_name=flag_name
            ).first()
            
            if override:
                override.enabled = enabled
                override.reason = reason
            else:
                override = UserFeatureFlag(
                    user_id=user_id,
                    flag_name=flag_name,
                    enabled=enabled,
                    reason=reason
                )
                db.session.add(override)
            
            db.session.commit()
    
    def get_flag_status(self, flag_name: str) -> Optional[Dict]:
        """
        Get current status of a feature flag.
        
        Args:
            flag_name: Name of feature flag
        
        Returns:
            Dict with flag status or None
        """
        flag = FeatureFlag.query.filter_by(flag_name=flag_name).first()
        
        if not flag:
            return None
        
        # Count user overrides
        overrides = UserFeatureFlag.query.filter_by(flag_name=flag_name).all()
        enabled_overrides = sum(1 for o in overrides if o.enabled)
        disabled_overrides = sum(1 for o in overrides if not o.enabled)
        
        return {
            'flag_name': flag_name,
            'enabled': flag.enabled,
            'rollout_percentage': flag.rollout_percentage,
            'rollout_strategy': flag.rollout_strategy,
            'user_overrides': {
                'enabled': enabled_overrides,
                'disabled': disabled_overrides
            },
            'updated_at': flag.updated_at.isoformat() if flag.updated_at else None
        }


# Decorator for feature flag protection
def require_feature_flag(flag_name: str, default: bool = False):
    """
    Decorator to protect routes with feature flags.
    
    Usage:
        @app.route('/api/suggestions/generate')
        @require_feature_flag('ai_suggestions')
        def generate_suggestions():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import g, abort
            
            # Get user_id from Flask context
            user_id = getattr(g, 'user_id', None)
            
            # Check feature flag
            service = FeatureFlagService()
            if not service.is_enabled(flag_name, user_id, default):
                abort(403, description=f"Feature '{flag_name}' is not enabled")
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    
    return decorator
