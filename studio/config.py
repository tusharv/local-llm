from pathlib import Path

BIND_HOST = "127.0.0.1"
PORT = 8000
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "studio.db"
UPLOADS_DIR = DATA_DIR / "uploads"
ONBOARDING_PATH = DATA_DIR / "onboarding.json"
STUDIO_URL = f"http://{BIND_HOST}:{PORT}"
