"""
Initialize the database for the Reference Assistant application.
Creates all tables (users, bibliographies, references).
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.app import app, db

if __name__ == '__main__':
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        print("  - users")
        print("  - bibliographies")
        print("  - references")
