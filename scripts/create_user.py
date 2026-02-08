"""
Create a user account for the Reference Assistant.
"""
import os
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.app import app, db
from ui.database import User
from werkzeug.security import generate_password_hash

print("\n" + "="*60)
print("CREATE USER ACCOUNT")
print("="*60)

email = input("\nEnter email: ").strip()
username = input("Enter username: ").strip()
password = input("Enter password: ").strip()

with app.app_context():
    # Check if user exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f"\nUser with email '{email}' already exists!")
        print("="*60 + "\n")
        sys.exit(1)
    
    # Create user
    user = User(
        email=email,
        username=username,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    
    print(f"\nUser created successfully!")
    print(f"  Email: {email}")
    print(f"  Username: {username}")
    print(f"  ID: {user.id}")
    print("\nYou can now log in with these credentials.")
    print("="*60 + "\n")
