"""
Model Adapter Interface and OpenAI Implementation

This module provides a strict architectural boundary between the AI remediation
system and external LLM providers.

CRITICAL BOUNDARIES:
- NO database access
- NO validation logic
- NO calibration
- NO autonomous writes
- NO business rules

The adapter is purely a translation layer: reference payload → model response.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging
import time
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """
    Standardized response from any LLM provider.
    
    This is the ONLY output format allowed from adapters.
    """
    suggestion: Dict[str, Any]  # The raw suggestion data (patches, etc.)
    confidence: float  # Model's confidence score (0.0 to 1.0)
    rationale: str  # Human-readable explanation
    metadata: Dict[str, Any]  # Provider-specific metadata (tokens, latency, etc.)
    
    def __post_init__(self):
        """Validate response structure."""
        if not isinstance(self.suggestion, dict):
            raise ValueError("suggestion must be a dictionary")
        
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be a number")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if not isinstance(self.rationale, str):
            raise ValueError("rationale must be a string")
        
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")


class ModelAdapter(ABC):
    """
    Abstract base class for LLM provider adapters.
    
    All adapters MUST:
    - Be stateless
    - Return ModelResponse
    - Handle their own retries
    - Handle their own timeouts
    - Log provider + model version
    
    All adapters MUST NOT:
    - Access the database
    - Apply validation rules
    - Apply calibration
    - Modify reference data
    - Make gating decisions
    """
    
    @abstractmethod
    def generate_suggestion(
        self,
        reference_payload: Dict[str, Any],
        tier: str = "tier_1",
        violations: Optional[list] = None,
        external_metadata: Optional[Dict] = None
    ) -> ModelResponse:
        """
        Generate a suggestion for the given reference.
        
        Args:
            reference_payload: Reference data (title, authors, year, etc.)
            tier: Remediation tier (tier_0, tier_1, tier_2)
            violations: Optional list of detected violations
            external_metadata: Optional verified metadata from external APIs
        
        Returns:
            ModelResponse with suggestion, confidence, rationale, metadata
        
        Raises:
            ModelAdapterError: If generation fails after retries
        """
        pass


class ModelAdapterError(Exception):
    """Base exception for model adapter errors."""
    pass


class OpenAIAdapter(ModelAdapter):
    """
    OpenAI GPT-5 adapter with strict architectural isolation.
    
    Features:
    - Structured JSON response format
    - 3 retries with exponential backoff
    - 30-second timeout
    - Response schema validation
    - Provider + model version logging
    
    Boundaries:
    - NO database access
    - NO validation logic
    - NO calibration
    - NO autonomous writes
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",  # Will be "gpt-5" when available
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI adapter.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (e.g., "gpt-4", "gpt-5")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ModelAdapterError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )
        
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Import OpenAI SDK
        try:
            import openai
            self.openai = openai
            self.client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
        except ImportError:
            raise ModelAdapterError(
                "OpenAI SDK not installed. Run: pip install openai"
            )
        
        logger.info(
            f"OpenAIAdapter initialized: model={self.model}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )
    
    def generate_suggestion(
        self,
        reference_payload: Dict[str, Any],
        tier: str = "tier_1",
        violations: Optional[list] = None,
        external_metadata: Optional[Dict] = None
    ) -> ModelResponse:
        """
        Generate suggestion via OpenAI API with retry logic.
        
        Args:
            reference_payload: Reference data
            tier: Remediation tier
            violations: Detected violations
            external_metadata: Verified external metadata
        
        Returns:
            ModelResponse
        
        Raises:
            ModelAdapterError: If generation fails after retries
        """
        start_time = time.time()
        
        # Build prompt
        prompt = self._build_prompt(reference_payload, tier, violations, external_metadata)
        
        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"OpenAI API call attempt {attempt}/{self.max_retries} "
                    f"for reference: {reference_payload.get('title', 'Unknown')[:50]}"
                )
                
                # Call OpenAI API with structured output
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a Harvard referencing expert. Generate structured JSON suggestions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,  # Deterministic
                    max_tokens=2000
                )
                
                # Extract response
                raw_content = response.choices[0].message.content
                
                # Parse JSON
                suggestion_data = json.loads(raw_content)
                
                # Validate and extract required fields
                model_response = self._parse_response(
                    suggestion_data,
                    response,
                    time.time() - start_time
                )
                
                logger.info(
                    f"OpenAI API success: confidence={model_response.confidence:.2f}, "
                    f"latency={model_response.metadata['latency_ms']:.0f}ms"
                )
                
                return model_response
            
            except json.JSONDecodeError as e:
                last_error = ModelAdapterError(f"Invalid JSON response: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}")
            
            except KeyError as e:
                last_error = ModelAdapterError(f"Missing required field: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}")
            
            except self.openai.APITimeoutError as e:
                last_error = ModelAdapterError(f"API timeout: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}")
            
            except self.openai.RateLimitError as e:
                last_error = ModelAdapterError(f"Rate limit exceeded: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}")
            
            except self.openai.APIError as e:
                last_error = ModelAdapterError(f"OpenAI API error: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}")
            
            except Exception as e:
                last_error = ModelAdapterError(f"Unexpected error: {e}")
                logger.error(f"Attempt {attempt} failed: {last_error}", exc_info=True)
            
            # Exponential backoff (1s, 2s, 4s)
            if attempt < self.max_retries:
                backoff = 2 ** (attempt - 1)
                logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)
        
        # All retries exhausted
        raise last_error or ModelAdapterError("All retry attempts failed")
    
    def _build_prompt(
        self,
        reference: Dict[str, Any],
        tier: str,
        violations: Optional[list],
        external_metadata: Optional[Dict]
    ) -> str:
        """
        Build the prompt for GPT-5.
        
        This is the ONLY place where prompt engineering happens.
        """
        prompt_parts = [
            "# Task: Generate Harvard Referencing Suggestion",
            "",
            f"## Reference Data",
            f"```json",
            f"{self._format_reference(reference)}",
            f"```",
            "",
            f"## Tier: {tier}",
        ]
        
        if violations:
            prompt_parts.extend([
                "",
                "## Detected Violations",
                f"```json",
                f"{violations}",
                f"```"
            ])
        
        if external_metadata:
            prompt_parts.extend([
                "",
                "## Verified External Metadata",
                f"```json",
                f"{external_metadata}",
                f"```"
            ])
        
        prompt_parts.extend([
            "",
            "## Output Format (JSON)",
            "```json",
            "{",
            '  "patches": [',
            '    {"op": "replace", "path": "/field_name", "value": "new_value"}',
            "  ],",
            '  "confidence_scores": {"field_name": 0.95},',
            '  "overall_confidence": 0.95,',
            '  "rationales": {"field_name": "Explanation..."}',
            "}",
            "```",
            "",
            "Generate the suggestion now."
        ])
        
        return "\n".join(prompt_parts)
    
    def _format_reference(self, reference: Dict[str, Any]) -> str:
        """Format reference for prompt."""
        return json.dumps(reference, indent=2)
    
    def _parse_response(
        self,
        suggestion_data: Dict[str, Any],
        api_response: Any,
        latency_seconds: float
    ) -> ModelResponse:
        """
        Parse and validate OpenAI response.
        
        Args:
            suggestion_data: Parsed JSON from API
            api_response: Raw API response object
            latency_seconds: Request latency
        
        Returns:
            ModelResponse
        
        Raises:
            ModelAdapterError: If response is malformed
        """
        # Extract required fields
        try:
            patches = suggestion_data["patches"]
            confidence_scores = suggestion_data["confidence_scores"]
            overall_confidence = suggestion_data["overall_confidence"]
            rationales = suggestion_data["rationales"]
        except KeyError as e:
            raise ModelAdapterError(f"Missing required field in response: {e}")
        
        # Validate types
        if not isinstance(patches, list):
            raise ModelAdapterError("patches must be a list")
        
        if not isinstance(confidence_scores, dict):
            raise ModelAdapterError("confidence_scores must be a dict")
        
        if not isinstance(overall_confidence, (int, float)):
            raise ModelAdapterError("overall_confidence must be a number")
        
        if not isinstance(rationales, dict):
            raise ModelAdapterError("rationales must be a dict")
        
        # Build rationale string
        rationale_text = "; ".join(
            f"{field}: {reason}" for field, reason in rationales.items()
        )
        
        # Extract metadata
        metadata = {
            "provider": "openai",
            "model": self.model,
            "model_version": api_response.model,  # Actual model used
            "latency_ms": latency_seconds * 1000,
            "tokens_used": api_response.usage.total_tokens,
            "prompt_tokens": api_response.usage.prompt_tokens,
            "completion_tokens": api_response.usage.completion_tokens,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Build suggestion dict
        suggestion = {
            "patches": patches,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_confidence,
            "rationales": rationales
        }
        
        return ModelResponse(
            suggestion=suggestion,
            confidence=overall_confidence,
            rationale=rationale_text,
            metadata=metadata
        )
