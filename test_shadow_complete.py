"""
Complete Shadow Mode Test with Sample Data

Creates sample references and runs shadow mode test with real GPT-5.
"""
import os
import sys
import json

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# API KEY
API_KEY = "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"
os.environ["OPENAI_API_KEY"] = API_KEY

from ui.app import app, db
from ui.database import Reference, Bibliography
from src.ai_remediation.shadow_mode import ShadowModeRunner
from src.ai_remediation.suggestion_orchestrator import SuggestionOrchestrator
from src.ai_remediation.gpt5_service import GPT5Service

print("\n" + "="*60)
print("SHADOW MODE COMPLETE TEST")
print("="*60)
print()

with app.app_context():
    # Step 1: Create sample bibliography
    print("Step 1: Creating sample bibliography...")
    bib = Bibliography.query.first()
    if not bib:
        bib = Bibliography(name="Test Bibliography", user_id=1)
        db.session.add(bib)
        db.session.commit()
    print(f"   Bibliography ID: {bib.id}")
    
    # Step 2: Create sample references
    print("\nStep 2: Creating sample references...")
    sample_refs = [
        {
            'title': 'machine learning fundamentals',
            'authors': '["Smith, J.", "Jones, A."]',
            'year': '2024',
            'journal': 'AI Review',
            'volume': '10',
            'pages': '1-20'
        },
        {
            'title': 'deep learning applications',
            'authors': '["Brown, K."]',
            'year': '2023',
            'journal': 'Neural Networks',
            'volume': '15',
            'pages': '100-120'
        },
        {
            'title': 'natural language processing',
            'authors': '["Davis, M.", "Wilson, R."]',
            'year': '2024',
            'journal': 'Computational Linguistics',
            'volume': '8',
            'pages': '50-75'
        },
        {
            'title': 'computer vision techniques',
            'authors': '["Taylor, S."]',
            'year': '2023',
            'publisher': 'MIT Press',
            'location': 'Cambridge'
        },
        {
            'title': 'reinforcement learning',
            'authors': '["Anderson, P.", "Lee, Q."]',
            'year': '2024',
            'journal': 'Machine Learning Journal',
            'volume': '12',
            'pages': '200-250'
        }
    ]
    
    # Delete existing test refs
    Reference.query.filter_by(bibliography_id=bib.id).delete()
    db.session.commit()
    
    # Add new refs
    for ref_data in sample_refs:
        ref = Reference(
            bibliography_id=bib.id,
            source='manual',
            **ref_data
        )
        db.session.add(ref)
    
    db.session.commit()
    
    ref_count = Reference.query.filter_by(bibliography_id=bib.id).count()
    print(f"   Created {ref_count} sample references")
    
    # Step 3: Initialize GPT-5 service
    print("\nStep 3: Initializing GPT-5 service...")
    gpt5 = GPT5Service(api_key=API_KEY)
    print(f"   API Key: {API_KEY[:20]}...")
    print("   Service ready")
    
    # Step 4: Create orchestrator and runner
    print("\nStep 4: Creating orchestrator and runner...")
    orchestrator = SuggestionOrchestrator(gpt5_service=gpt5)
    runner = ShadowModeRunner(orchestrator=orchestrator, batch_size=5)
    print("   Ready to run")
    
    # Step 5: Run shadow mode test
    print("\nStep 5: Running shadow mode test...")
    print("   Processing 5 references with real GPT-5 API...")
    print("   This may take 30-60 seconds...")
    print()
    
    results = runner.run_batch(
        limit=5,
        tier='tier_1',
        bibliography_id=bib.id
    )
    
    # Step 6: Display results
    print("\n" + "="*60)
    print("SHADOW MODE TEST RESULTS")
    print("="*60)
    print(f"Total references:        {results['total']}")
    print(f"Successful:              {results['successful']}")
    print(f"Failed:                  {results['failed']}")
    print(f"Validation passed:       {results['validation_passed']}")
    print(f"Validation failed:       {results['validation_failed']}")
    if results['successful'] > 0:
        print(f"Validation pass rate:    {results['validation_pass_rate']:.1%}")
        print(f"Avg confidence:          {results['avg_confidence']:.2f}")
        print(f"Avg patches/suggestion:  {results['avg_patches_per_suggestion']:.1f}")
    print(f"Duration:                {results['duration_seconds']:.1f}s")
    print(f"Avg time/reference:      {results['avg_time_per_reference']:.2f}s")
    print("="*60)
    
    # Step 7: Save results
    output_file = 'shadow_mode_complete_test.json'
    runner.save_results(results, output_file)
    print(f"\nResults saved to: {output_file}")
    
    # Step 8: Show sample suggestions
    if results['suggestions']:
        print("\nSample Suggestions:")
        print("-" * 60)
        for i, sugg in enumerate(results['suggestions'][:3], 1):
            print(f"{i}. Reference ID: {sugg['reference_id']}")
            print(f"   Validation: {'PASSED' if sugg['validation_passed'] else 'FAILED'}")
            print(f"   Confidence: {sugg['confidence']:.2f}")
            print(f"   Patches: {sugg['num_patches']}")
            print()
    
    print("\nShadow mode test complete!")
    print("REMINDER: Suggestions are stored but NOT applied (shadow mode)")
    print("="*60 + "\n")
