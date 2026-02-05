"""
Validation Pipeline - Week 2 Implementation

7-stage deterministic validation pipeline for AI suggestions.
ALL suggestions (Tier 0, 1, 2) must pass this pipeline.
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import jsonschema
from src.ai_remediation.protected_fields import ProtectedFieldsPolicy, FieldProtectionLevel


class RejectionCode(Enum):
    """Machine-readable rejection codes."""
    
    # Stage 1: Schema Validation
    INVALID_JSON = "invalid_json"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FIELD_TYPE = "invalid_field_type"
    
    # Stage 2: Patch Structure
    INVALID_PATCH_FORMAT = "invalid_patch_format"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    INVALID_PATH = "invalid_path"
    
    # Stage 3: Field Authorization
    IMMUTABLE_FIELD = "immutable_field"
    CRITICAL_FIELD_NO_VERIFICATION = "critical_field_no_verification"
    UNAUTHORIZED_FIELD = "unauthorized_field"
    
    # Stage 4: Violation Mapping
    NO_VIOLATION_MAPPED = "no_violation_mapped"
    UNRELATED_FIELD = "unrelated_field"
    
    # Stage 5: Data Type Validation
    INVALID_DATA_TYPE = "invalid_data_type"
    INVALID_FORMAT = "invalid_format"
    VALUE_OUT_OF_RANGE = "value_out_of_range"
    
    # Stage 6: Confidence Threshold
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    MISSING_CONFIDENCE = "missing_confidence"
    
    # Stage 7: Business Rules
    DUPLICATE_FIELD = "duplicate_field"
    CONFLICTING_CHANGES = "conflicting_changes"
    EXCESSIVE_CHANGES = "excessive_changes"


@dataclass
class RejectionDetail:
    """Detailed rejection information."""
    stage: str
    code: RejectionCode
    message: str
    field: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation pipeline."""
    passed: bool
    stage_passed: int  # Number of stages passed (0-7)
    rejections: List[RejectionDetail]
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'passed': self.passed,
            'stage_passed': self.stage_passed,
            'rejections': [
                {
                    'stage': r.stage,
                    'code': r.code.value,
                    'message': r.message,
                    'field': r.field
                }
                for r in self.rejections
            ]
        }


class SchemaValidator:
    """Stage 1: Schema Validation"""
    
    # JSON Schema for AI suggestion
    SUGGESTION_SCHEMA = {
        "type": "object",
        "required": ["patches", "rationales", "confidence_scores", "overall_confidence"],
        "properties": {
            "patches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["op", "path", "value"],
                    "properties": {
                        "op": {"type": "string", "enum": ["replace", "add"]},
                        "path": {"type": "string"},
                        "value": {}
                    }
                }
            },
            "rationales": {"type": "object"},
            "confidence_scores": {"type": "object"},
            "overall_confidence": {"type": "number"}
        }
    }
    
    @staticmethod
    def validate(suggestion: dict) -> List[RejectionDetail]:
        """Validate suggestion against schema."""
        rejections = []
        
        try:
            jsonschema.validate(suggestion, SchemaValidator.SUGGESTION_SCHEMA)
        except jsonschema.ValidationError as e:
            rejections.append(RejectionDetail(
                stage="schema_validation",
                code=RejectionCode.INVALID_JSON,
                message=f"Schema validation failed: {e.message}",
                field=e.path[0] if e.path else None
            ))
        
        return rejections


class PatchStructureValidator:
    """Stage 2: Patch Structure Validation"""
    
    @staticmethod
    def validate(patches: List[dict]) -> List[RejectionDetail]:
        """Validate RFC 6902 patch structure."""
        rejections = []
        
        for i, patch in enumerate(patches):
            # Check operation
            if patch.get('op') not in ['replace', 'add']:
                rejections.append(RejectionDetail(
                    stage="patch_structure",
                    code=RejectionCode.UNSUPPORTED_OPERATION,
                    message=f"Unsupported operation: {patch.get('op')}",
                    expected="replace or add",
                    actual=patch.get('op')
                ))
            
            # Check path format
            path = patch.get('path', '')
            if not path.startswith('/'):
                rejections.append(RejectionDetail(
                    stage="patch_structure",
                    code=RejectionCode.INVALID_PATH,
                    message=f"Path must start with '/': {path}"
                ))
            
            # Extract field name
            field_name = path[1:] if path.startswith('/') else path
            
            # Check if field is known
            if not ProtectedFieldsPolicy.validate_field_name(field_name):
                rejections.append(RejectionDetail(
                    stage="patch_structure",
                    code=RejectionCode.INVALID_PATH,
                    message=f"Unknown field: {field_name}",
                    field=field_name
                ))
        
        return rejections


class FieldAuthorizationValidator:
    """Stage 3: Field Authorization (uses Protected Fields Policy)"""
    
    @staticmethod
    def validate(
        patches: List[dict],
        reference: dict,
        has_external_verification: bool = False
    ) -> List[RejectionDetail]:
        """Validate field modifications are authorized."""
        rejections = []
        
        for patch in patches:
            field_name = patch['path'][1:]  # Remove leading '/'
            new_value = patch['value']
            old_value = reference.get(field_name)
            
            # Check authorization
            allowed, reason = ProtectedFieldsPolicy.is_modification_allowed(
                field_name,
                old_value,
                new_value,
                has_external_verification=has_external_verification,
                is_formatting_only=False  # TODO: Detect formatting-only changes
            )
            
            if not allowed:
                # Map to rejection code
                protection_level = ProtectedFieldsPolicy.get_protection_level(field_name)
                
                if protection_level == FieldProtectionLevel.IMMUTABLE:
                    code = RejectionCode.IMMUTABLE_FIELD
                elif protection_level == FieldProtectionLevel.CRITICAL:
                    code = RejectionCode.CRITICAL_FIELD_NO_VERIFICATION
                else:
                    code = RejectionCode.UNAUTHORIZED_FIELD
                
                rejections.append(RejectionDetail(
                    stage="field_authorization",
                    code=code,
                    message=reason,
                    field=field_name
                ))
        
        return rejections


class ViolationMappingValidator:
    """Stage 4: Violation Mapping (ensures fixes address actual violations)"""
    
    @staticmethod
    def validate(
        patches: List[dict],
        violations: List[dict]
    ) -> List[RejectionDetail]:
        """Validate that patches address actual violations."""
        rejections = []
        
        if not violations:
            # No violations to fix
            rejections.append(RejectionDetail(
                stage="violation_mapping",
                code=RejectionCode.NO_VIOLATION_MAPPED,
                message="No violations to address"
            ))
            return rejections
        
        # Extract fields from violations
        violation_fields = set()
        for violation in violations:
            field = violation.get('field')
            if field:
                violation_fields.add(field)
        
        # Check each patch addresses a violation
        for patch in patches:
            field_name = patch['path'][1:]
            
            if field_name not in violation_fields:
                rejections.append(RejectionDetail(
                    stage="violation_mapping",
                    code=RejectionCode.UNRELATED_FIELD,
                    message=f"Field '{field_name}' not in violations",
                    field=field_name
                ))
        
        return rejections


class DataTypeValidator:
    """Stage 5: Data Type Validation"""
    
    @staticmethod
    def validate(patches: List[dict]) -> List[RejectionDetail]:
        """Validate data types and formats."""
        rejections = []
        
        for patch in patches:
            field_name = patch['path'][1:]
            value = patch['value']
            
            # Year validation
            if field_name == 'year':
                if not isinstance(value, str):
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.INVALID_DATA_TYPE,
                        message=f"Year must be string, got {type(value).__name__}",
                        field=field_name
                    ))
                elif not value.isdigit() or len(value) != 4:
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.INVALID_FORMAT,
                        message=f"Year must be 4-digit string, got '{value}'",
                        field=field_name
                    ))
                elif int(value) < 1000 or int(value) > 2100:
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.VALUE_OUT_OF_RANGE,
                        message=f"Year out of range: {value}",
                        field=field_name
                    ))
            
            # Authors validation
            if field_name in ['author', 'authors']:
                if not isinstance(value, (str, list)):
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.INVALID_DATA_TYPE,
                        message=f"Authors must be string or list, got {type(value).__name__}",
                        field=field_name
                    ))
            
            # String fields
            if field_name in ['title', 'publisher', 'journal', 'location']:
                if not isinstance(value, str):
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.INVALID_DATA_TYPE,
                        message=f"{field_name} must be string, got {type(value).__name__}",
                        field=field_name
                    ))
                elif len(value.strip()) == 0:
                    rejections.append(RejectionDetail(
                        stage="data_type",
                        code=RejectionCode.INVALID_FORMAT,
                        message=f"{field_name} cannot be empty",
                        field=field_name
                    ))
        
        return rejections


class ConfidenceThresholdValidator:
    """Stage 6: Confidence Threshold Validation"""
    
    # Tier-specific thresholds
    TIER_THRESHOLDS = {
        'tier_0': 1.0,   # Deterministic (always 1.0)
        'tier_1': 0.95,  # High confidence auto-enrichment
        'tier_2': 0.50,  # Medium confidence (requires approval)
        'tier_3': 0.0    # Low confidence (suppressed)
    }
    
    @staticmethod
    def validate(
        patches: List[dict],
        confidence_scores: Dict[str, float],
        tier: str
    ) -> List[RejectionDetail]:
        """Validate confidence scores meet tier threshold."""
        rejections = []
        
        threshold = ConfidenceThresholdValidator.TIER_THRESHOLDS.get(tier, 0.95)
        
        for patch in patches:
            field_name = patch['path'][1:]
            confidence = confidence_scores.get(field_name)
            
            if confidence is None:
                rejections.append(RejectionDetail(
                    stage="confidence_threshold",
                    code=RejectionCode.MISSING_CONFIDENCE,
                    message=f"Missing confidence score for field '{field_name}'",
                    field=field_name
                ))
            elif confidence < threshold:
                rejections.append(RejectionDetail(
                    stage="confidence_threshold",
                    code=RejectionCode.CONFIDENCE_TOO_LOW,
                    message=f"Confidence {confidence:.2f} below threshold {threshold:.2f}",
                    field=field_name,
                    expected=str(threshold),
                    actual=str(confidence)
                ))
        
        return rejections


class BusinessRulesValidator:
    """Stage 7: Business Rules Validation"""
    
    MAX_FIELDS_PER_SUGGESTION = 10
    
    @staticmethod
    def validate(patches: List[dict]) -> List[RejectionDetail]:
        """Validate business rules."""
        rejections = []
        
        # Rule 1: No duplicate fields
        fields_modified = [p['path'][1:] for p in patches]
        duplicates = [f for f in fields_modified if fields_modified.count(f) > 1]
        
        if duplicates:
            rejections.append(RejectionDetail(
                stage="business_rules",
                code=RejectionCode.DUPLICATE_FIELD,
                message=f"Duplicate field modifications: {set(duplicates)}"
            ))
        
        # Rule 2: Not too many changes
        if len(patches) > BusinessRulesValidator.MAX_FIELDS_PER_SUGGESTION:
            rejections.append(RejectionDetail(
                stage="business_rules",
                code=RejectionCode.EXCESSIVE_CHANGES,
                message=f"Too many fields modified: {len(patches)} > {BusinessRulesValidator.MAX_FIELDS_PER_SUGGESTION}"
            ))
        
        return rejections


class ValidationOrchestrator:
    """
    Orchestrates the 7-stage validation pipeline.
    
    Stages:
    1. Schema Validation
    2. Patch Structure Validation
    3. Field Authorization
    4. Violation Mapping
    5. Data Type Validation
    6. Confidence Threshold
    7. Business Rules
    """
    
    def __init__(self):
        self.validators = [
            ('schema_validation', SchemaValidator()),
            ('patch_structure', PatchStructureValidator()),
            ('field_authorization', FieldAuthorizationValidator()),
            ('violation_mapping', ViolationMappingValidator()),
            ('data_type', DataTypeValidator()),
            ('confidence_threshold', ConfidenceThresholdValidator()),
            ('business_rules', BusinessRulesValidator())
        ]
    
    def validate(
        self,
        suggestion: dict,
        reference: dict,
        violations: List[dict],
        external_metadata: Optional[dict] = None
    ) -> ValidationResult: 
        """
        Run the full validation pipeline.
        
        Args:
            suggestion: The raw JSON output from GPT-5
            reference: The original reference data
            violations: List of detected violations (context)
            external_metadata: Verified metadata from external APIs
            
        Returns:
            ValidationResult object
        """
        all_rejections = []
        stage_passed = 0
        
        # Stage 1: Schema Validation
        rejections = SchemaValidator.validate(suggestion)
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # Extract data
        patches = suggestion.get('patches', [])
        confidence_scores = suggestion.get('confidence_scores', {})
        tier = suggestion.get('tier', 'tier_2')
        
        # Stage 2: Patch Structure
        rejections = PatchStructureValidator.validate(patches)
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # Stage 3: Field Authorization
        auth_rejections = FieldAuthorizationValidator().validate(
            reference, 
            patches, 
            violations,
            external_metadata=external_metadata
        )
        if auth_rejections:
            all_rejections.extend([r[1] for r in auth_rejections])
            # Filter out rejected patches for subsequent stages
            start_count = len(patches)
            rejected_indices = {r[0] for r in auth_rejections}
            patches = [p for i, p in enumerate(patches) if i not in rejected_indices]
            
            if not patches and start_count > 0:
                 return ValidationResult(
                    False,
                    stage_passed,
                    all_rejections
                )
        stage_passed += 1
        
        # Stage 4: Violation Mapping
        rejections = ViolationMappingValidator.validate(patches, violations)
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # Stage 5: Data Type Validation
        rejections = DataTypeValidator.validate(patches)
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # Stage 6: Confidence Threshold
        rejections = ConfidenceThresholdValidator.validate(
            patches, confidence_scores, tier
        )
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # Stage 7: Business Rules
        rejections = BusinessRulesValidator.validate(patches)
        if rejections:
            all_rejections.extend(rejections)
            return ValidationResult(False, stage_passed, all_rejections)
        stage_passed += 1
        
        # All stages passed!
        return ValidationResult(True, stage_passed, [])
