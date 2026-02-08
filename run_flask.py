"""
DEVELOPMENT ENTRY POINT

This is the canonical entry point for local development.
For production deployments, use: wsgi.py

Runs Flask development server with debug mode enabled.
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('./src'))

# Now import and run the app
from ui.app import app

if __name__ == "__main__":
    app.run(debug=True)
