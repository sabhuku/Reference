"""
Quick Start Script for Shadow Mode Testing

This script helps you set the API key and run shadow mode tests.
"""
import os
import sys

# Instructions
print("\n" + "="*60)
print("SHADOW MODE - QUICK START")
print("="*60)
print()
print("To run shadow mode with real GPT-5, you need to set your API key.")
print()
print("Option 1: Set environment variable (PowerShell)")
print("-" * 60)
print('$env:OPENAI_API_KEY = "sk-your-key-here"')
print('python -m src.ai_remediation.shadow_mode --test')
print()
print("Option 2: Test infrastructure without API (Mock mode)")
print("-" * 60)
print('python test_shadow_mode_mock.py')
print()
print("Option 3: Add API key to this script")
print("-" * 60)
print("Edit this file and add your API key below:")
print()

# EDIT THIS LINE - Add your API key here
OPENAI_API_KEY = ""  # <-- Put your API key here

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    print(f"✅ API key loaded from script")
    print()
    print("Running shadow mode test with 5 references...")
    print("="*60)
    print()
    
    # Run shadow mode
    os.system("python -m src.ai_remediation.shadow_mode --test")
else:
    print("⚠️  No API key set!")
    print()
    print("Please either:")
    print("1. Edit this file and add your key to OPENAI_API_KEY variable")
    print("2. Set $env:OPENAI_API_KEY in PowerShell")
    print("3. Run mock test: python test_shadow_mode_mock.py")
    print()
    print("="*60)
