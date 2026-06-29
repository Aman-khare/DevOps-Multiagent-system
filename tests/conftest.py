import os
import tempfile
from pathlib import Path

TMP_DIR = Path(tempfile.gettempdir())
TMP_DIR.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH = TMP_DIR / f"devops_ai_architect_test_{os.getpid()}.db"

os.environ["APP_ENV"] = "test"
os.environ["DRY_RUN"] = "true"
os.environ["AGENT_PIPELINE_ENABLED"] = "false"
os.environ["DEVOPS_AI_DB_PATH"] = str(TEST_DB_PATH)
os.environ["WEBHOOK_SECRET"] = ""  # Disable webhook auth for tests

try:
    TEST_DB_PATH.unlink()
except FileNotFoundError:
    pass