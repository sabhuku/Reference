"""
Check WHEN duplicate references were created (BUG-002 investigation)
"""
import sys
sys.path.insert(0, 'C:\\Users\\stenf\\Documents\\referencing_backup')

from ui.database import db, ProjectReference
from ui.app import app

# Create app context
with app.app_context():
    # Get the duplicate titles
    duplicate_titles = [
        "APPROACHES FROM AUTOMATED PROCESSING OF HUMAN SPEECH TO MONITORING & PREDICTING IMPORTANT EVENTS IN HONEYBEE HIVES USING ACOUSTIC SIGNALS",
        "Identifying Queenlessness in Honeybee Hives from Audio Signals Using Machine Learning",
        "Prediction of Honeybee Swarms Using Audio Signals and Convolutional Neural Networks",
        "Use of LSTM Networks to Identify 'Queenlessness' in Honeybee Hives from Audio Signals"
    ]
    
    print("=" * 70)
    print("BUG-002 INVESTIGATION: When were duplicates created?")
    print("=" * 70)
    print()
    
    for title in duplicate_titles:
        # Find all references with this title
        refs = ProjectReference.query.filter(
            ProjectReference.title.like(f"%{title[:50]}%")
        ).all()
        
        if refs:
            print(f"Title: {title[:60]}...")
            print(f"Found {len(refs)} copies:")
            for ref in refs:
                print(f"  - ID: {ref.id}, Source: {ref.source}, DOI: {ref.doi}")
            print()
    
    print("=" * 70)
    print("CONCLUSION:")
    print("If IDs are sequential (e.g., 1,2 or 10,11), they were likely created")
    print("in the same migration run, indicating BUG-002 was not fixed.")
    print()
    print("If IDs are far apart (e.g., 1,25), they may be pre-existing duplicates")
    print("from different import/migration sessions.")
    print("=" * 70)
