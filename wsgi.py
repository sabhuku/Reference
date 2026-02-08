"""
PRODUCTION ENTRY POINT

This is the canonical WSGI entry point for production deployments.
For local development, use: run_flask.py

Security reviewers: This is the primary application entry point.
All production traffic flows through this module.
"""
import os
import sys

# Add the current directory to the Python path
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the src directory to the Python path
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import and run the app
from ui.app import app as application

if __name__ == "__main__":
    application.run(debug=True)
