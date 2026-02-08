"""
Shadow Mode Test Runner with API Key

Run this script directly - it loads the API key from environment.
"""
import os
import sys

# Set API key from environment (should already be set in PowerShell)
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment!")
    print("\nPlease run in PowerShell:")
    print('$env:OPENAI_API_KEY = "your-key-here"')
    print('python run_shadow_test.py')
    sys.exit(1)

print(f"✅ API key loaded: {api_key[:20]}...")
print()

# Now run shadow mode
from src.ai_remediation.shadow_mode import main
main()
