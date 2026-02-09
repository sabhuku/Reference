"""
Compute confusion matrix for Stage 1 classification.

Matrix format:
- Rows = true labels
- Columns = predicted labels

Labels are explicitly sorted for deterministic ordering.
"""

import csv
from collections import defaultdict
from pathlib import Path
import sys

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


def compute_confusion_matrix(stage1_results_path, output_path):
    """
    Build confusion matrix from Stage 1 results.
    
    Ensures deterministic label ordering by explicit sorting.
    """
    # Read results
    with open(stage1_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    # Get unique labels (EXPLICITLY SORTED for determinism)
    true_labels = set(r['true_type'] for r in results)
    pred_labels = set(r['predicted_type'] for r in results)
    all_labels = sorted(true_labels | pred_labels)  # Union, then sort
    
    # Build matrix
    matrix = defaultdict(lambda: defaultdict(int))
    for row in results:
        true_label = row['true_type']
        pred_label = row['predicted_type']
        matrix[true_label][pred_label] += 1
    
    # Write CSV with deterministic ordering
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header (sorted column labels)
        writer.writerow(['true_label'] + all_labels)
        
        # Rows (sorted row labels)
        for true_label in all_labels:
            row = [true_label]
            for pred_label in all_labels:
                row.append(matrix[true_label][pred_label])
            writer.writerow(row)
    
    print(f"Confusion matrix saved: {output_path}")
    print(f"Label order (deterministic): {all_labels}")


if __name__ == '__main__':
    tables_dir = ROOT / 'evaluation' / 'tables'
    stage1_results = tables_dir / 'stage1_results.csv'
    output = tables_dir / 'stage1_confusion_matrix.csv'
    
    if not stage1_results.exists():
        print(f"ERROR: Stage 1 results not found: {stage1_results}")
        print("Run generate_tables.py first.")
        sys.exit(1)
    
    compute_confusion_matrix(stage1_results, output)
