"""
Test Suite for GPT-5 Service

Tests GPT-5 API client with mocked responses.
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from src.ai_remediation.gpt5_service import GPT5Service


class TestGPT5Service:
    """Test GPT-5 service functionality."""
    
    def test_initialization_with_api_key(self):
        """Should initialize with provided API key."""
        service = GPT5Service(api_key="test-key-123")
        
        assert service.api_key == "test-key-123"
        assert service.model == "gpt-4"
        assert service.total_requests == 0
    
    def test_initialization_without_api_key_raises_error(self):
        """Should raise error if no API key provided."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GPT5Service()
            
            assert "API key required" in str(exc_info.value)
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_generate_suggestion_success(self, mock_openai):
        """Should generate suggestion successfully."""
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "patches": [
                {
                    "op": "replace",
                    "path": "/title",
                    "value": "Machine learning fundamentals"
                }
            ],
            "overall_confidence": 0.95,
            "tier_used": "tier_1",
            "requires_verification": False
        })
        mock_response.usage.total_tokens = 500
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 200
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        
        reference = {
            "id": 1,
            "title": "machine learning fundamentals",
            "authors": "Smith, J."
        }
        
        violations = [
            {"field": "title", "description": "Title capitalization"}
        ]
        
        result = service.generate_suggestion(reference, violations)
        
        assert len(result['patches']) == 1
        assert result['overall_confidence'] == 0.95
        assert result['metadata']['tokens_used'] == 500
        assert service.total_requests == 1
        assert service.total_tokens == 500
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_retry_on_rate_limit(self, mock_openai):
        """Should retry on rate limit error."""
        from openai import RateLimitError
        
        # First call fails, second succeeds
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limit exceeded", response=Mock(), body=None),
            Mock(
                choices=[Mock(message=Mock(content=json.dumps({
                    "patches": [],
                    "overall_confidence": 0.0,
                    "tier_used": "tier_1",
                    "requires_verification": False
                })))],
                usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
            )
        ]
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        
        with patch('time.sleep'):  # Speed up test
            result = service.generate_suggestion(
                {"id": 1, "title": "Test"},
                [{"field": "title", "description": "Test"}]
            )
        
        assert result is not None
        assert service.total_retries == 1
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_max_retries_exceeded(self, mock_openai):
        """Should fail after max retries."""
        from openai import APIError
        
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APIError("API error", request=Mock(), body=None)
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        
        with patch('time.sleep'):  # Speed up test
            with pytest.raises(Exception) as exc_info:
                service.generate_suggestion(
                    {"id": 1, "title": "Test"},
                    [{"field": "title", "description": "Test"}]
                )
        
        assert "failed after" in str(exc_info.value)
        assert service.total_failures == 1
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_rate_limiting(self, mock_openai):
        """Should enforce rate limiting."""
        mock_response = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "patches": [],
                "overall_confidence": 0.0,
                "tier_used": "tier_1",
                "requires_verification": False
            })))],
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        )
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        service.MAX_REQUESTS_PER_MINUTE = 3  # Lower limit for testing
        
        # Make 3 requests (should succeed)
        for i in range(3):
            service.generate_suggestion(
                {"id": i, "title": "Test"},
                [{"field": "title", "description": "Test"}]
            )
        
        # 4th request should trigger rate limiting
        start_time = time.time()
        with patch('time.sleep') as mock_sleep:
            service.generate_suggestion(
                {"id": 4, "title": "Test"},
                [{"field": "title", "description": "Test"}]
            )
            
            # Should have called sleep
            assert mock_sleep.called
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_json_decode_error(self, mock_openai):
        """Should handle JSON decode errors."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON{{"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        
        with pytest.raises(Exception):
            service.generate_suggestion(
                {"id": 1, "title": "Test"},
                [{"field": "title", "description": "Test"}]
            )
        
        assert service.total_failures == 1
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_build_system_prompt(self, mock_openai):
        """Should build correct system prompt."""
        mock_openai.return_value = Mock()
        service = GPT5Service(api_key="test-key")
        
        prompt = service._build_system_prompt("tier_1")
        
        assert "Harvard citation style expert" in prompt
        assert "tier_1" in prompt
        assert "temperature = 0" in prompt.lower()
        assert "JSON" in prompt
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_build_user_prompt(self, mock_openai):
        """Should build correct user prompt."""
        mock_openai.return_value = Mock()
        service = GPT5Service(api_key="test-key")
        
        reference = {"id": 1, "title": "Test"}
        violations = [{"field": "title", "description": "Capitalization"}]
        
        prompt = service._build_user_prompt(reference, violations)
        
        assert "REFERENCE TO FIX" in prompt
        assert "Test" in prompt
        assert "DETECTED VIOLATIONS" in prompt
        assert "Capitalization" in prompt
    
    @patch('src.ai_remediation.gpt5_service.OpenAI')
    def test_get_metrics(self, mock_openai):
        """Should return service metrics."""
        mock_response = Mock(
            choices=[Mock(message=Mock(content=json.dumps({
                "patches": [],
                "overall_confidence": 0.0,
                "tier_used": "tier_1",
                "requires_verification": False
            })))],
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        )
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = GPT5Service(api_key="test-key")
        
        # Make some requests
        for i in range(3):
            service.generate_suggestion(
                {"id": i, "title": "Test"},
                [{"field": "title", "description": "Test"}]
            )
        
        metrics = service.get_metrics()
        
        assert metrics['total_requests'] == 3
        assert metrics['total_tokens'] == 300
        assert metrics['success_rate'] == 1.0
        assert metrics['avg_tokens_per_request'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
