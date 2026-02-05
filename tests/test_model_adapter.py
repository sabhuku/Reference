"""
Tests for ModelAdapter and OpenAIAdapter

Verifies:
- Response schema validation
- Retry logic on transient failures
- Timeout handling
- Malformed response rejection
"""
import unittest
from unittest.mock import MagicMock, patch, Mock
import json
from src.ai_remediation.model_adapter import (
    ModelAdapter,
    OpenAIAdapter,
    ModelResponse,
    ModelAdapterError
)


class TestModelResponse(unittest.TestCase):
    """Test ModelResponse validation."""
    
    def test_valid_response(self):
        """Test valid ModelResponse creation."""
        response = ModelResponse(
            suggestion={"patches": []},
            confidence=0.95,
            rationale="Test rationale",
            metadata={"provider": "test"}
        )
        
        self.assertEqual(response.confidence, 0.95)
        self.assertEqual(response.rationale, "Test rationale")
    
    def test_invalid_confidence_range(self):
        """Test confidence must be between 0 and 1."""
        with self.assertRaises(ValueError):
            ModelResponse(
                suggestion={},
                confidence=1.5,  # Invalid
                rationale="Test",
                metadata={}
            )
    
    def test_invalid_suggestion_type(self):
        """Test suggestion must be a dict."""
        with self.assertRaises(ValueError):
            ModelResponse(
                suggestion="invalid",  # Should be dict
                confidence=0.5,
                rationale="Test",
                metadata={}
            )


class TestOpenAIAdapter(unittest.TestCase):
    """Test OpenAIAdapter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reference_payload = {
            "title": "Test Article",
            "authors": ["Smith, J."],
            "year": "2020"
        }
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_successful_generation(self, mock_openai_class):
        """Test successful suggestion generation."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "patches": [{"op": "replace", "path": "/year", "value": "2021"}],
            "confidence_scores": {"year": 0.95},
            "overall_confidence": 0.95,
            "rationales": {"year": "Corrected year"}
        })
        mock_response.model = "gpt-4"
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 50
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create adapter and generate
        adapter = OpenAIAdapter(api_key="test-key")
        result = adapter.generate_suggestion(self.reference_payload)
        
        # Verify
        self.assertIsInstance(result, ModelResponse)
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.metadata['provider'], 'openai')
        self.assertEqual(result.metadata['tokens_used'], 100)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_retry_on_rate_limit(self, mock_openai_class):
        """Test retry logic on rate limit error."""
        import openai
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # First call: rate limit error
        # Second call: success
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "patches": [],
            "confidence_scores": {},
            "overall_confidence": 0.5,
            "rationales": {}
        })
        mock_response.model = "gpt-4"
        mock_response.usage.total_tokens = 50
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 25
        
        # Create a proper mock response for the error
        error_response = MagicMock()
        error_response.request = MagicMock()
        
        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=error_response, body=None),
            mock_response
        ]
        
        # Create adapter with fast retry
        adapter = OpenAIAdapter(api_key="test-key", max_retries=3)
        
        # Should succeed on second attempt
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = adapter.generate_suggestion(self.reference_payload)
        
        self.assertIsInstance(result, ModelResponse)
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_malformed_response_rejection(self, mock_openai_class):
        """Test rejection of malformed responses."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Missing required field 'patches'
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "confidence_scores": {},
            "overall_confidence": 0.5,
            "rationales": {}
            # Missing 'patches'
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        adapter = OpenAIAdapter(api_key="test-key")
        
        # Should raise ModelAdapterError
        with self.assertRaises(ModelAdapterError) as context:
            adapter.generate_suggestion(self.reference_payload)
        
        self.assertIn("Missing required field", str(context.exception))
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def test_timeout_handling(self, mock_openai_class):
        """Test timeout error handling."""
        import openai
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # All attempts timeout
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(
            "Request timed out"
        )
        
        adapter = OpenAIAdapter(api_key="test-key", max_retries=2)
        
        # Should raise ModelAdapterError after retries
        with patch('time.sleep'):
            with self.assertRaises(ModelAdapterError) as context:
                adapter.generate_suggestion(self.reference_payload)
        
        self.assertIn("timeout", str(context.exception).lower())
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
    
    def test_missing_api_key(self):
        """Test error when API key is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ModelAdapterError) as context:
                OpenAIAdapter()
            
            self.assertIn("API key", str(context.exception))


if __name__ == "__main__":
    unittest.main()
