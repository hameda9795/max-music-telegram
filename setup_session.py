"""
Run this ONCE on the server to create the user session for voice chat.
The session file will be saved to sessions/UserClient.session
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
    client = Client(
        "UserClient",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE,
        workdir="sessions",
    )
    async with client:
        me = await client.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username})")
        print("Session saved to sessions/UserClient.session")

asyncio.run(main())
