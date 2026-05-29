import logging

from pyrogram import Client
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

factory = GroupCallFactory(app)
register(app, factory)

logging.info("Bot started successfully.")
app.run()
