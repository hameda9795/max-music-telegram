"""
Play handler -- uses pytgcalls GroupCallFactory API (MarshalX, v3.0.0.dev).

Exported API of the installed package:
  GroupCallFactory(client)            -- factory bound to an MTProto client
  factory.get_file_group_call(path)   -- creates a GroupCallFileAction instance
  call.start(chat_id)                 -- join voice chat and begin playback
  call.stop()                         -- leave voice chat
  call.input_filename = path          -- hot-swap the playing file
  @call.on_playout_ended              -- fired when the current file finishes
"""

import asyncio
import logging
import os
import re
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import GroupCallFactory

from utils.queue import Track, queue
from utils import ytdl

logger = logging.getLogger(__name__)

_PLAY_RE   = re.compile(r"^[/]?(پخش|play)\s*(.*)",      re.IGNORECASE | re.DOTALL)
_STOP_RE   = re.compile(r"^[/]?(توقف|stop)\s*$",        re.IGNORECASE)
_SKIP_RE   = re.compile(r"^[/]?(رد|skip)\s*$",           re.IGNORECASE)
_REPLAY_RE = re.compile(r"^[/]?(پخش_دوباره|replay)\s*$", re.IGNORECASE)
_QUEUE_RE  = re.compile(r"^[/]?(صف|queue)\s*$",          re.IGNORECASE)
_HELP_RE   = re.compile(r"^[/]?(راهنما|help)\s*$",       re.IGNORECASE)


def _fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


async def _command_filter_func(_, __, message: Message) -> bool:
    text = (message.text or "").strip()
    return bool(
        _PLAY_RE.match(text) or _STOP_RE.match(text) or _SKIP_RE.match(text)
        or _REPLAY_RE.match(text) or _QUEUE_RE.match(text) or _HELP_RE.match(text)
    )


_command_filter = filters.create(_command_filter_func)


class CallManager:
    """Manages one GroupCallFileAction instance per active chat."""

    def __init__(self, app: Client, factory: GroupCallFactory) -> None:
        self._app = app
        self._factory = factory
        self._calls: dict = {}

    def is_active(self, chat_id: int) -> bool:
        return chat_id in self._calls

    async def join_and_play(self, chat_id: int, file_path: str) -> None:
        if chat_id in self._calls:
            self._calls[chat_id].input_filename = file_path
        else:
            call = self._factory.get_file_group_call(file_path)
            self._calls[chat_id] = call

            @call.on_playout_ended
            def _on_ended(context, source):
                asyncio.ensure_future(self._advance_queue(chat_id))

            await call.start(chat_id)

    async def change_stream(self, chat_id: int, file_path: str) -> bool:
        if chat_id not in self._calls:
            return False
        self._calls[chat_id].input_filename = file_path
        return True

    async def leave(self, chat_id: int) -> None:
        if chat_id in self._calls:
            try:
                await self._calls[chat_id].stop()
            except Exception:
                pass
            del self._calls[chat_id]

    async def _advance_queue(self, chat_id: int) -> None:
        next_track = queue.dequeue(chat_id)
        if next_track:
            try:
                self._calls[chat_id].input_filename = next_track.path
                dur = _fmt_duration(next_track.duration)
                await self._app.send_message(
                    chat_id,
                    f"*{next_track.title}*"
                    + (f"\n{dur}" if dur else "")
                    + f"\n{next_track.requested_by}",
                )
            except Exception as exc:
                logger.error("Error advancing queue in chat %s: %s", chat_id, exc)
        else:
            await self.leave(chat_id)
            try:
                await self._app.send_message(chat_id, "صف پخش تمام شد.")
            except Exception:
                pass


def register(app: Client, factory: GroupCallFactory) -> None:
    manager = CallManager(app, factory)

    @app.on_message(filters.command("ping"))
    async def _ping(client: Client, message: Message) -> None:
        await message.reply("pong! ربات فعال است.")

    @app.on_message()
    async def _debug_log(client: Client, message: Message) -> None:
        text = (message.text or message.caption or "").strip()
        logger.info("MSG chat=%s type=%s text=%r", message.chat.id, message.chat.type, text[:80])

    @app.on_message(filters.group & filters.text)
    async def _group_text_test(client: Client, message: Message) -> None:
        text = (message.text or "").strip()
        matched = bool(_PLAY_RE.match(text) or _STOP_RE.match(text) or _SKIP_RE.match(text))
        logger.info("GROUP_TEXT chat=%s text=%r filter_match=%s", message.chat.id, text[:40], matched)

    @app.on_message(filters.group & filters.text & _command_filter)
    async def _on_command(client: Client, message: Message) -> None:
        logger.info("CMD from %s: %r", message.chat.id, (message.text or "")[:60])
        text = (message.text or "").strip()
        if _PLAY_RE.match(text):
            await _play(client, message, manager)
        elif _STOP_RE.match(text):
            await _stop(message, manager)
        elif _SKIP_RE.match(text):
            await _skip(message, manager)
        elif _REPLAY_RE.match(text):
            await _replay(message, manager)
        elif _QUEUE_RE.match(text):
            await _show_queue(message)
        elif _HELP_RE.match(text):
            await _help(message)


async def _play(client: Client, message: Message, manager: CallManager) -> None:
    chat_id = message.chat.id
    user = message.from_user.first_name if message.from_user else "کاربر"
    text = (message.text or "").strip()
    m = _PLAY_RE.match(text)
    arg = m.group(2).strip() if m else ""

    replied = message.reply_to_message
    if replied and (replied.audio or replied.voice or replied.video_note or replied.video):
        status = await message.reply("در حال دانلود فایل...")
        media = replied.audio or replied.voice or replied.video_note or replied.video
        try:
            file_path = await client.download_media(
                media, file_name=os.path.join("downloads", f"{media.file_id}.mp3")
            )
            title = (
                getattr(replied.audio, "title", None)
                or getattr(replied.audio, "file_name", None)
                or "فایل صوتی"
            )
            duration = getattr(media, "duration", None)
            track = Track(title=title, path=file_path, requested_by=user, duration=duration)
            await _enqueue_and_play(manager, message, chat_id, track, status)
        except Exception as exc:
            await status.edit_text(f"خطا در دانلود فایل: {exc}")
        return

    if not arg:
        await message.reply(
            "لطفا نام آهنگ یا لینک یوتیوب وارد کنید.\n\n"
            "مثال:\nپخش شادمهر عقیلی\nپخش https://youtu.be/..."
        )
        return

    status = await message.reply(
        "در حال دانلود از یوتیوب..." if ytdl.is_youtube_url(arg)
        else "در حال جستجو در یوتیوب..."
    )
    try:
        info = await ytdl.fetch(arg)
        track = Track(
            title=info["title"],
            path=info["path"],
            requested_by=user,
            duration=info.get("duration"),
        )
        await _enqueue_and_play(manager, message, chat_id, track, status)
    except Exception as exc:
        logger.error("Download error for %r: %s", arg, exc)
        await status.edit(f"خطا در دانلود: {exc}")


async def _enqueue_and_play(manager, message, chat_id, track, status_msg) -> None:
    current = queue.current(chat_id)
    queue.enqueue(chat_id, track)

    if current is None:
        next_track = queue.dequeue(chat_id)
        try:
            await manager.join_and_play(chat_id, next_track.path)
            dur = _fmt_duration(next_track.duration)
            await status_msg.edit(
                f"در حال پخش: {next_track.title}"
                + (f"\n{dur}" if dur else "")
                + f"\n{next_track.requested_by}"
            )
        except Exception as exc:
            queue.clear(chat_id)
            err = str(exc).lower()
            if any(k in err for k in ("no active", "not found", "not started")):
                await status_msg.edit(
                    "هیچ ویدیو کالی فعال نیست.\n"
                    "لطفا ابتدا یک ویدیو کال در گروه شروع کنید."
                )
            else:
                logger.error("join_and_play error in chat %s: %s", chat_id, exc)
                await status_msg.edit(f"خطا در اتصال به ویدیو کال: {exc}")
    else:
        pos = len(queue.list_queue(chat_id))
        await status_msg.edit(
            f"به صف اضافه شد: {track.title}\nموقعیت در صف: {pos}"
        )


async def _stop(message: Message, manager: CallManager) -> None:
    queue.clear(message.chat.id)
    await manager.leave(message.chat.id)
    await message.reply("پخش متوقف شد.")


async def _skip(message: Message, manager: CallManager) -> None:
    chat_id = message.chat.id
    next_track = queue.dequeue(chat_id)
    if next_track:
        ok = await manager.change_stream(chat_id, next_track.path)
        if ok:
            dur = _fmt_duration(next_track.duration)
            await message.reply(
                f"آهنگ بعدی: {next_track.title}"
                + (f"\n{dur}" if dur else "")
                + f"\n{next_track.requested_by}"
            )
        else:
            await message.reply("ربات در ویدیو کال نیست.")
    else:
        await manager.leave(chat_id)
        await message.reply("صف خالی است. پخش متوقف شد.")


async def _replay(message: Message, manager: CallManager) -> None:
    chat_id = message.chat.id
    current = queue.current(chat_id)
    if not current:
        await message.reply("هیچ آهنگی در حال پخش نیست.")
        return
    ok = await manager.change_stream(chat_id, current.path)
    if ok:
        await message.reply(f"پخش دوباره: {current.title}")
    else:
        await message.reply("ربات در ویدیو کال نیست.")


async def _show_queue(message: Message) -> None:
    chat_id = message.chat.id
    current = queue.current(chat_id)
    items = queue.list_queue(chat_id)
    if not current and not items:
        await message.reply("صف پخش خالی است.")
        return
    lines = ["صف پخش:\n"]
    if current:
        dur = _fmt_duration(current.duration)
        lines.append(f"در حال پخش: {current.title}" + (f" ({dur})" if dur else ""))
    if items:
        lines.append("\nبعدیها:")
        for i, t in enumerate(items, 1):
            dur = _fmt_duration(t.duration)
            lines.append(f"{i}. {t.title}" + (f" ({dur})" if dur else ""))
    await message.reply("\n".join(lines))


async def _help(message: Message) -> None:
    await message.reply(
        "ربات موزیک گروه\n\n"
        "دستورات:\n"
        "پخش [نام آهنگ] - جستجو در یوتیوب و پخش\n"
        "پخش [لینک یوتیوب] - پخش مستقیم\n"
        "پخش (ریپلای روی فایل) - پخش فایل صوتی\n"
        "رد - رد کردن آهنگ فعلی\n"
        "توقف - توقف کامل پخش\n"
        "پخش_دوباره - پخش دوباره آهنگ فعلی\n"
        "صف - نمایش صف پخش\n"
        "راهنما - نمایش این پیام\n\n"
        "نکته: ابتدا باید یک ویدیو کال فعال در گروه وجود داشته باشد."
    )
