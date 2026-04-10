"""Dev launcher for the AlgoTrader web dashboard."""
import uvicorn
from infrastructure.dashboard.web_ui import create_app

# ── configure here for dev ──
API_TOKEN = "dev-token"   # change before production
HOST = "127.0.0.1"
PORT = 8000

app = create_app(api_token=API_TOKEN)

if __name__ == "__main__":
    print(f"\n  ALGO TERMINAL  →  http://{HOST}:{PORT}")
    print(f"  Token: {API_TOKEN}\n")
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
