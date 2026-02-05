"""
Database migration script to create Project and ProjectReference tables.

This script adds multi-project support to the database for authenticated users.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.app import app
from ui.database import db, Project, ProjectReference

def migrate():
    """Create new tables for multi-project support."""
    with app.app_context():
        print("Creating Project and ProjectReference tables...")
        
        # Create tables
        db.create_all()
        
        print("[PASS] Tables created successfully!")
        print()
        print("New tables:")
        print("  - projects: Stores user projects")
        print("  - project_references: Stores references within projects")
        print()
        print("Next: Existing users will get a default project auto-created")
        print("      when they first use the multi-project UI.")

if __name__ == "__main__":
    migrate()
