import os
import sys

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import and run the app
from ui.app import app

if __name__ == "__main__":
    app.run(debug=True)
