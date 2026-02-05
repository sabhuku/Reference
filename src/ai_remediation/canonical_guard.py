"""
Canonical Data Guard - Week 3 Implementation

Protects the canonical references table from unauthorized modifications.
Only whitelisted services can write to the references table.
"""
from typing import Set, Optional
from threading import RLock
from ui.database import db
from src.ai_remediation.protected_fields import ProtectedFieldsPolicy, FieldProtectionLevel
from src.ai_remediation.audit_logger import log_unauthorized_access, log_field_modified


class CanonicalDataGuard:
    """
    Write protection for canonical references table.
    
    Ensures:
    1. Only authorized callers can write to references
    2. Immutable fields are never modified
    3. All modifications are logged
    """
    
    # Whitelisted callers (services allowed to write to references)
    AUTHORIZED_CALLERS = {
        'user_manual_edit',      # User directly editing reference
        'docx_importer',         # DOCX import
        'api_lookup',            # External API lookup (CrossRef, PubMed, etc.)
        'tier_0_auto_fix',       # Tier 0 deterministic fixes
        'tier_1_auto_enrich',    # Tier 1 auto-enrichment (high confidence)
        'user_approved_suggestion'  # User accepted AI suggestion
    }
    
    def __init__(self):
        """Initialize canonical data guard."""
        self._lock = RLock()
    
    def authorize_write(
        self,
        caller: str,
        reference_id: int,
        field_name: str,
        old_value: any,
        new_value: any,
        user_id: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Authorize a write operation to the references table.
        
        Args:
            caller: Identifier of the calling service
            reference_id: ID of reference being modified
            field_name: Name of field being modified
            old_value: Current value
            new_value: Proposed new value
            user_id: User ID (if applicable)
        
        Returns:
            (authorized: bool, reason: str)
        """
        with self._lock:
            # Check 1: Caller is authorized
            if caller not in self.AUTHORIZED_CALLERS:
                log_unauthorized_access(
                    event_type='unauthorized_write_attempt',
                    details={
                        'caller': caller,
                        'reference_id': reference_id,
                        'field': field_name,
                        'reason': 'Caller not in whitelist'
                    },
                    user_id=user_id
                )
                return False, f"Caller '{caller}' not authorized to write to references table"
            
            # Check 2: Field is not immutable
            protection_level = ProtectedFieldsPolicy.get_protection_level(field_name)
            
            if protection_level == FieldProtectionLevel.IMMUTABLE:
                log_unauthorized_access(
                    event_type='immutable_field_violation',
                    details={
                        'caller': caller,
                        'reference_id': reference_id,
                        'field': field_name,
                        'reason': 'Attempted to modify immutable field'
                    },
                    user_id=user_id
                )
                return False, f"Field '{field_name}' is immutable and cannot be modified"
            
            # Check 3: No value change (optimization)
            if old_value == new_value:
                return False, "No change in value"
            
            # Authorization passed - log the modification
            log_field_modified(
                reference_id=reference_id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                source=caller,
                user_id=user_id
            )
            
            return True, f"Write authorized for caller '{caller}'"
    
    def apply_modification(
        self,
        caller: str,
        reference: 'Reference',  # Type hint for Reference model
        field_name: str,
        new_value: any,
        user_id: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Apply a modification to a reference field (with authorization).
        
        Args:
            caller: Identifier of the calling service
            reference: Reference object to modify
            field_name: Name of field to modify
            new_value: New value
            user_id: User ID (if applicable)
        
        Returns:
            (success: bool, message: str)
        """
        with self._lock:
            # Get old value
            old_value = getattr(reference, field_name, None)
            
            # Authorize write
            authorized, reason = self.authorize_write(
                caller=caller,
                reference_id=reference.id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                user_id=user_id
            )
            
            if not authorized:
                return False, reason
            
            # Apply modification
            try:
                setattr(reference, field_name, new_value)
                db.session.commit()
                return True, f"Field '{field_name}' modified successfully"
            except Exception as e:
                db.session.rollback()
                return False, f"Database error: {str(e)}"
    
    def batch_apply_modifications(
        self,
        caller: str,
        reference: 'Reference',
        modifications: dict,
        user_id: Optional[int] = None
    ) -> tuple[bool, str, list]:
        """
        Apply multiple modifications to a reference (with authorization).
        
        Args:
            caller: Identifier of the calling service
            reference: Reference object to modify
            modifications: {field_name: new_value}
            user_id: User ID (if applicable)
        
        Returns:
            (success: bool, message: str, failed_fields: list)
        """
        with self._lock:
            failed_fields = []
            
            for field_name, new_value in modifications.items():
                old_value = getattr(reference, field_name, None)
                
                # Authorize write
                authorized, reason = self.authorize_write(
                    caller=caller,
                    reference_id=reference.id,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    user_id=user_id
                )
                
                if not authorized:
                    failed_fields.append({
                        'field': field_name,
                        'reason': reason
                    })
                    continue
                
                # Apply modification
                try:
                    setattr(reference, field_name, new_value)
                except Exception as e:
                    failed_fields.append({
                        'field': field_name,
                        'reason': f"Error: {str(e)}"
                    })
            
            # Commit all changes
            if not failed_fields:
                try:
                    db.session.commit()
                    return True, f"All {len(modifications)} fields modified successfully", []
                except Exception as e:
                    db.session.rollback()
                    return False, f"Database commit failed: {str(e)}", []
            else:
                db.session.rollback()
                return False, f"{len(failed_fields)} fields failed authorization", failed_fields
    
    @staticmethod
    def is_caller_authorized(caller: str) -> bool:
        """Check if caller is authorized."""
        return caller in CanonicalDataGuard.AUTHORIZED_CALLERS


# Decorator for protecting reference modifications
def require_canonical_authorization(caller: str):
    """
    Decorator to enforce canonical data guard.
    
    Usage:
        @require_canonical_authorization('tier_0_auto_fix')
        def apply_tier0_fix(reference, field_name, new_value):
            ...
    """
    def decorator(func):
        def wrapper(reference, field_name, new_value, **kwargs):
            guard = CanonicalDataGuard()
            user_id = kwargs.get('user_id')
            
            success, message = guard.apply_modification(
                caller=caller,
                reference=reference,
                field_name=field_name,
                new_value=new_value,
                user_id=user_id
            )
            
            if not success:
                raise PermissionError(f"Canonical data guard: {message}")
            
            return func(reference, field_name, new_value, **kwargs)
        
        return wrapper
    return decorator
