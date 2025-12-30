import os
import sys

# Get the absolute path of the current directory
current_dir = os.path.abspath('.')

# Add the current directory and src directory to the Python path
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))

# Set the PYTHONPATH environment variable
os.environ['PYTHONPATH'] = os.pathsep.join([current_dir, os.path.join(current_dir, 'src')])

# Now import and run the app
from ui.app import app

if __name__ == "__main__":
    print("Starting the application...")
    print(f"Current Python path: {sys.path}")
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting the application: {e}")
