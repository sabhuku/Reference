"""
Test suite for Protected Fields Policy

Tests all protection levels and authorization logic.
"""
import pytest
from src.ai_remediation.protected_fields import (
    ProtectedFieldsPolicy,
    FieldProtectionLevel,
    require_field_authorization
)


class TestProtectionLevels:
    """Test field classification."""
    
    def test_immutable_fields(self):
        """Immutable fields should never be modifiable."""
        assert ProtectedFieldsPolicy.get_protection_level('id') == FieldProtectionLevel.IMMUTABLE
        assert ProtectedFieldsPolicy.get_protection_level('added_at') == FieldProtectionLevel.IMMUTABLE
        assert ProtectedFieldsPolicy.get_protection_level('source') == FieldProtectionLevel.IMMUTABLE
    
    def test_critical_fields(self):
        """Critical fields require verification."""
        assert ProtectedFieldsPolicy.get_protection_level('author') == FieldProtectionLevel.CRITICAL
        assert ProtectedFieldsPolicy.get_protection_level('title') == FieldProtectionLevel.CRITICAL
        assert ProtectedFieldsPolicy.get_protection_level('year') == FieldProtectionLevel.CRITICAL
    
    def test_enrichable_fields(self):
        """Enrichable fields can be filled if empty."""
        assert ProtectedFieldsPolicy.get_protection_level('publisher') == FieldProtectionLevel.ENRICHABLE
        assert ProtectedFieldsPolicy.get_protection_level('location') == FieldProtectionLevel.ENRICHABLE
        assert ProtectedFieldsPolicy.get_protection_level('doi') == FieldProtectionLevel.ENRICHABLE
    
    def test_formattable_fields(self):
        """Formattable fields can always be modified."""
        assert ProtectedFieldsPolicy.get_protection_level('pub_type') == FieldProtectionLevel.FORMATTABLE
    
    def test_unknown_field_defaults_to_critical(self):
        """Unknown fields should default to CRITICAL (safe default)."""
        assert ProtectedFieldsPolicy.get_protection_level('unknown_field') == FieldProtectionLevel.CRITICAL


class TestModificationAuthorization:
    """Test modification authorization logic."""
    
    def test_immutable_field_always_denied(self):
        """Immutable fields can never be modified."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'id', '123', '456', has_external_verification=True
        )
        assert not allowed
        assert 'immutable' in reason.lower()
    
    def test_formattable_field_always_allowed(self):
        """Formattable fields can always be modified."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'pub_type', 'journal article', 'Journal Article'
        )
        assert allowed
    
    def test_enrichable_empty_field_allowed(self):
        """Enrichable fields can be filled if empty."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'publisher', None, 'Oxford University Press'
        )
        assert allowed
        assert 'enriching' in reason.lower()
    
    def test_enrichable_empty_field_with_verification(self):
        """Enrichable fields with verification are allowed."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'publisher', '', 'Oxford University Press', has_external_verification=True
        )
        assert allowed
        assert 'verified' in reason.lower()
    
    def test_enrichable_existing_field_without_verification_denied(self):
        """Cannot modify existing enrichable field without verification."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'publisher', 'Old Publisher', 'New Publisher', has_external_verification=False
        )
        assert not allowed
        assert 'verification' in reason.lower()
    
    def test_enrichable_existing_field_with_verification_allowed(self):
        """Can modify existing enrichable field with verification."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'publisher', 'Old Publisher', 'New Publisher', has_external_verification=True
        )
        assert allowed
    
    def test_enrichable_formatting_only_allowed(self):
        """Formatting-only changes to enrichable fields are allowed."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'publisher', 'oxford university press', 'Oxford University Press', is_formatting_only=True
        )
        assert allowed
        assert 'formatting' in reason.lower()
    
    def test_critical_field_without_verification_denied(self):
        """Cannot modify critical field without verification."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'author', 'Smith, J.', 'Smith, John', has_external_verification=False
        )
        assert not allowed
        assert 'verification' in reason.lower()
    
    def test_critical_field_with_verification_allowed(self):
        """Can modify critical field with verification (still requires user approval)."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'author', 'Smith, J.', 'Smith, John', has_external_verification=True
        )
        assert allowed
        assert 'approval' in reason.lower()
    
    def test_critical_field_formatting_allowed(self):
        """Formatting-only changes to critical fields allowed (with approval)."""
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            'title', 'the great gatsby', 'The Great Gatsby', is_formatting_only=True
        )
        assert allowed


class TestDecorator:
    """Test field authorization decorator."""
    
    def test_decorator_allows_valid_modification(self):
        """Decorator should allow valid modifications."""
        @require_field_authorization
        def modify_field(field_name, old_value, new_value, **kwargs):
            return f"Modified {field_name}"
        
        result = modify_field('pub_type', 'article', 'Article')
        assert result == "Modified pub_type"
    
    def test_decorator_blocks_invalid_modification(self):
        """Decorator should block invalid modifications."""
        @require_field_authorization
        def modify_field(field_name, old_value, new_value, **kwargs):
            return f"Modified {field_name}"
        
        with pytest.raises(PermissionError) as exc_info:
            modify_field('id', '123', '456')
        
        assert 'immutable' in str(exc_info.value).lower()


class TestPolicyMetadata:
    """Test policy metadata."""
    
    def test_policy_version_exists(self):
        """Policy should have version number."""
        assert hasattr(ProtectedFieldsPolicy, 'POLICY_VERSION')
        assert ProtectedFieldsPolicy.POLICY_VERSION == "1.0.0"
    
    def test_all_fields_classified(self):
        """All fields should be classified."""
        all_fields = ProtectedFieldsPolicy.get_all_fields()
        
        # Check some expected fields
        assert 'id' in all_fields
        assert 'author' in all_fields
        assert 'publisher' in all_fields
        assert 'pub_type' in all_fields


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
