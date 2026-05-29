"""
Play handler — registers all bot commands for the music bot.

Supported commands (with or without leading /):
  پخش [query|url]      — play a song (search YouTube or direct link)
  پخش                  — (reply to audio/video) play the replied file
  توقف                 — stop playback and leave voice chat
  رد                   — skip current track
  پخش_دوباره           — restart current track from the beginning
  صف                   — show current queue
  راهنما               — show help message
"""

import logging
import os
import re
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

# ── pytgcalls compatibility shim ────────────────────────────────────────────
# pytgcalls v3.x uses AudioPiped; v4.x (ntgcalls) uses MediaStream.
try:
    from pytgcalls.types.input_stream import AudioPiped as _StreamType  # v3.x

    def _make_stream(path: str):
        return _StreamType(path)

except ImportError:
    from pytgcalls.types import MediaStream as _StreamType  # v4.x

    def _make_stream(path: str):
        return _StreamType(path)

from pytgcalls import PyTgCalls

try:
    from pytgcalls.exceptions import (
        AlreadyJoinedError,
        GroupCallNotFound,
        NoActiveGroupCall,
    )
except ImportError:
    # Fallback if exception names changed between versions
    AlreadyJoinedError = Exception
    GroupCallNotFound = Exception
    NoActiveGroupCall = Exception

from utils.queue import Track, queue
from utils import ytdl

logger = logging.getLogger(__name__)

# ── Regex patterns for commands ──────────────────────────────────────────────
_PLAY_RE = re.compile(r"^[/]?(پخش|play)\s*(.*)", re.I | re.S)
_STOP_RE = re.compile(r"^[/]?(توقف|stop)\s*$", re.I)
_SKIP_RE = re.compile(r"^[/]?(رد|skip)\s*$", re.I)
_REPLAY_RE = re.compile(r"^[/]?(پخش_دوباره|replay)\s*$", re.I)
_QUEUE_RE = re.compile(r"^[/]?(صف|queue)\s*$", re.I)
_HELP_RE = re.compile(r"^[/]?(راهنما|help)\s*$", re.I)


def _fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


async def _command_filter_func(_, __, message: Message) -> bool:
    text = (message.text or "").strip()
    return bool(
        _PLAY_RE.match(text)
        or _STOP_RE.match(text)
        or _SKIP_RE.match(text)
        or _REPLAY_RE.match(text)
        or _QUEUE_RE.match(text)
        or _HELP_RE.match(text)
    )


_command_filter = filters.create(_command_filter_func)


def register(app: Client, call: PyTgCalls) -> None:
    """Register all handlers on the pyrogram Client and pytgcalls instance."""

    # ── Stream-end auto-play ─────────────────────────────────────────────
    @call.on_stream_end()
    async def _on_stream_end(_, update) -> None:
        chat_id = update.chat_id
        next_track = queue.dequeue(chat_id)
        if next_track:
            try:
                await call.change_stream(chat_id, _make_stream(next_track.path))
                dur = _fmt_duration(next_track.duration)
                await app.send_message(
                    chat_id,
                    f"▶️ **{next_track.title}**"
                    + (f"\n⏱ {dur}" if dur else "")
                    + f"\n👤 {next_track.requested_by}",
                )
            except Exception as exc:
                logger.error("Error advancing queue in chat %s: %s", chat_id, exc)
        else:
            try:
                await call.leave_group_call(chat_id)
            except Exception:
                pass
            try:
                await app.send_message(chat_id, "✅ صف پخش تمام شد.")
            except Exception:
                pass

    # ── Message dispatcher ───────────────────────────────────────────────
    @app.on_message(filters.group & filters.text & _command_filter)
    async def _on_command(client: Client, message: Message) -> None:
        text = (message.text or "").strip()
        if _PLAY_RE.match(text):
            await _play(client, message, call)
        elif _STOP_RE.match(text):
            await _stop(message, call)
        elif _SKIP_RE.match(text):
            await _skip(message, call)
        elif _REPLAY_RE.match(text):
            await _replay(message, call)
        elif _QUEUE_RE.match(text):
            await _show_queue(message)
        elif _HELP_RE.match(text):
            await _help(message)


# ── Command implementations ──────────────────────────────────────────────────

async def _play(client: Client, message: Message, call: PyTgCalls) -> None:
    chat_id = message.chat.id
    user = message.from_user.first_name if message.from_user else "کاربر"
    text = (message.text or "").strip()
    m = _PLAY_RE.match(text)
    arg = m.group(2).strip() if m else ""

    # ── Case 1: Reply to an audio / voice / video file ───────────────────
    replied = message.reply_to_message
    if replied and (replied.audio or replied.voice or replied.video_note or replied.video):
        status = await message.reply("⏳ در حال دانلود فایل...")
        media = replied.audio or replied.voice or replied.video_note or replied.video
        try:
            file_path = await client.download_media(
                media, file_name=os.path.join("downloads", f"{media.file_id}.mp3")
            )
            title = (
                getattr(replied.audio, "title", None)
                or getattr(replied.audio, "file_name", None)
                or getattr(replied.video, "file_name", None)
                or "فایل صوتی"
            )
            duration = getattr(media, "duration", None)
            track = Track(title=title, path=file_path, requested_by=user, duration=duration)
            await _enqueue_and_play(call, message, chat_id, track, status)
        except Exception as exc:
            await status.edit(f"❌ خطا در دانلود فایل: {exc}")
        return

    # ── Case 2: No argument provided ────────────────────────────────────
    if not arg:
        await message.reply(
            "❓ لطفاً نام آهنگ یا لینک یوتیوب وارد کنید، یا روی یک فایل صوتی ریپلای کنید.\n\n"
            "📖 مثال‌ها:\n"
            "`پخش شادمهر عقیلی دلتنگی`\n"
            "`پخش https://youtu.be/...`"
        )
        return

    # ── Case 3: YouTube URL or search query ──────────────────────────────
    if ytdl.is_youtube_url(arg):
        status = await message.reply("⏳ در حال دانلود از یوتیوب...")
    else:
        status = await message.reply("🔍 در حال جستجو در یوتیوب...")

    try:
        info = await ytdl.fetch(arg)
        track = Track(
            title=info["title"],
            path=info["path"],
            requested_by=user,
            duration=info.get("duration"),
        )
        await _enqueue_and_play(call, message, chat_id, track, status)
    except Exception as exc:
        logger.error("Download error for query %r: %s", arg, exc)
        await status.edit(f"❌ خطا در دانلود: {exc}")


async def _enqueue_and_play(
    call: PyTgCalls,
    message: Message,
    chat_id: int,
    track: Track,
    status_msg,
) -> None:
    current = queue.current(chat_id)
    queue.enqueue(chat_id, track)

    if current is None:
        # Nothing is playing — start immediately
        next_track = queue.dequeue(chat_id)
        try:
            try:
                await call.join_group_call(chat_id, _make_stream(next_track.path))
            except AlreadyJoinedError:
                await call.change_stream(chat_id, _make_stream(next_track.path))

            dur = _fmt_duration(next_track.duration)
            await status_msg.edit(
                f"▶️ در حال پخش: **{next_track.title}**"
                + (f"\n⏱ {dur}" if dur else "")
                + f"\n👤 {next_track.requested_by}"
            )
        except NoActiveGroupCall:
            queue.clear(chat_id)
            await status_msg.edit(
                "❌ هیچ ویدیو کالی فعال نیست.\n"
                "لطفاً ابتدا یک **ویدیو کال** در گروه شروع کنید و سپس دستور پخش را بزنید."
            )
        except Exception as exc:
            queue.clear(chat_id)
            logger.error("join_group_call error in chat %s: %s", chat_id, exc)
            await status_msg.edit(f"❌ خطا در اتصال به ویدیو کال: {exc}")
    else:
        pos = len(queue.list_queue(chat_id))
        await status_msg.edit(
            f"✅ به صف اضافه شد: **{track.title}**\n"
            f"📍 موقعیت در صف: {pos}"
        )


async def _stop(message: Message, call: PyTgCalls) -> None:
    chat_id = message.chat.id
    queue.clear(chat_id)
    try:
        await call.leave_group_call(chat_id)
        await message.reply("⏹ پخش متوقف شد و ربات از ویدیو کال خارج شد.")
    except (NoActiveGroupCall, GroupCallNotFound):
        await message.reply("⏹ ربات در ویدیو کال نیست.")
    except Exception as exc:
        await message.reply(f"❌ خطا: {exc}")


async def _skip(message: Message, call: PyTgCalls) -> None:
    chat_id = message.chat.id
    next_track = queue.dequeue(chat_id)
    if next_track:
        try:
            await call.change_stream(chat_id, _make_stream(next_track.path))
            dur = _fmt_duration(next_track.duration)
            await message.reply(
                f"⏭ آهنگ بعدی: **{next_track.title}**"
                + (f"\n⏱ {dur}" if dur else "")
                + f"\n👤 {next_track.requested_by}"
            )
        except Exception as exc:
            await message.reply(f"❌ خطا: {exc}")
    else:
        try:
            await call.leave_group_call(chat_id)
        except Exception:
            pass
        await message.reply("✅ صف خالی است. پخش متوقف شد.")


async def _replay(message: Message, call: PyTgCalls) -> None:
    chat_id = message.chat.id
    current = queue.current(chat_id)
    if not current:
        await message.reply("❌ هیچ آهنگی در حال پخش نیست.")
        return
    try:
        await call.change_stream(chat_id, _make_stream(current.path))
        await message.reply(f"🔁 پخش دوباره: **{current.title}**")
    except Exception as exc:
        await message.reply(f"❌ خطا: {exc}")


async def _show_queue(message: Message) -> None:
    chat_id = message.chat.id
    current = queue.current(chat_id)
    items = queue.list_queue(chat_id)

    if not current and not items:
        await message.reply("📭 صف پخش خالی است.")
        return

    lines = ["🎵 **صف پخش:**\n"]
    if current:
        dur = _fmt_duration(current.duration)
        lines.append(f"▶️ **در حال پخش:** {current.title}" + (f" ({dur})" if dur else ""))

    if items:
        lines.append("\n📋 **بعدی‌ها:**")
        for i, t in enumerate(items, 1):
            dur = _fmt_duration(t.duration)
            lines.append(f"{i}. {t.title}" + (f" ({dur})" if dur else ""))

    await message.reply("\n".join(lines))


async def _help(message: Message) -> None:
    await message.reply(
        "🤖 **ربات موزیک گروه**\n\n"
        "**دستورات:**\n"
        "▶️ `پخش [نام آهنگ]` — جستجو در یوتیوب و پخش در ویدیو کال\n"
        "▶️ `پخش [لینک یوتیوب]` — پخش مستقیم از یوتیوب\n"
        "▶️ `پخش` (ریپلای روی فایل) — پخش فایل صوتی/موزیک ارسال‌شده\n"
        "⏭ `رد` — رد کردن آهنگ فعلی و رفتن به بعدی\n"
        "⏹ `توقف` — توقف کامل پخش\n"
        "🔁 `پخش_دوباره` — پخش دوباره آهنگ فعلی از ابتدا\n"
        "📋 `صف` — نمایش صف پخش\n"
        "❓ `راهنما` — نمایش این پیام\n\n"
        "⚠️ **نکته:** برای استفاده، باید یک **ویدیو کال** فعال در گروه وجود داشته باشد."
    )
