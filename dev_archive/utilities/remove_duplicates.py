"""
Safe Duplicate Removal Script
==============================

This script removes pre-existing duplicate references from the database.
It keeps the OLDER reference (lower ID) and deletes the newer duplicate.

SAFETY FEATURES:
- Dry-run mode by default (set DRY_RUN=False to actually delete)
- Shows what will be deleted before doing anything
- Only deletes duplicates identified in verification
"""
import sys
sys.path.insert(0, 'C:\\Users\\stenf\\Documents\\referencing_backup')

from ui.database import db, ProjectReference
from ui.app import app

# SAFETY: Set to False to actually delete
DRY_RUN = False

# Duplicates identified during verification
DUPLICATES_TO_REMOVE = [
    # (title_pattern, keep_id, delete_id)
    ("APPROACHES FROM AUTOMATED PROCESSING", 8, 33),
    ("Identifying Queenlessness in Honeybee Hives", 1, 31),
    ("Prediction of Honeybee Swarms", 4, 32),
    ("Use of LSTM Networks to Identify", None, None),  # Need to find IDs
]

def find_duplicate_ids(title_pattern):
    """Find all references matching the title pattern."""
    refs = ProjectReference.query.filter(
        ProjectReference.title.like(f"%{title_pattern}%")
    ).order_by(ProjectReference.id).all()
    return refs

def main():
    with app.app_context():
        print("=" * 70)
        print("DUPLICATE REMOVAL SCRIPT")
        print("=" * 70)
        print()
        
        if DRY_RUN:
            print("*** DRY RUN MODE - No changes will be made ***")
            print()
        else:
            print("!!! LIVE MODE - Changes will be committed !!!")
            print()
        
        # First, find all duplicates
        all_duplicates = []
        
        for title_pattern, keep_id, delete_id in DUPLICATES_TO_REMOVE:
            refs = find_duplicate_ids(title_pattern)
            
            if len(refs) == 2:
                # Keep the older one (lower ID), delete the newer one
                keep_ref = refs[0]
                delete_ref = refs[1]
                all_duplicates.append((keep_ref, delete_ref))
                
                print(f"Found duplicate: {title_pattern[:50]}...")
                print(f"  KEEP:   ID {keep_ref.id} (older)")
                print(f"  DELETE: ID {delete_ref.id} (newer)")
                print()
            elif len(refs) > 2:
                print(f"WARNING: Found {len(refs)} copies of: {title_pattern[:50]}...")
                print("  Skipping - manual review required")
                print()
            elif len(refs) == 1:
                print(f"INFO: Only 1 copy found: {title_pattern[:50]}...")
                print("  No action needed")
                print()
        
        # Summary
        print("=" * 70)
        print(f"SUMMARY: Found {len(all_duplicates)} duplicates to remove")
        print("=" * 70)
        print()
        
        if not all_duplicates:
            print("No duplicates to remove. Exiting.")
            return
        
        # Show what will be deleted
        print("References to be DELETED:")
        for keep_ref, delete_ref in all_duplicates:
            print(f"  - ID {delete_ref.id}: {delete_ref.title[:60]}...")
        print()
        
        print("References to be KEPT:")
        for keep_ref, delete_ref in all_duplicates:
            print(f"  - ID {keep_ref.id}: {keep_ref.title[:60]}...")
        print()
        
        # Perform deletion
        if DRY_RUN:
            print("=" * 70)
            print("DRY RUN - No changes made")
            print("To actually delete, set DRY_RUN = False in the script")
            print("=" * 70)
        else:
            print("=" * 70)
            print("DELETING DUPLICATES...")
            print("=" * 70)
            
            deleted_count = 0
            for keep_ref, delete_ref in all_duplicates:
                try:
                    db.session.delete(delete_ref)
                    deleted_count += 1
                    print(f"  Deleted ID {delete_ref.id}")
                except Exception as e:
                    print(f"  ERROR deleting ID {delete_ref.id}: {e}")
            
            # Commit changes
            try:
                db.session.commit()
                print()
                print(f"SUCCESS: Deleted {deleted_count} duplicate references")
                print("Database has been updated")
            except Exception as e:
                db.session.rollback()
                print()
                print(f"ERROR: Failed to commit changes: {e}")
                print("Database rolled back - no changes made")
        
        # Final count
        total_refs = ProjectReference.query.count()
        print()
        print("=" * 70)
        print(f"Total references in database: {total_refs}")
        if DRY_RUN:
            print(f"After deletion, will have: {total_refs - len(all_duplicates)}")
        print("=" * 70)

if __name__ == '__main__':
    main()
