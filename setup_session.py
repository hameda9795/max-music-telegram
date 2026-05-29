"""
Run once to generate USER_SESSION string.
Usage: python setup_session.py CODE
Example: python setup_session.py 12345
"""
import asyncio
import sys
from dotenv import load_dotenv
import os

load_dotenv()

from pyrogram import Client

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE = os.environ.get("PHONE", "")


async def main(code: str):
    app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE)
    await app.connect()
    sent = await app.send_code(PHONE)
    signed_in = await app.sign_in(PHONE, sent.phone_code_hash, code)
    session_string = await app.export_session_string()
    await app.disconnect()
    print("\n=== COPY THIS LINE TO .env ===")
    print(f"USER_SESSION={session_string}")
    print("==============================\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_session.py CODE")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
