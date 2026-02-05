"""
Shadow Mode Test - Direct API Key

This script allows you to paste your API key directly and run the test.
"""
import os
import sys

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# PASTE YOUR API KEY HERE (or it will try to read from environment)
API_KEY = "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"

# Set in environment for subprocess
os.environ["OPENAI_API_KEY"] = API_KEY

print("\n" + "="*60)
print("SHADOW MODE TEST - 5 REFERENCES")
print("="*60)
print(f"API Key: {API_KEY[:20]}...")
print()

from src.ai_remediation.shadow_mode import ShadowModeRunner
from src.ai_remediation.suggestion_orchestrator import SuggestionOrchestrator
from src.ai_remediation.gpt5_service import GPT5Service
from ui.app import app

# Create GPT-5 service with API key
gpt5 = GPT5Service(api_key=API_KEY)

# Create orchestrator
orchestrator = SuggestionOrchestrator(gpt5_service=gpt5)

# Create runner
runner = ShadowModeRunner(orchestrator=orchestrator, batch_size=5)

print("Starting shadow mode test...")
print()

with app.app_context():
    # Run on 5 references
    results = runner.run_batch(limit=5, tier='tier_1')
    
    # Print results
    print("\n" + "="*60)
    print("SHADOW MODE TEST RESULTS")
    print("="*60)
    print(f"Total references:        {results['total']}")
    print(f"Successful:              {results['successful']}")
    print(f"Failed:                  {results['failed']}")
    print(f"Validation passed:       {results['validation_passed']}")
    print(f"Validation failed:       {results['validation_failed']}")
    print(f"Validation pass rate:    {results['validation_pass_rate']:.1%}")
    print(f"Avg confidence:          {results['avg_confidence']:.2f}")
    print(f"Avg patches/suggestion:  {results['avg_patches_per_suggestion']:.1f}")
    print(f"Duration:                {results['duration_seconds']:.1f}s")
    print("="*60)
    
    # Save results
    runner.save_results(results, 'shadow_mode_test_results.json')
    print(f"\nResults saved to: shadow_mode_test_results.json")
    print("\n✅ Shadow mode test complete!")
    print("="*60 + "\n")
