"""
Protected Fields Policy - Phase 1, Task 1.2

Defines which fields can be modified and under what conditions.
This is the FIRST line of defense before any modification (AI or deterministic).
"""
from enum import Enum
from typing import Set


class FieldProtectionLevel(Enum):
    """Protection levels for reference fields."""
    IMMUTABLE = "immutable"  # Never modified (ID, timestamps, source document)
    CRITICAL = "critical"    # Requires external verification (author, title, year)
    ENRICHABLE = "enrichable"  # Can be filled if empty (publisher, location, DOI)
    FORMATTABLE = "formattable"  # Can be reformatted (capitalization, whitespace)


class ProtectedFieldsPolicy:
    """
    Deterministic policy for field modification authorization.
    
    This policy is IMMUTABLE and version-controlled.
    Changes require governance committee approval.
    """
    
    # Version tracking
    POLICY_VERSION = "1.0.0"
    LAST_UPDATED = "2026-02-02"
    
    # Field classifications
    IMMUTABLE_FIELDS: Set[str] = {
        'id',
        'bibliography_id',
        'added_at',
        'source',  # Original source (crossref, pubmed, manual)
    }
    
    CRITICAL_FIELDS: Set[str] = {
        'author',
        'authors',
        'title',
        'year',
    }
    
    ENRICHABLE_FIELDS: Set[str] = {
        'publisher',
        'location',
        'journal',
        'volume',
        'issue',
        'pages',
        'doi',
        'editor',
        'edition',
        'conference_name',
        'conference_location',
        'conference_date',
        'url',
    }
    
    FORMATTABLE_FIELDS: Set[str] = {
        'pub_type',
        'collection',
        'access_date',
    }
    
    @classmethod
    def get_protection_level(cls, field_name: str) -> FieldProtectionLevel:
        """
        Get protection level for a field.
        
        Args:
            field_name: Name of the field
        
        Returns:
            FieldProtectionLevel enum
        """
        if field_name in cls.IMMUTABLE_FIELDS:
            return FieldProtectionLevel.IMMUTABLE
        elif field_name in cls.CRITICAL_FIELDS:
            return FieldProtectionLevel.CRITICAL
        elif field_name in cls.ENRICHABLE_FIELDS:
            return FieldProtectionLevel.ENRICHABLE
        elif field_name in cls.FORMATTABLE_FIELDS:
            return FieldProtectionLevel.FORMATTABLE
        else:
            # Unknown fields default to CRITICAL (safe default)
            return FieldProtectionLevel.CRITICAL
    
    @classmethod
    def is_modification_allowed(
        cls,
        field_name: str,
        old_value: str,
        new_value: str,
        has_external_verification: bool = False,
        is_formatting_only: bool = False
    ) -> tuple[bool, str]:
        """
        Check if field modification is allowed.
        
        Args:
            field_name: Name of the field
            old_value: Current value (None if empty)
            new_value: Proposed new value
            has_external_verification: Whether change is verified by external API
            is_formatting_only: Whether change is formatting-only (no content change)
        
        Returns:
            (allowed: bool, reason: str)
        """
        protection_level = cls.get_protection_level(field_name)
        
        # Rule 1: IMMUTABLE fields can NEVER be modified
        if protection_level == FieldProtectionLevel.IMMUTABLE:
            return False, f"Field '{field_name}' is immutable"
        
        # Rule 2: FORMATTABLE fields can always be modified
        if protection_level == FieldProtectionLevel.FORMATTABLE:
            return True, "Formattable field"
        
        # Rule 3: ENRICHABLE fields can be filled if empty
        if protection_level == FieldProtectionLevel.ENRICHABLE:
            if old_value is None or old_value.strip() == '':
                # Filling empty field
                if has_external_verification:
                    return True, "Enriching empty field with verified data"
                else:
                    return True, "Enriching empty field (requires user approval)"
            else:
                # Correcting existing value
                if is_formatting_only:
                    return True, "Formatting existing value"
                elif has_external_verification:
                    return True, "Correcting with verified data (requires user approval)"
                else:
                    return False, f"Cannot modify existing '{field_name}' without verification"
        
        # Rule 4: CRITICAL fields require external verification
        if protection_level == FieldProtectionLevel.CRITICAL:
            if is_formatting_only:
                return True, "Formatting critical field (requires user approval)"
            elif has_external_verification:
                return True, "Modifying critical field with verification (requires user approval)"
            else:
                return False, f"Cannot modify critical field '{field_name}' without verification"
        
        # Default: deny
        return False, f"Unknown protection level for field '{field_name}'"
    
    @classmethod
    def get_all_fields(cls) -> Set[str]:
        """Get all known fields."""
        return (
            cls.IMMUTABLE_FIELDS |
            cls.CRITICAL_FIELDS |
            cls.ENRICHABLE_FIELDS |
            cls.FORMATTABLE_FIELDS
        )
    
    @classmethod
    def validate_field_name(cls, field_name: str) -> bool:
        """Check if field name is known."""
        return field_name in cls.get_all_fields()


# Policy enforcement decorator
def require_field_authorization(func):
    """
    Decorator to enforce field protection policy.
    
    Usage:
        @require_field_authorization
        def modify_field(field_name, old_value, new_value, **kwargs):
            ...
    """
    def wrapper(field_name, old_value, new_value, **kwargs):
        allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
            field_name,
            old_value,
            new_value,
            has_external_verification=kwargs.get('has_external_verification', False),
            is_formatting_only=kwargs.get('is_formatting_only', False)
        )
        
        if not allowed:
            raise PermissionError(f"Field modification denied: {reason}")
        
        return func(field_name, old_value, new_value, **kwargs)
    
    return wrapper
