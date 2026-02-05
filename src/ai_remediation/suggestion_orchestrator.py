"""
Suggestion Orchestrator

Coordinates GPT-5 generation → validation → storage pipeline.
This is the main entry point for AI-assisted remediation.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from src.ai_remediation.gpt5_service import GPT5Service
from src.ai_remediation.validation import ValidationOrchestrator
from src.ai_remediation.feature_flags import FeatureFlagService
from src.ai_remediation.metrics import AIMetricsCollector
from src.ai_remediation.audit_logger import AuditLogger, AuditEventType
from src.ai_remediation.models import AISuggestion
from src.ai_remediation.external_services import ExternalMetadataService
from src.ai_remediation.calibration_service import CalibrationService
from src.ai_remediation.drift_monitor import DriftMonitor
from ui.database import db, Reference

logger = logging.getLogger(__name__)


class SuggestionOrchestrator:
    """
    Orchestrates AI suggestion generation and validation.
    
    Flow:
    1. Check feature flag (ai_suggestions)
    2. Generate suggestion via GPT-5
    3. Validate through 7-stage pipeline
    4. Store in ai_suggestions table
    5. Log metrics and audit trail
    6. Return suggestion (NOT applied)
    """
    
    def __init__(
        self,
        gpt5_service: Optional[GPT5Service] = None,
        db_session=None
    ):
        """
        Initialize orchestrator with dependencies.
        
        Args:
            gpt5_service: GPT-5 service (creates default if None)
            db_session: Database session for metrics and audit logger.
        """
        self.feature_flags = FeatureFlagService()
        self.gpt5_service = gpt5_service or GPT5Service()
        self.validator = ValidationOrchestrator()
        self.metrics = AIMetricsCollector(db_session)
        self.audit_logger = AuditLogger(db_session)
        self.external_service = ExternalMetadataService()
        self.calibration_service = CalibrationService()
        self.drift_monitor = DriftMonitor(window_size=1000, baseline_window_size=500)
        self.db = db_session
        
        logger.info("SuggestionOrchestrator initialized")
    
    def generate_and_validate(
        self,
        reference_id: int,
        user_id: int,
        tier: str = "tier_1",
        violations: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and validate AI suggestion for a reference.
        
        CRITICAL: This is SHADOW MODE ONLY - suggestions are NOT applied!
        
        Args:
            reference_id: Reference ID to remediate
            user_id: User ID for logging
            tier: Remediation tier (tier_0, tier_1, tier_2)
            violations: Optional list of detected violations
        
        Returns:
            Suggestion dictionary if successful, None if feature disabled or failed
        """
        # Step 1: Check feature flag
        if not self.feature_flags.is_enabled('ai_suggestions', user_id):
            logger.info(
                f"AI suggestions disabled for user {user_id} (feature flag off)"
            )
            return None
        
        # Step 2: Load reference
        reference = Reference.query.get(reference_id)
        if not reference:
            logger.error(f"Reference {reference_id} not found")
            return None
        
        reference_dict = reference.to_dict()
        
        # Step 2: Fetch external metadata (Stage 3 Verification)
        external_metadata = None
        try:
            external_metadata = self.external_service.fetch_metadata(reference_dict)
        except Exception as e:
            logger.warning(f"External metadata fetch failed: {e}")

        # Step 3: Generate suggestion
        try:
            logger.info(
                f"Generating AI suggestion: reference_id={reference_id}, "
                f"tier={tier}, user_id={user_id}"
            )
            
            suggestion_data = self.gpt5_service.generate_suggestion(
                reference=reference_dict,
                violations=violations,
                tier=tier,
                user_id=user_id,
                external_metadata=external_metadata 
            )
            
            # Extract patches and metadata
            patches = suggestion_data.get('patches', [])
            raw_confidence = suggestion_data.get('overall_confidence', 0.0)
            metadata = suggestion_data.get('metadata', {})
            model_version = metadata.get('model_version', 'gpt-4-default')
            
            # Calibrate confidence score
            try:
                calibrated_confidence = self.calibration_service.calibrate(
                    raw_confidence=raw_confidence,
                    model_version=model_version
                )
                
                # Get calibration profile for audit logging
                calibration_profile = self.calibration_service.load_profile(model_version)
                calibration_method = calibration_profile.method if calibration_profile else 'fallback'
                calibration_profile_version = calibration_profile.created_at if calibration_profile else None
                
            except Exception as e:
                logger.error(f"Calibration failed: {e}", exc_info=True)
                
                # Record calibration failure
                self.metrics.record_event(
                    event_type='calibration_failed',
                    event_data={
                        'error': str(e),
                        'model_version': model_version,
                        'raw_confidence': raw_confidence
                    },
                    user_id=user_id,
                    reference_id=reference_id
                )
                
                # FAIL CLOSED: Block suggestion if calibration fails
                return None
            
            # Store both raw and calibrated confidence
            suggestion_data['raw_confidence'] = raw_confidence
            suggestion_data['calibrated_confidence'] = calibrated_confidence
            suggestion_data['overall_confidence'] = calibrated_confidence  # Use calibrated for gating
            
            # Add tier to suggestion data for validation
            suggestion_data['tier'] = tier
            
            logger.info(
                f"GPT-5 generated {len(patches)} patches with "
                f"raw_confidence={raw_confidence:.2f}, "
                f"calibrated_confidence={calibrated_confidence:.2f} "
                f"(method={calibration_method})"
            )
            
        except Exception as e:
            logger.error(f"GPT-5 generation failed: {e}", exc_info=True)
            
            # Record failure metric
            self.metrics.record_event(
                event_type='suggestion_generation_failed',
                event_data={'error': str(e), 'tier': tier},
                user_id=user_id,
                reference_id=reference_id
            )
            
            return None
        
        # Step 4: Validate suggestion
        validation_passed = False
        validation_result = None
        try:
            logger.info(f"Validating suggestion for reference_id={reference_id}")
            validation_result = self.validator.validate(
                suggestion=suggestion_data,
                reference=reference_dict,
                violations=violations or [],
                external_metadata=external_metadata
            )
            
            if not validation_result.passed:
                logger.warning(
                    f"Suggestion failed validation at stage {validation_result.stage_passed}: "
                    f"{[r.code for r in validation_result.rejections]}"
                )
                
                # Record validation failure
                self.metrics.record_validation_failure(
                    suggestion_id=None,  # Not stored yet
                    reference_id=reference_id,
                    stage_failed=validation_result.stage_passed + 1,
                    rejection_codes=[r.code.value for r in validation_result.rejections]
                )
                
                # Still store failed suggestion for analysis
                validation_passed = False
            else:
                logger.info("Suggestion passed all 7 validation stages")
                validation_passed = True
        
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            validation_passed = False
            validation_result = None
        
        # Step 5: Store in database (SHADOW MODE - not applied!)
        try:
            suggestion = AISuggestion(
                reference_id=reference_id,
                user_id=user_id,
                tier=tier,
                patches=json.dumps(patches),
                rationale=json.dumps(suggestion_data.get('rationales', {})),
                confidence_scores=json.dumps(suggestion_data.get('confidence_scores', {})),
                validation_passed=validation_passed,
                validation_errors=(
                    json.dumps(validation_result.to_dict()['rejections']) 
                    if validation_result and not validation_passed else None
                ),
                status='pending',  # SHADOW MODE: never auto-applied
                created_at=datetime.utcnow(),
                tokens_used=metadata.get('tokens_used'),
                cost_usd=metadata.get('cost_usd'),
                latency_ms=metadata.get('latency_ms'),
                model_version=metadata.get('model_version')
            )
            
            db.session.add(suggestion)
            db.session.commit()
            
            suggestion_id = suggestion.id
            
            logger.info(
                f"Suggestion stored: id={suggestion_id}, "
                f"validation_passed={validation_passed}"
            )
            
        except Exception as e:
            logger.error(f"Failed to store suggestion: {e}", exc_info=True)
            db.session.rollback()
            return None
        
        # Step 6: Record metrics
        try:
            self.metrics.record_suggestion_generated(
                suggestion_id=suggestion_id,
                reference_id=reference_id,
                user_id=user_id,
                tier=tier,
                num_patches=len(patches),
                avg_confidence=overall_confidence,
                latency_ms=metadata.get('latency_ms', 0)
            )
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}", exc_info=True)
        
        # Step 7: Audit log
        try:
            self.audit_logger.log_event(
                event_type=AuditEventType.SUGGESTION_GENERATED,
                details={
                    'tier': tier,
                    'num_patches': len(patches),
                    'validation_passed': validation_passed,
                    'raw_confidence': raw_confidence,
                    'calibrated_confidence': calibrated_confidence,
                    'confidence_delta': raw_confidence - calibrated_confidence,
                    'overall_confidence': calibrated_confidence,
                    'model_version': model_version,
                    'calibration_method': calibration_method,
                    'calibration_profile_version': calibration_profile_version
                },
                user_id=user_id,
                reference_id=reference_id,
                suggestion_id=suggestion_id
            )
        except Exception as e:
            logger.error(f"Failed to log audit trail: {e}", exc_info=True)
        
        # Step 8: Return suggestion (NOT applied!)
        return {
            'suggestion_id': suggestion_id,
            'reference_id': reference_id,
            'tier': tier,
            'patches': patches,
            'overall_confidence': overall_confidence,
            'validation_passed': validation_passed,
            'validation_details': validation_result.to_dict() if validation_result else None,
            'metadata': metadata,
            'status': 'pending',  # SHADOW MODE
            'created_at': suggestion.created_at.isoformat()
        }
    
    def batch_generate(
        self,
        reference_ids: List[int],
        user_id: int,
        tier: str = "tier_1"
    ) -> Dict[str, Any]:
        """
        Generate suggestions for multiple references (shadow mode batch).
        
        Args:
            reference_ids: List of reference IDs
            user_id: User ID for logging
            tier: Remediation tier
        
        Returns:
            Summary of batch results
        """
        results = {
            'total': len(reference_ids),
            'successful': 0,
            'failed': 0,
            'validation_passed': 0,
            'validation_failed': 0,
            'suggestions': []
        }
        
        for ref_id in reference_ids:
            try:
                suggestion = self.generate_and_validate(
                    reference_id=ref_id,
                    user_id=user_id,
                    tier=tier
                )
                
                if suggestion:
                    results['successful'] += 1
                    results['suggestions'].append(suggestion)
                    
                    if suggestion['validation_passed']:
                        results['validation_passed'] += 1
                    else:
                        results['validation_failed'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Batch generation failed for ref {ref_id}: {e}")
                results['failed'] += 1
        
        logger.info(
            f"Batch generation complete: {results['successful']}/{results['total']} successful, "
            f"{results['validation_passed']} passed validation"
        )
        
        return results
