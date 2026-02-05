"""
Test Suite for Suggestion Orchestrator

Tests end-to-end AI suggestion pipeline with mocked dependencies.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.ai_remediation.suggestion_orchestrator import SuggestionOrchestrator
from src.ai_remediation.validation import ValidationResult, RejectionCode
from ui.database import db, Reference


class TestSuggestionOrchestrator:
    """Test suggestion orchestrator functionality."""
    
    @pytest.fixture
    def mock_gpt5(self):
        """Mock GPT-5 service."""
        mock = Mock()
        mock.generate_suggestion.return_value = {
            'patches': [
                {
                    'op': 'replace',
                    'path': '/title',
                    'value': 'Machine learning fundamentals'
                }
            ],
            'overall_confidence': 0.95,
            'tier_used': 'tier_1',
            'requires_verification': False,
            'metadata': {
                'latency_ms': 250,
                'tokens_used': 500
            }
        }
        return mock
    
    @pytest.fixture
    def mock_validator(self):
        """Mock validation orchestrator."""
        mock = Mock()
        result = Mock()
        result.passed = True
        result.stage_passed = 7
        result.rejections = []
        result.to_dict = Mock(return_value={
            'passed': True,
            'stage_passed': 7,
            'rejections': []
        })
        mock.validate_suggestion.return_value = result
        return mock
    
    @pytest.fixture
    def mock_feature_flags(self):
        """Mock feature flag service."""
        mock = Mock()
        mock.is_enabled.return_value = True
        return mock
    
    @pytest.fixture
    def mock_metrics(self):
        """Mock metrics collector."""
        return Mock()
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger."""
        return Mock()
    
    def test_generate_and_validate_success(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should successfully generate and validate suggestion."""
        with app.app_context():
            # Create test reference
            ref = Reference(
                bibliography_id=1,
                title='machine learning fundamentals',
                authors='["Smith, J."]',
                year='2024'
            )
            db.session.add(ref)
            db.session.commit()
            
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            result = orchestrator.generate_and_validate(
                reference_id=ref.id,
                user_id=1,
                tier='tier_1'
            )
            
            assert result is not None
            assert result['validation_passed'] is True
            assert len(result['patches']) == 1
            assert result['overall_confidence'] == 0.95
            assert result['status'] == 'pending'  # SHADOW MODE
            
            # Verify GPT-5 was called
            mock_gpt5.generate_suggestion.assert_called_once()
            
            # Verify validation was called
            mock_validator.validate_suggestion.assert_called_once()
            
            # Verify metrics were recorded
            mock_metrics.record_suggestion_generated.assert_called_once()
            
            # Verify audit log
            mock_audit_logger.log_suggestion_generated.assert_called_once()
    
    def test_feature_flag_disabled(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should return None if feature flag is disabled."""
        with app.app_context():
            mock_feature_flags.is_enabled.return_value = False
            
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            result = orchestrator.generate_and_validate(
                reference_id=1,
                user_id=1
            )
            
            assert result is None
            mock_gpt5.generate_suggestion.assert_not_called()
    
    def test_reference_not_found(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should return None if reference not found."""
        with app.app_context():
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            result = orchestrator.generate_and_validate(
                reference_id=99999,  # Non-existent
                user_id=1
            )
            
            assert result is None
    
    def test_gpt5_generation_fails(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should handle GPT-5 generation failure."""
        with app.app_context():
            # Create test reference
            ref = Reference(
                bibliography_id=1,
                title='Test',
                authors='["Smith, J."]',
                year='2024'
            )
            db.session.add(ref)
            db.session.commit()
            
            # Make GPT-5 fail
            mock_gpt5.generate_suggestion.side_effect = Exception("API error")
            
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            result = orchestrator.generate_and_validate(
                reference_id=ref.id,
                user_id=1
            )
            
            assert result is None
            
            # Verify failure was recorded
            mock_metrics.record_event.assert_called_once()
            call_args = mock_metrics.record_event.call_args
            assert call_args[1]['event_type'] == 'suggestion_generation_failed'
    
    def test_validation_fails(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should store suggestion even if validation fails."""
        with app.app_context():
            # Create test reference
            ref = Reference(
                bibliography_id=1,
                title='Test',
                authors='["Smith, J."]',
                year='2024'
            )
            db.session.add(ref)
            db.session.commit()
            
            # Make validation fail
            failed_result = Mock()
            failed_result.passed = False
            failed_result.stage_passed = 2
            failed_result.rejections = [Mock(code=RejectionCode.IMMUTABLE_FIELD)]
            failed_result.to_dict = Mock(return_value={
                'passed': False,
                'stage_passed': 2,
                'rejections': [{'code': 'IMMUTABLE_FIELD'}]
            })
            mock_validator.validate_suggestion.return_value = failed_result
            
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            result = orchestrator.generate_and_validate(
                reference_id=ref.id,
                user_id=1
            )
            
            assert result is not None
            assert result['validation_passed'] is False
            
            # Verify validation failure was recorded
            mock_metrics.record_validation_failure.assert_called_once()
    
    def test_batch_generate(
        self,
        app,
        mock_gpt5,
        mock_validator,
        mock_feature_flags,
        mock_metrics,
        mock_audit_logger
    ):
        """Should generate suggestions for multiple references."""
        with app.app_context():
            # Create test references
            refs = []
            for i in range(5):
                ref = Reference(
                    bibliography_id=1,
                    title=f'Test {i}',
                    authors='["Smith, J."]',
                    year='2024'
                )
                db.session.add(ref)
                refs.append(ref)
            db.session.commit()
            
            orchestrator = SuggestionOrchestrator(
                gpt5_service=mock_gpt5,
                validator=mock_validator,
                feature_flags=mock_feature_flags,
                metrics=mock_metrics,
                audit_logger=mock_audit_logger
            )
            
            results = orchestrator.batch_generate(
                reference_ids=[r.id for r in refs],
                user_id=1
            )
            
            assert results['total'] == 5
            assert results['successful'] == 5
            assert results['validation_passed'] == 5
            assert len(results['suggestions']) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
