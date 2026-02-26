import sys
from pathlib import Path

# Add the greenflow directory to sys.path so we can import from it
sys.path.append(str(Path(__file__).parent / "greenflow"))

from greenflow.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
