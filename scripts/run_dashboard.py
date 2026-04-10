"""Dev launcher for the AlgoTrader web dashboard."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import uvicorn
from infrastructure.dashboard.web_ui import create_app

API_TOKEN = os.environ.get("DASHBOARD_TOKEN")
if not API_TOKEN:
    print("\n  ERROR: DASHBOARD_TOKEN not set in .env\n")
    sys.exit(1)

HOST = "127.0.0.1"
PORT = 8000

app = create_app(api_token=API_TOKEN)

if __name__ == "__main__":
    print(f"\n  ALGO TERMINAL  >>  http://{HOST}:{PORT}")
    print(f"  Token loaded from .env\n")
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
