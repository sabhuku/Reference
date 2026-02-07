"""
Check for duplicate references in the database (BUG-002 verification)
"""
import sys
sys.path.insert(0, 'C:\\Users\\stenf\\Documents\\referencing_backup')

from ui.database import db, ProjectReference
from ui.app import app

# Create app context
with app.app_context():
    # Query for duplicates
    query = """
    SELECT title, COUNT(*) as count 
    FROM project_references 
    GROUP BY title 
    HAVING count > 1
    """
    
    duplicates = db.session.execute(db.text(query)).fetchall()
    
    print("=" * 70)
    print("BUG-002 VERIFICATION: Checking for Duplicate Database Inserts")
    print("=" * 70)
    print()
    
    if duplicates:
        print(f"FAIL: Found {len(duplicates)} duplicate titles:")
        print()
        for row in duplicates:
            print(f'  - "{row[0]}": {row[1]} copies')
        print()
        print("This indicates BUG-002 may not be fully fixed.")
    else:
        print("PASS: No duplicate references found!")
        print()
        print("All references have unique titles.")
        print("BUG-002 fix verified successfully.")
    
    print()
    print("=" * 70)
    
    # Also show total reference count
    total = db.session.query(ProjectReference).count()
    print(f"Total references in database: {total}")
    print("=" * 70)
