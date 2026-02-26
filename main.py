"""
main.py — GreenFlow AI Application Entry Point
================================================
This file launches the FastAPI application located in greenflow/main.py.
Run from the project root with:

    uvicorn greenflow.main:app --reload --host 0.0.0.0 --port 8000

Or simply:
    python main.py
"""

import sys
import uvicorn
from pathlib import Path

# Ensure the project root is in Python's module search path
sys.path.insert(0, str(Path(__file__).parent))

# Import the FastAPI app from the greenflow package
from greenflow.main import app  # noqa: F401  (re-exported for uvicorn)


if __name__ == "__main__":
    uvicorn.run(
        "greenflow.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
