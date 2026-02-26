import sys
import os

# Add the current directory to sys.path to simulate being in the greenflow root
sys.path.append(os.getcwd())

try:
    from database.session import SystemAlert
    print("SUCCESS: Imported SystemAlert")
except ImportError as e:
    print(f"FAILED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
