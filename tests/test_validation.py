"""
Test Suite for Validation Pipeline

Comprehensive tests for all 7 validation stages.
"""
import pytest
from src.ai_remediation.validation import (
    ValidationOrchestrator,
    SchemaValidator,
    PatchStructureValidator,
    FieldAuthorizationValidator,
    ViolationMappingValidator,
    DataTypeValidator,
    ConfidenceThresholdValidator,
    BusinessRulesValidator,
    RejectionCode
)


class TestSchemaValidator:
    """Test Stage 1: Schema Validation"""
    
    def test_valid_suggestion(self):
        """Valid suggestion should pass."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}],
            'rationale': 'Fixed publisher name',
            'confidence_scores': {'publisher': 0.95}
        }
        
        rejections = SchemaValidator.validate(suggestion)
        assert len(rejections) == 0
    
    def test_missing_required_field(self):
        """Missing required field should fail."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}],
            # Missing 'rationale' and 'confidence_scores'
        }
        
        rejections = SchemaValidator.validate(suggestion)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_JSON
    
    def test_invalid_patch_structure(self):
        """Invalid patch structure should fail."""
        suggestion = {
            'patches': [{'invalid': 'structure'}],  # Missing 'op', 'path', 'value'
            'rationale': 'Test',
            'confidence_scores': {}
        }
        
        rejections = SchemaValidator.validate(suggestion)
        assert len(rejections) > 0


class TestPatchStructureValidator:
    """Test Stage 2: Patch Structure Validation"""
    
    def test_valid_patches(self):
        """Valid patches should pass."""
        patches = [
            {'op': 'replace', 'path': '/publisher', 'value': 'Oxford'},
            {'op': 'add', 'path': '/location', 'value': 'London'}
        ]
        
        rejections = PatchStructureValidator.validate(patches)
        assert len(rejections) == 0
    
    def test_unsupported_operation(self):
        """Unsupported operation should fail."""
        patches = [
            {'op': 'remove', 'path': '/publisher', 'value': 'Oxford'}  # 'remove' not allowed
        ]
        
        rejections = PatchStructureValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.UNSUPPORTED_OPERATION
    
    def test_invalid_path_format(self):
        """Invalid path format should fail."""
        patches = [
            {'op': 'replace', 'path': 'publisher', 'value': 'Oxford'}  # Missing leading '/'
        ]
        
        rejections = PatchStructureValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_PATH
    
    def test_unknown_field(self):
        """Unknown field should fail."""
        patches = [
            {'op': 'replace', 'path': '/unknown_field', 'value': 'test'}
        ]
        
        rejections = PatchStructureValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_PATH


class TestFieldAuthorizationValidator:
    """Test Stage 3: Field Authorization"""
    
    def test_immutable_field_rejected(self):
        """Immutable fields should be rejected."""
        patches = [{'op': 'replace', 'path': '/id', 'value': '999'}]
        reference = {'id': '123'}
        
        rejections = FieldAuthorizationValidator.validate(patches, reference)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.IMMUTABLE_FIELD
    
    def test_enrichable_empty_field_allowed(self):
        """Enriching empty field should be allowed."""
        patches = [{'op': 'add', 'path': '/publisher', 'value': 'Oxford'}]
        reference = {'publisher': None}
        
        rejections = FieldAuthorizationValidator.validate(patches, reference)
        assert len(rejections) == 0
    
    def test_critical_field_without_verification_rejected(self):
        """Critical field without verification should be rejected."""
        patches = [{'op': 'replace', 'path': '/author', 'value': 'Smith, John'}]
        reference = {'author': 'Smith, J.'}
        
        rejections = FieldAuthorizationValidator.validate(
            patches, reference, has_external_verification=False
        )
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.CRITICAL_FIELD_NO_VERIFICATION
    
    def test_critical_field_with_verification_allowed(self):
        """Critical field with verification should be allowed."""
        patches = [{'op': 'replace', 'path': '/author', 'value': 'Smith, John'}]
        reference = {'author': 'Smith, J.'}
        
        rejections = FieldAuthorizationValidator.validate(
            patches, reference, has_external_verification=True
        )
        assert len(rejections) == 0


class TestViolationMappingValidator:
    """Test Stage 4: Violation Mapping"""
    
    def test_patch_addresses_violation(self):
        """Patch addressing violation should pass."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        violations = [{'field': 'publisher', 'message': 'Missing publisher'}]
        
        rejections = ViolationMappingValidator.validate(patches, violations)
        assert len(rejections) == 0
    
    def test_patch_not_addressing_violation(self):
        """Patch not addressing violation should fail."""
        patches = [{'op': 'replace', 'path': '/location', 'value': 'London'}]
        violations = [{'field': 'publisher', 'message': 'Missing publisher'}]
        
        rejections = ViolationMappingValidator.validate(patches, violations)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.UNRELATED_FIELD
    
    def test_no_violations(self):
        """No violations should fail."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        violations = []
        
        rejections = ViolationMappingValidator.validate(patches, violations)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.NO_VIOLATION_MAPPED


class TestDataTypeValidator:
    """Test Stage 5: Data Type Validation"""
    
    def test_valid_year(self):
        """Valid year should pass."""
        patches = [{'op': 'replace', 'path': '/year', 'value': '2023'}]
        
        rejections = DataTypeValidator.validate(patches)
        assert len(rejections) == 0
    
    def test_invalid_year_format(self):
        """Invalid year format should fail."""
        patches = [{'op': 'replace', 'path': '/year', 'value': '23'}]  # Not 4 digits
        
        rejections = DataTypeValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_FORMAT
    
    def test_year_out_of_range(self):
        """Year out of range should fail."""
        patches = [{'op': 'replace', 'path': '/year', 'value': '2999'}]
        
        rejections = DataTypeValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.VALUE_OUT_OF_RANGE
    
    def test_invalid_data_type(self):
        """Invalid data type should fail."""
        patches = [{'op': 'replace', 'path': '/title', 'value': 123}]  # Should be string
        
        rejections = DataTypeValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_DATA_TYPE
    
    def test_empty_string(self):
        """Empty string should fail."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': '   '}]
        
        rejections = DataTypeValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.INVALID_FORMAT


class TestConfidenceThresholdValidator:
    """Test Stage 6: Confidence Threshold"""
    
    def test_tier1_high_confidence_passes(self):
        """Tier 1 with high confidence should pass."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        confidence_scores = {'publisher': 0.96}
        
        rejections = ConfidenceThresholdValidator.validate(patches, confidence_scores, 'tier_1')
        assert len(rejections) == 0
    
    def test_tier1_low_confidence_fails(self):
        """Tier 1 with low confidence should fail."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        confidence_scores = {'publisher': 0.85}  # Below 0.95 threshold
        
        rejections = ConfidenceThresholdValidator.validate(patches, confidence_scores, 'tier_1')
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.CONFIDENCE_TOO_LOW
    
    def test_tier2_medium_confidence_passes(self):
        """Tier 2 with medium confidence should pass."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        confidence_scores = {'publisher': 0.75}
        
        rejections = ConfidenceThresholdValidator.validate(patches, confidence_scores, 'tier_2')
        assert len(rejections) == 0
    
    def test_missing_confidence(self):
        """Missing confidence should fail."""
        patches = [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}]
        confidence_scores = {}  # Missing 'publisher'
        
        rejections = ConfidenceThresholdValidator.validate(patches, confidence_scores, 'tier_2')
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.MISSING_CONFIDENCE


class TestBusinessRulesValidator:
    """Test Stage 7: Business Rules"""
    
    def test_no_duplicates(self):
        """No duplicate fields should pass."""
        patches = [
            {'op': 'replace', 'path': '/publisher', 'value': 'Oxford'},
            {'op': 'replace', 'path': '/location', 'value': 'London'}
        ]
        
        rejections = BusinessRulesValidator.validate(patches)
        assert len(rejections) == 0
    
    def test_duplicate_fields(self):
        """Duplicate fields should fail."""
        patches = [
            {'op': 'replace', 'path': '/publisher', 'value': 'Oxford'},
            {'op': 'replace', 'path': '/publisher', 'value': 'Cambridge'}  # Duplicate
        ]
        
        rejections = BusinessRulesValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.DUPLICATE_FIELD
    
    def test_excessive_changes(self):
        """Too many changes should fail."""
        patches = [
            {'op': 'replace', 'path': f'/field{i}', 'value': f'value{i}'}
            for i in range(15)  # More than MAX_FIELDS_PER_SUGGESTION (10)
        ]
        
        rejections = BusinessRulesValidator.validate(patches)
        assert len(rejections) > 0
        assert rejections[0].code == RejectionCode.EXCESSIVE_CHANGES


class TestValidationOrchestrator:
    """Test full validation pipeline."""
    
    def test_valid_suggestion_passes_all_stages(self):
        """Valid suggestion should pass all 7 stages."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford University Press'}],
            'rationale': 'Added missing publisher from DOI lookup',
            'confidence_scores': {'publisher': 0.98},
            'tier': 'tier_1'
        }
        
        reference = {'publisher': None, 'title': 'Test Article'}
        violations = [{'field': 'publisher', 'message': 'Missing publisher'}]
        
        orchestrator = ValidationOrchestrator()
        result = orchestrator.validate(suggestion, reference, violations, has_external_verification=True)
        
        assert result.passed
        assert result.stage_passed == 7
        assert len(result.rejections) == 0
    
    def test_fails_at_stage_1(self):
        """Invalid schema should fail at stage 1."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}],
            # Missing 'rationale' and 'confidence_scores'
        }
        
        reference = {}
        violations = []
        
        orchestrator = ValidationOrchestrator()
        result = orchestrator.validate(suggestion, reference, violations)
        
        assert not result.passed
        assert result.stage_passed == 0
        assert len(result.rejections) > 0
    
    def test_fails_at_stage_3(self):
        """Unauthorized field should fail at stage 3."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/id', 'value': '999'}],  # Immutable field
            'rationale': 'Test',
            'confidence_scores': {'id': 1.0},
            'tier': 'tier_0'
        }
        
        reference = {'id': '123'}
        violations = [{'field': 'id', 'message': 'Test'}]
        
        orchestrator = ValidationOrchestrator()
        result = orchestrator.validate(suggestion, reference, violations)
        
        assert not result.passed
        assert result.stage_passed == 2  # Passed stages 1 and 2
        assert len(result.rejections) > 0
        assert result.rejections[0].code == RejectionCode.IMMUTABLE_FIELD
    
    def test_result_to_dict(self):
        """Result should convert to dict."""
        suggestion = {
            'patches': [{'op': 'replace', 'path': '/publisher', 'value': 'Oxford'}],
            'rationale': 'Test',
            'confidence_scores': {'publisher': 0.98},
            'tier': 'tier_1'
        }
        
        reference = {'publisher': None}
        violations = [{'field': 'publisher', 'message': 'Missing'}]
        
        orchestrator = ValidationOrchestrator()
        result = orchestrator.validate(suggestion, reference, violations, has_external_verification=True)
        
        result_dict = result.to_dict()
        
        assert 'passed' in result_dict
        assert 'stage_passed' in result_dict
        assert 'rejections' in result_dict


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
