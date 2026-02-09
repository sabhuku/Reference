"""
Generate evaluation tables from pipeline reports.

Produces:
- stage1_results.csv (classification results)
- stage2_results.csv (extraction results)
- pipeline_summary.csv (full pipeline summary)
"""

import csv
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


def generate_stage1_table(reports_dir, output_path):
    """
    Generate Stage 1 classification results table.
    
    Reads Stage 1 outputs from top-level pipeline fields:
    - reference_type (predicted type)
    - type_confidence (confidence score)
    
    Note: hardening_applied is not included in final pipeline output,
    so it's marked as 'unknown' in the table.
    """
    rows = []
    
    for report_file in sorted(Path(reports_dir).glob('*.json')):
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = data.get('evaluation_metadata', {})
        
        # Stage 1 fields are at TOP LEVEL of pipeline output
        rows.append({
            'id': meta.get('id', ''),
            'true_type': meta.get('true_type', ''),
            'predicted_type': data.get('reference_type', ''),
            'type_confidence': f"{data.get('type_confidence', 0.0):.3f}",
            'hardening_applied': 'unknown'  # Not in final pipeline output
        })
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'true_type', 'predicted_type', 'type_confidence', 'hardening_applied'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated Stage 1 results: {output_path}")


def generate_stage2_table(reports_dir, output_path):
    """
    Generate Stage 2 extraction results table.
    
    Reads Stage 2 outputs from data["stage2"] object.
    """
    rows = []
    
    for report_file in sorted(Path(reports_dir).glob('*.json')):
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = data.get('evaluation_metadata', {})
        stage2 = data.get('stage2', {})
        
        if stage2 is None:
            # Stage 2 not executed (rejected at Stage 1)
            rows.append({
                'id': meta.get('id', ''),
                'predicted_type': data.get('reference_type', ''),
                'status': 'not_executed',
                'missing_fields': 'N/A'
            })
        else:
            status = stage2.get('extraction_status', 'unknown')
            
            # Identify missing fields
            extracted = stage2.get('extracted_fields', {})
            missing = [k for k, v in extracted.items() if not v] if extracted else []
            missing_str = ', '.join(missing) if missing else 'none'
            
            rows.append({
                'id': meta.get('id', ''),
                'predicted_type': data.get('reference_type', ''),
                'status': status,
                'missing_fields': missing_str
            })
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'predicted_type', 'status', 'missing_fields'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated Stage 2 results: {output_path}")


def generate_pipeline_summary(reports_dir, output_path):
    """
    Generate full pipeline summary table.
    """
    rows = []
    
    for report_file in sorted(Path(reports_dir).glob('*.json')):
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = data.get('evaluation_metadata', {})
        stage2 = data.get('stage2', {})
        stage3 = data.get('stage3', {})
        
        # Stage 2 status
        if stage2 is None:
            stage2_status = 'not_executed'
        else:
            stage2_status = stage2.get('extraction_status', 'unknown')
        
        # Stage 3 status
        if stage3 is None:
            stage3_status = 'not_executed'
        else:
            stage3_status = stage3.get('status', 'unknown')
        
        rows.append({
            'id': meta.get('id', ''),
            'true_type': meta.get('true_type', ''),
            'predicted_type': data.get('reference_type', ''),
            'stage2_status': stage2_status,
            'stage3_status': stage3_status,
            'analysis_mode': str(meta.get('analysis_mode', True)),
            'timestamp': meta.get('timestamp', '')
        })
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'true_type', 'predicted_type', 'stage2_status', 
            'stage3_status', 'analysis_mode', 'timestamp'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated pipeline summary: {output_path}")


if __name__ == '__main__':
    reports_dir = ROOT / 'evaluation' / 'reports'
    tables_dir = ROOT / 'evaluation' / 'tables'
    tables_dir.mkdir(parents=True, exist_ok=True)
    
    generate_stage1_table(reports_dir, tables_dir / 'stage1_results.csv')
    generate_stage2_table(reports_dir, tables_dir / 'stage2_results.csv')
    generate_pipeline_summary(reports_dir, tables_dir / 'pipeline_summary.csv')
    
    print("\nAll tables generated successfully.")
