"""
Run once on the server to generate USER_SESSION string.
Usage: python setup_session.py
Then copy the printed string to .env as USER_SESSION=...
"""
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

from pyrogram import Client

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE = os.environ.get("PHONE", "")

async def main():
    print("Logging in with phone number:", PHONE)
    async with Client(":memory:", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE) as app:
        session_string = await app.export_session_string()
        print("\n\n=== COPY THIS LINE TO .env ===")
        print(f"USER_SESSION={session_string}")
        print("==============================\n")

asyncio.run(main())
