
import json
import os
import sys

# Ensure we can import locally
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stage2_evaluator import Stage2Evaluator
from stage2_orchestrator import run_stage2

def run_evaluation():
    # 1. Load Gold Data
    gold_path = os.path.join(os.path.dirname(__file__), "stage2_gold_dataset.json")
    try:
        with open(gold_path, "r", encoding="utf-8") as f:
            gold_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Gold dataset not found at {gold_path}")
        return

    print(f"Loaded {len(gold_data)} gold records.")

    # 2. Generate Extracted Data
    extracted_data = []
    for record in gold_data:
        raw_ref = record["raw_reference"]
        # Simulate Stage 1 output (perfect classification for this test as per constraints)
        stage1_output = {
            "predicted_type": record["reference_type"],
            "type_confidence": 1.0 # Assume high confidence from Stage 1 for these gold examples
        }
        
        # Run Orchestrator
        extraction_result = run_stage2(raw_ref, stage1_output)
        extracted_data.append(extraction_result)

    # 3. Run Evaluation
    evaluator = Stage2Evaluator(thresholds=[0.6, 0.7, 0.8, 0.9])
    results = evaluator.evaluate_dataset(gold_data, extracted_data)

    # 4. Print Report
    import pandas as pd
    # Set pandas display options for better readability
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', lambda x: '%.4f' % x)

    print("\n=== Stage 2 Evaluation Report ===\n")
    
    for rtype, metrics in results.items():
        print(f"\n>> REFERENCE TYPE: {rtype.upper()}")
        if not metrics:
            print("  No data.")
            continue

        # Print summary for 0.7 and 0.9 thresholds
        for thresh in ["thresh_0.7", "thresh_0.9"]:
            if thresh in metrics:
                data = metrics[thresh]
                print(f"\n  Threshold: {thresh} | Macro F1: {data['summary']['macro_f1']}")
                print(f"  Field Metrics:")
                df = pd.DataFrame(data['field_metrics']).T[['precision', 'recall', 'f1', 'coverage']]
                print(df.to_string())
        print("-" * 60)

if __name__ == "__main__":
    run_evaluation()
