"""
Test script for Multi-Project UI feature - Simple ASCII version
"""
import requests
import sqlite3
import os

BASE_URL = "http://127.0.0.1:5000"

print("=" * 60)
print("MULTI-PROJECT UI - AUTOMATED VERIFICATION")
print("=" * 60)

# Test 1: Flask app health
print("\n[TEST 1] Flask App Health")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200:
        print("[PASS] Flask app is running on port 5000")
    else:
        print(f"[FAIL] Health check returned: {response.status_code}")
except Exception as e:
    print(f"[FAIL] Flask app not reachable: {e}")

# Test 2: Template files exist
print("\n[TEST 2] Template Files")
templates = [
    "ui/templates/projects.html",
    "ui/templates/index.html"
]
for template in templates:
    if os.path.exists(template):
        size = os.path.getsize(template) / 1024
        print(f"[PASS] {template} exists ({size:.1f} KB)")
    else:
        print(f"[FAIL] {template} not found")

# Test 3: Database schema
print("\n[TEST 3] Database Schema")
try:
    db_path = "instance/app.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check projects table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            print(f"[PASS] 'projects' table exists ({count} records)")
        else:
            print("[FAIL] 'projects' table not found")
        
        # Check project_references table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_references'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM project_references")
            count = cursor.fetchone()[0]
            print(f"[PASS] 'project_references' table exists ({count} records)")
        else:
            print("[FAIL] 'project_references' table not found")
        
        conn.close()
    else:
        print("[FAIL] Database file not found at instance/app.db")
except Exception as e:
    print(f"[FAIL] Database check failed: {e}")

# Test 4: Authentication protection
print("\n[TEST 4] Authentication Protection")
try:
    response = requests.get(f"{BASE_URL}/projects", allow_redirects=False)
    if response.status_code == 302:
        print("[PASS] /projects redirects unauthenticated users (status: 302)")
    elif response.status_code == 401:
        print("[PASS] /projects returns 401 for unauthenticated users")
    elif response.status_code == 200:
        print("[WARN] /projects accessible without login (unexpected)")
    else:
        print(f"[INFO] /projects returned status: {response.status_code}")
except Exception as e:
    print(f"[FAIL] Error checking /projects: {e}")

# Test 5: Routes exist in app.py
print("\n[TEST 5] Flask Routes in app.py")
try:
    with open("ui/app.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    routes = [
        "def manage_projects():",
        "def create_project():",
        "def switch_project(project_id):",
        "def rename_project(project_id):",
        "def delete_project(project_id):",
        "def inject_project_context():"
    ]
    
    for route in routes:
        if route in content:
            print(f"[PASS] Found route: {route}")
        else:
            print(f"[FAIL] Missing route: {route}")
            
except Exception as e:
    print(f"[FAIL] Error checking routes: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\n[INFO] MANUAL TESTING REQUIRED:")
print("  1. Login to http://127.0.0.1:5000")
print("  2. Look for project dropdown in navbar")
print("  3. Visit /projects to manage projects")
print("  4. Create, switch, rename, and delete projects")
print("=" * 60)
