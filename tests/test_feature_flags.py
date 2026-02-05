"""
Test Suite for Feature Flag Service

Tests deterministic cohort assignment, per-user overrides, and caching.
"""
import pytest
from src.ai_remediation.feature_flags import FeatureFlagService
from src.ai_remediation.models import FeatureFlag, UserFeatureFlag, RolloutCohort
from ui.database import db


class TestFeatureFlagService:
    """Test feature flag service."""
    
    def test_flag_not_exists_returns_default(self, app):
        """Non-existent flag should return default value."""
        with app.app_context():
            service = FeatureFlagService()
            
            assert service.is_enabled('nonexistent_flag', default=False) is False
            assert service.is_enabled('nonexistent_flag', default=True) is True
    
    def test_disabled_flag_returns_false(self, app):
        """Disabled flag should return False."""
        with app.app_context():
            # Create disabled flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=False,
                rollout_percentage=1.0
            )
            db.session.add(flag)
            db.session.commit()
            
            service = FeatureFlagService()
            assert service.is_enabled('test_flag') is False
    
    def test_enabled_flag_100_percent_returns_true(self, app):
        """Enabled flag at 100% should return True."""
        with app.app_context():
            # Create enabled flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=True,
                rollout_percentage=1.0
            )
            db.session.add(flag)
            db.session.commit()
            
            service = FeatureFlagService()
            assert service.is_enabled('test_flag', user_id=1) is True
    
    def test_deterministic_cohort_assignment(self, app):
        """Cohort assignment should be deterministic."""
        with app.app_context():
            service = FeatureFlagService()
            
            # Get cohort percentage for user
            cohort1 = service._get_user_cohort_percentage(user_id=123)
            cohort2 = service._get_user_cohort_percentage(user_id=123)
            
            # Should be identical
            assert cohort1 == cohort2
            
            # Should be between 0 and 1
            assert 0.0 <= cohort1 <= 1.0
    
    def test_rollout_percentage_respected(self, app):
        """Rollout percentage should be respected."""
        with app.app_context():
            # Create flag at 50% rollout
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=True,
                rollout_percentage=0.5
            )
            db.session.add(flag)
            db.session.commit()
            
            service = FeatureFlagService()
            
            # Test 100 users
            enabled_count = 0
            for user_id in range(1, 101):
                if service.is_enabled('test_flag', user_id=user_id):
                    enabled_count += 1
            
            # Should be approximately 50% (allow ±20% variance)
            assert 30 <= enabled_count <= 70
    
    def test_user_override_enabled(self, app):
        """User override should enable flag."""
        with app.app_context():
            # Create disabled flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=False,
                rollout_percentage=0.0
            )
            db.session.add(flag)
            db.session.commit()
            
            # Add user override
            override = UserFeatureFlag(
                user_id=123,
                flag_name='test_flag',
                enabled=True,
                reason='beta_tester'
            )
            db.session.add(override)
            db.session.commit()
            
            service = FeatureFlagService()
            
            # Should be enabled for user 123
            assert service.is_enabled('test_flag', user_id=123) is True
            
            # Should be disabled for other users
            assert service.is_enabled('test_flag', user_id=456) is False
    
    def test_user_override_disabled(self, app):
        """User override should disable flag."""
        with app.app_context():
            # Create enabled flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=True,
                rollout_percentage=1.0
            )
            db.session.add(flag)
            db.session.commit()
            
            # Add user override to disable
            override = UserFeatureFlag(
                user_id=123,
                flag_name='test_flag',
                enabled=False,
                reason='opt_out'
            )
            db.session.add(override)
            db.session.commit()
            
            service = FeatureFlagService()
            
            # Should be disabled for user 123
            assert service.is_enabled('test_flag', user_id=123) is False
            
            # Should be enabled for other users
            assert service.is_enabled('test_flag', user_id=456) is True
    
    def test_enable_flag(self, app):
        """Should enable flag."""
        with app.app_context():
            service = FeatureFlagService()
            
            service.enable_flag('new_flag', rollout_percentage=0.25)
            
            flag = FeatureFlag.query.filter_by(flag_name='new_flag').first()
            assert flag is not None
            assert flag.enabled is True
            assert flag.rollout_percentage == 0.25
    
    def test_disable_flag(self, app):
        """Should disable flag (kill-switch)."""
        with app.app_context():
            # Create enabled flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=True,
                rollout_percentage=1.0
            )
            db.session.add(flag)
            db.session.commit()
            
            service = FeatureFlagService()
            service.disable_flag('test_flag', reason='emergency')
            
            # Reload flag
            flag = FeatureFlag.query.filter_by(flag_name='test_flag').first()
            assert flag.enabled is False
    
    def test_set_user_override(self, app):
        """Should set per-user override."""
        with app.app_context():
            service = FeatureFlagService()
            
            service.set_user_override(
                user_id=123,
                flag_name='test_flag',
                enabled=True,
                reason='beta_tester'
            )
            
            override = UserFeatureFlag.query.filter_by(
                user_id=123,
                flag_name='test_flag'
            ).first()
            
            assert override is not None
            assert override.enabled is True
            assert override.reason == 'beta_tester'
    
    def test_cache_refresh(self, app):
        """Cache should refresh after TTL."""
        with app.app_context():
            service = FeatureFlagService(cache_ttl_seconds=0)  # Immediate expiry
            
            # Create flag
            flag = FeatureFlag(
                flag_name='test_flag',
                enabled=True,
                rollout_percentage=1.0
            )
            db.session.add(flag)
            db.session.commit()
            
            # Check flag (populates cache)
            assert service.is_enabled('test_flag') is True
            
            # Modify flag directly in DB
            flag.enabled = False
            db.session.commit()
            
            # Check again (should see updated value due to cache expiry)
            assert service.is_enabled('test_flag') is False





if __name__ == '__main__':
    pytest.main([__file__, '-v'])
