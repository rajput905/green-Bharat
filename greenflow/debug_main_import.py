import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import main.app...")
    from main import app
    print("SUCCESS: Imported main.app")
except Exception as e:
    import traceback
    print("FAILED: Exception during import")
    traceback.print_exc()
