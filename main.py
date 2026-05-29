import logging
import asyncio

from pyrogram import Client, idle
from pytgcalls import GroupCallFactory

from config import API_ID, API_HASH, BOT_TOKEN, PHONE
from handlers.play import register

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Bot client: receives commands, sends messages
bot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions",
)

# User client: joins voice chat (must have session file from setup_session.py)
user = Client(
    "UserClient",
    api_id=API_ID,
    api_hash=API_HASH,
    phone_number=PHONE,
    workdir="sessions",
)

factory = GroupCallFactory(user)
register(bot, factory)


async def main() -> None:
    await user.start()
    me = await user.get_me()
    logging.info("User client: %s (@%s)", me.first_name, me.username)

    await bot.start()
    logging.info("Bot started successfully.")

    await idle()

    await bot.stop()
    await user.stop()


if __name__ == "__main__":
    asyncio.run(main())
