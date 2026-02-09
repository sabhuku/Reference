"""
Compute per-class precision, recall, and F1 for Stage 1 classification.

Uses standard definitions:
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * (Precision * Recall) / (Precision + Recall)

Handles edge cases defensively:
- Labels in predictions but not in true labels
- Division by zero
"""

import csv
from pathlib import Path
import sys

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


def compute_metrics(confusion_matrix_path, output_path):
    """
    Compute P/R/F1 from confusion matrix.
    
    Defensive implementation:
    - Handles labels that appear only in predictions
    - Safe division (avoids ZeroDivisionError)
    - Preserves deterministic label ordering
    """
    # Read confusion matrix
    with open(confusion_matrix_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        labels = header[1:]  # Skip 'true_label' column
        
        matrix = {}
        for row in reader:
            true_label = row[0]
            counts = [int(x) for x in row[1:]]
            matrix[true_label] = dict(zip(labels, counts))
    
    # Compute metrics per class (using SAME label order as confusion matrix)
    metrics = []
    for label in labels:
        # True Positives (diagonal element)
        # Defensive: check if label exists as true label
        tp = matrix.get(label, {}).get(label, 0)
        
        # False Positives (predicted as label, but not true label)
        # Sum column (excluding diagonal)
        fp = 0
        for other_label in labels:
            if other_label != label:
                fp += matrix.get(other_label, {}).get(label, 0)
        
        # False Negatives (true label, but predicted as other)
        # Sum row (excluding diagonal)
        fn = 0
        if label in matrix:
            for other_label in labels:
                if other_label != label:
                    fn += matrix[label].get(other_label, 0)
        
        # Support (total true instances)
        # Defensive: handle labels that don't appear as true labels
        support = sum(matrix.get(label, {}).values())
        
        # Precision (safe division)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        
        # Recall (safe division)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        # F1 (safe division)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics.append({
            'class': label,
            'precision': f"{precision:.3f}",
            'recall': f"{recall:.3f}",
            'f1': f"{f1:.3f}",
            'support': support
        })
    
    # Write metrics (preserving label order)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['class', 'precision', 'recall', 'f1', 'support'])
        writer.writeheader()
        writer.writerows(metrics)
    
    print(f"Metrics saved: {output_path}")
    print(f"Classes evaluated: {labels}")


if __name__ == '__main__':
    tables_dir = ROOT / 'evaluation' / 'tables'
    confusion_matrix = tables_dir / 'stage1_confusion_matrix.csv'
    output = tables_dir / 'stage1_metrics.csv'
    
    if not confusion_matrix.exists():
        print(f"ERROR: Confusion matrix not found: {confusion_matrix}")
        print("Run compute_confusion_matrix.py first.")
        sys.exit(1)
    
    compute_metrics(confusion_matrix, output)
