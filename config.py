import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

API_ID: int = int(os.environ["API_ID"])
API_HASH: str = os.environ["API_HASH"]
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
PHONE: str = os.getenv("PHONE", "")
USER_SESSION: str = os.getenv("USER_SESSION", "")

DOWNLOADS_DIR: str = os.getenv("DOWNLOADS_DIR", "downloads")
pathlib.Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)
