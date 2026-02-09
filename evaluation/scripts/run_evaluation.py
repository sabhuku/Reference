"""
Offline pipeline evaluation runner.

Executes run_pipeline() in analysis_mode=True for each reference in corpus.
Saves full pipeline output as immutable JSON artifacts.
"""

import csv
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from modelling.pipeline import run_pipeline


def run_evaluation(corpus_path, output_dir):
    """
    Execute pipeline on evaluation corpus.
    
    Args:
        corpus_path: Path to corpus.csv
        output_dir: Directory for JSON reports
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(corpus_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            ref_id = row['id']
            reference_text = row['reference_text']
            
            print(f"Processing {ref_id}...")
            
            # Run pipeline in ANALYSIS MODE (Stage 3 disabled)
            result = run_pipeline(reference_text, analysis_mode=True)
            
            # Add evaluation metadata
            result['evaluation_metadata'] = {
                'id': ref_id,
                'true_type': row['true_type'],
                'notes': row.get('notes', ''),
                'analysis_mode': True,  # Explicit flag for traceability
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Save as JSON
            output_path = output_dir / f"{ref_id}.json"
            with open(output_path, 'w', encoding='utf-8') as out:
                json.dump(result, out, indent=2)
            
            print(f"  -> Saved to {output_path}")


if __name__ == '__main__':
    corpus = ROOT / 'evaluation' / 'corpus.csv'
    reports = ROOT / 'evaluation' / 'reports'
    
    if not corpus.exists():
        print(f"ERROR: Corpus file not found: {corpus}")
        sys.exit(1)
    
    run_evaluation(corpus, reports)
    print("\nEvaluation complete.")
