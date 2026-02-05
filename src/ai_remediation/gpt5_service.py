"""
GPT-5 Service Client for AI Remediation

Thin wrapper around ModelAdapter that preserves prompt engineering logic.
This service is responsible for building prompts and translating between
the application's domain model and the adapter's interface.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.ai_remediation.model_adapter import (
    ModelAdapter,
    OpenAIAdapter,
    ModelResponse,
    ModelAdapterError
)

logger = logging.getLogger(__name__)


class GPT5Service:
    """
    GPT-5 service that delegates to OpenAIAdapter.
    
    Responsibilities:
    - Prompt engineering (system + user prompts)
    - Domain model translation
    - Metrics tracking
    
    NOT responsible for:
    - API calls (delegated to adapter)
    - Retry logic (delegated to adapter)
    - Timeout handling (delegated to adapter)
    """
    
    def __init__(
        self,
        adapter: Optional[ModelAdapter] = None,
        model: str = "gpt-4"
    ):
        """
        Initialize GPT-5 service.
        
        Args:
            adapter: Model adapter (defaults to OpenAIAdapter)
            model: Model name to use
        """
        self.adapter = adapter or OpenAIAdapter(model=model)
        self.model = model
        
        # Metrics
        self.total_requests = 0
        self.total_tokens = 0
        self.total_failures = 0
        
        logger.info(f"GPT-5 service initialized with model: {self.model}")
    
    def generate_suggestion(
        self,
        reference: Dict[str, Any],
        violations: Optional[List[Dict]] = None,
        tier: str = "tier_1",
        user_id: Optional[int] = None,
        external_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI suggestion for reference remediation.
        
        Args:
            reference: Reference data dictionary
            violations: List of detected violations
            tier: Remediation tier (tier_0, tier_1, tier_2)
            user_id: User ID for logging
            external_metadata: Optional verified metadata
        
        Returns:
            Suggestion dictionary with patches, confidence, etc.
        
        Raises:
            Exception: If generation fails
        """
        try:
            logger.info(
                f"Generating suggestion: reference_id={reference.get('id', 'unknown')}, "
                f"tier={tier}"
            )
            
            # Delegate to adapter
            model_response: ModelResponse = self.adapter.generate_suggestion(
                reference_payload=reference,
                tier=tier,
                violations=violations,
                external_metadata=external_metadata
            )
            
            # Extract suggestion data
            suggestion = model_response.suggestion
            
            # Add user_id to metadata
            suggestion['metadata']['user_id'] = user_id
            
            # Update metrics
            self.total_requests += 1
            self.total_tokens += suggestion['metadata'].get('tokens_used', 0)
            
            logger.info(
                f"Suggestion generated: {len(suggestion.get('patches', []))} patches, "
                f"confidence={model_response.confidence:.2f}"
            )
            
            return suggestion
        
        except ModelAdapterError as e:
            self.total_failures += 1
            logger.error(f"Model adapter error: {e}")
            raise Exception(f"Failed to generate suggestion: {e}")
        
        except Exception as e:
            self.total_failures += 1
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens,
            'total_failures': self.total_failures,
            'success_rate': (
                (self.total_requests - self.total_failures) / self.total_requests
                if self.total_requests > 0 else 0.0
            ),
            'avg_tokens_per_request': (
                self.total_tokens / self.total_requests
                if self.total_requests > 0 else 0
            )
        }
