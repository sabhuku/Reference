import json
import pandas as pd
from typing import List, Dict, Any, Set, Union

class Stage2Evaluator:
    def __init__(self, thresholds: List[float] = [0.6, 0.7, 0.8, 0.9]):
        self.thresholds = thresholds

    def normalize_value(self, value: Any) -> Any:
        """Normalizes strings for comparison. Lists are converted to sorted tuples."""
        if isinstance(value, str):
            # Standard normalization: strip, lower
            return value.strip().lower()
        elif isinstance(value, list):
            # Set match for lists (authors, editors), normalized
            return tuple(sorted([self.normalize_value(v) for v in value if v]))
        elif isinstance(value, int):
            return value
        else:
            return value

    def is_match(self, gold: Any, extracted: Any) -> bool:
        """Determines if extracted value matches gold value exactly."""
        if gold is None or extracted is None:
            return False
        return self.normalize_value(gold) == self.normalize_value(extracted)

    def evaluate_dataset(self, gold_data: List[Dict], extracted_data: List[Dict]) -> Dict[str, Any]:
        """
        Evaluates extracted data against gold data.
        Both lists must contain objects with 'raw_reference', 'reference_type'.
        """
        # Index extracted data by raw_reference for matching
        extracted_map = {item["raw_reference"]: item for item in extracted_data}
        
        # Group by reference type
        results_by_type = {
            "journal": {"gold": [], "extracted": []},
            "book":    {"gold": [], "extracted": []},
            "website": {"gold": [], "extracted": []}
        }

        for gold_item in gold_data:
            ref_type = gold_item["reference_type"]
            raw_ref = gold_item["raw_reference"]
            
            if ref_type in results_by_type:
                results_by_type[ref_type]["gold"].append(gold_item)
                # Find corresponding extracted item
                if raw_ref in extracted_map:
                    results_by_type[ref_type]["extracted"].append(extracted_map[raw_ref])
                else:
                    # Should not happen in controlled test, but handle missing extraction
                    results_by_type[ref_type]["extracted"].append(None)

        evaluation_report = {}

        for ref_type, data in results_by_type.items():
            if not data["gold"]:
                continue
                
            type_report = self._evaluate_type(ref_type, data["gold"], data["extracted"])
            evaluation_report[ref_type] = type_report

        return evaluation_report

    def _evaluate_type(self, ref_type: str, gold_list: List[Dict], extracted_list: List[Dict]) -> Dict[str, Any]:
        """Evaluates a single reference type across all thresholds."""
        type_metrics = {}

        # Get all potential fields from first gold item or define schema keys
        # Using a superset of keys found in gold for safety
        all_fields = set()
        for g in gold_list:
            all_fields.update(g.get("gold_fields", {}).keys())
        
        sorted_fields = sorted(list(all_fields))

        for threshold in self.thresholds:
            threshold_metrics = {}
            total_refs = len(gold_list)
            
            for field in sorted_fields:
                tp = 0 # Correctly extracted
                fp = 0 # Extracted but incorrect (wrong value or not in gold)
                fn = 0 # Present in gold but not extracted or below threshold
                attempted = 0 # Extraction attempted (confidence > 0 or whatever criteria, here we focus on delivered/accepted)
                
                # For coverage: Prompt says "Extraction attempted / Total references"
                # But strict rule: "A field is correct only if value matches AND confidence >= threshold"
                # Coverage usually means "System produced an output >= threshold"
                
                extracted_count = 0 # Count of fields with confidence >= threshold

                for gold_item, ext_item in zip(gold_list, extracted_list):
                    gold_val = gold_item.get("gold_fields", {}).get(field)
                    
                    if ext_item and field in ext_item.get("fields", {}):
                        field_obj = ext_item["fields"][field]
                        ext_val = field_obj.get("value")
                        conf = field_obj.get("confidence", 0.0)
                        
                        accepted = conf >= threshold
                        
                        if accepted:
                            extracted_count += 1
                            if gold_val is not None:
                                if self.is_match(gold_val, ext_val):
                                    tp += 1
                                else:
                                    fp += 1
                            else:
                                # Extracted but not in gold -> FP
                                fp += 1
                        else:
                            # Not accepted (below threshold)
                            # If it was in gold, it's a False Negative (missed opportunity)
                            if gold_val is not None:
                                fn += 1
                    else:
                        # No extraction record
                        if gold_val is not None:
                            fn += 1

                # Calculate Metrics
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0 # logic: recall = correct / gold_present. tp+fn = gold_present
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                coverage = extracted_count / total_refs if total_refs > 0 else 0.0
                
                threshold_metrics[field] = {
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "coverage": round(coverage, 4),
                    "tp": tp,
                    "fp": fp,
                    "fn": fn
                }

            # Macro Averaging
            macro_f1 = sum(m["f1"] for m in threshold_metrics.values()) / len(threshold_metrics) if threshold_metrics else 0.0
            
            type_metrics[f"thresh_{threshold}"] = {
                "field_metrics": threshold_metrics,
                "summary": {
                    "macro_f1": round(macro_f1, 4),
                    "avg_coverage": round(sum(m["coverage"] for m in threshold_metrics.values()) / len(threshold_metrics) if threshold_metrics else 0.0, 4)
                }
            }

        return type_metrics

def generate_dummy_data():
    gold = [
        {
            "raw_reference": "Ref 1",
            "reference_type": "journal",
            "gold_fields": {"year": 2020, "authors": ["Smith, J."], "title": "Paper A"}
        },
        {
            "raw_reference": "Ref 2",
            "reference_type": "journal",
            "gold_fields": {"year": 2021, "authors": ["Doe, A.", "Ray, B."], "title": "Paper B", "doi": "10.1000/1"}
        }
    ]
    extracted = [
        {
            "raw_reference": "Ref 1",
            "reference_type": "journal",
            "fields": {
                "year": {"value": 2020, "confidence": 0.95},       # TP
                "authors": {"value": ["Smith, J."], "confidence": 0.85}, # TP
                "title": {"value": "Paper A", "confidence": 0.90}    # TP
            }
        },
        {
            "raw_reference": "Ref 2",
            "reference_type": "journal",
            "fields": {
                "year": {"value": 2021, "confidence": 0.50},       # Fail (Low Conf) -> FN
                "authors": {"value": ["Doe, A."], "confidence": 0.90},   # Fail (Partial list!=match) -> FP
                "title": {"value": "Paper B", "confidence": 0.95},   # TP
                "doi": {"value": "10.1000/1", "confidence": 0.95}    # TP
            }
        }
    ]
    return gold, extracted

if __name__ == "__main__":
    gold, extracted = generate_dummy_data()
    evaluator = Stage2Evaluator()
    results = evaluator.evaluate_dataset(gold, extracted)
    
    # Example Output Formatting
    print("--- Evaluation Report ---\n")
    for rtype, metrics in results.items():
        print(f"Reference Type: {rtype.upper()}")
        for thresh, data in metrics.items():
            print(f"\n  Threshold: {thresh}")
            print(f"  Macro F1: {data['summary']['macro_f1']}")
            print(f"  Field Metrics:")
            df = pd.DataFrame(data['field_metrics']).T[['precision', 'recall', 'f1', 'coverage']]
            print(df.to_string())
            print("-" * 40)
