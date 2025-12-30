import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath('..'))

# Now import and run the app
from ui.app import app

if __name__ == "__main__":
    app.run(debug=True)
