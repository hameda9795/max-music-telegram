import asyncio
import os
import re
from typing import Optional, TypedDict

import yt_dlp

from config import DOWNLOADS_DIR

_YT_REGEX = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)[\w\-?=&%+#]+",
    re.IGNORECASE,
)


class TrackInfo(TypedDict):
    title: str
    duration: Optional[int]
    path: str


def is_youtube_url(text: str) -> bool:
    return bool(_YT_REGEX.search(text))


def _build_ydl_opts() -> dict:
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }


def _extract(url_or_query: str) -> TrackInfo:
    opts = _build_ydl_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url_or_query, download=True)
        if "entries" in info:
            info = info["entries"][0]
        path = os.path.join(DOWNLOADS_DIR, f"{info['id']}.mp3")
        return {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration"),
            "path": path,
        }


async def fetch(query: str) -> TrackInfo:
    """Download audio from a YouTube URL or search query."""
    url = query if is_youtube_url(query) else f"ytsearch1:{query}"
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract, url)
