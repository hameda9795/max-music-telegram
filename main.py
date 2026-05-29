import asyncio
import logging

from pyrogram import Client, idle
from pytgcalls import GroupCallFactory

from config import API_ID, API_HASH, BOT_TOKEN
from handlers.play import register

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions",
)


async def main() -> None:
    factory = GroupCallFactory(app)
    register(app, factory)
    await app.start()
    logging.info("Bot started successfully.")
    await idle()


if __name__ == "__main__":
    asyncio.run(main())
