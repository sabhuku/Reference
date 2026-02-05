"""
Test Suite for Canonical Data Guard

Tests write protection for references table.
"""
import pytest
from src.ai_remediation.canonical_guard import (
    CanonicalDataGuard,
    require_canonical_authorization
)
from src.ai_remediation.protected_fields import FieldProtectionLevel
from ui.database import db, Reference


class TestCanonicalDataGuard:
    """Test canonical data guard functionality."""
    
    def test_authorized_caller_allowed(self, app, sample_reference):
        """Authorized caller should be allowed to write."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            authorized, reason = guard.authorize_write(
                caller='user_manual_edit',
                reference_id=sample_reference.id,
                field_name='publisher',
                old_value=None,
                new_value='Oxford University Press',
                user_id=1
            )
            
            assert authorized
            assert 'authorized' in reason.lower()
    
    def test_unauthorized_caller_blocked(self, app, sample_reference):
        """Unauthorized caller should be blocked."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            authorized, reason = guard.authorize_write(
                caller='malicious_script',  # Not in whitelist
                reference_id=sample_reference.id,
                field_name='publisher',
                old_value=None,
                new_value='Oxford',
                user_id=1
            )
            
            assert not authorized
            assert 'not authorized' in reason.lower()
    
    def test_immutable_field_blocked(self, app, sample_reference):
        """Immutable fields should be blocked."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            authorized, reason = guard.authorize_write(
                caller='user_manual_edit',
                reference_id=sample_reference.id,
                field_name='id',  # Immutable field
                old_value='123',
                new_value='456',
                user_id=1
            )
            
            assert not authorized
            assert 'immutable' in reason.lower()
    
    def test_no_change_rejected(self, app, sample_reference):
        """No change in value should be rejected (optimization)."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            authorized, reason = guard.authorize_write(
                caller='user_manual_edit',
                reference_id=sample_reference.id,
                field_name='publisher',
                old_value='Oxford',
                new_value='Oxford',  # Same value
                user_id=1
            )
            
            assert not authorized
            assert 'no change' in reason.lower()
    
    def test_apply_modification_success(self, app, sample_reference):
        """Should successfully apply modification."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            success, message = guard.apply_modification(
                caller='user_manual_edit',
                reference=sample_reference,
                field_name='publisher',
                new_value='Cambridge University Press',
                user_id=1
            )
            
            assert success
            assert sample_reference.publisher == 'Cambridge University Press'
    
    def test_apply_modification_blocked(self, app, sample_reference):
        """Should block unauthorized modification."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            old_id = sample_reference.id
            
            success, message = guard.apply_modification(
                caller='user_manual_edit',
                reference=sample_reference,
                field_name='id',  # Immutable
                new_value=999,
                user_id=1
            )
            
            assert not success
            assert sample_reference.id == old_id  # Unchanged
    
    def test_batch_apply_modifications(self, app, sample_reference):
        """Should apply multiple modifications."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            modifications = {
                'publisher': 'New Publisher',
                'location': 'London'
            }
            
            success, message, failed = guard.batch_apply_modifications(
                caller='user_manual_edit',
                reference=sample_reference,
                modifications=modifications,
                user_id=1
            )
            
            assert success
            assert len(failed) == 0
            assert sample_reference.publisher == 'New Publisher'
            assert sample_reference.location == 'London'
    
    def test_batch_apply_with_failures(self, app, sample_reference):
        """Should handle partial failures in batch."""
        with app.app_context():
            guard = CanonicalDataGuard()
            
            modifications = {
                'publisher': 'New Publisher',  # Valid
                'id': 999  # Invalid (immutable)
            }
            
            success, message, failed = guard.batch_apply_modifications(
                caller='user_manual_edit',
                reference=sample_reference,
                modifications=modifications,
                user_id=1
            )
            
            assert not success
            assert len(failed) == 1
            assert failed[0]['field'] == 'id'
    
    def test_is_caller_authorized(self):
        """Should check if caller is authorized."""
        assert CanonicalDataGuard.is_caller_authorized('user_manual_edit')
        assert CanonicalDataGuard.is_caller_authorized('tier_0_auto_fix')
        assert not CanonicalDataGuard.is_caller_authorized('unknown_caller')


class TestDecorator:
    """Test canonical authorization decorator."""
    
    def test_decorator_allows_authorized(self, app, sample_reference):
        """Decorator should allow authorized modifications."""
        with app.app_context():
            @require_canonical_authorization('user_manual_edit')
            def modify_field(reference, field_name, new_value, **kwargs):
                return f"Modified {field_name}"
            
            result = modify_field(
                sample_reference,
                'publisher',
                'New Publisher',
                user_id=1
            )
            
            assert result == "Modified publisher"
    
    def test_decorator_blocks_unauthorized(self, app, sample_reference):
        """Decorator should block unauthorized modifications."""
        with app.app_context():
            @require_canonical_authorization('user_manual_edit')
            def modify_field(reference, field_name, new_value, **kwargs):
                return f"Modified {field_name}"
            
            with pytest.raises(PermissionError) as exc_info:
                modify_field(
                    sample_reference,
                    'id',  # Immutable
                    999,
                    user_id=1
                )
            
            assert 'immutable' in str(exc_info.value).lower()





@pytest.fixture
def sample_reference(app):
    """Create sample reference for testing."""
    with app.app_context():
        ref = Reference(
            bibliography_id=1,  # Required field
            title='Test Article',
            authors='["Smith, John"]',
            year='2023',
            publisher='Oxford University Press',
            location='Oxford'
        )
        db.session.add(ref)
        db.session.commit()
        
        yield ref


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
