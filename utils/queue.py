from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class Track:
    title: str
    path: str
    requested_by: str
    duration: Optional[int] = None


class QueueManager:
    """Per-chat queue with current-track tracking."""

    def __init__(self) -> None:
        self._queue: dict[int, deque[Track]] = {}
        self._current: dict[int, Optional[Track]] = {}

    def enqueue(self, chat_id: int, track: Track) -> int:
        """Add track to queue. Returns new queue length."""
        if chat_id not in self._queue:
            self._queue[chat_id] = deque()
        self._queue[chat_id].append(track)
        return len(self._queue[chat_id])

    def dequeue(self, chat_id: int) -> Optional[Track]:
        """Pop next track and set it as current. Returns None if queue empty."""
        q = self._queue.get(chat_id)
        if q:
            track = q.popleft()
            self._current[chat_id] = track
            return track
        self._current[chat_id] = None
        return None

    def current(self, chat_id: int) -> Optional[Track]:
        return self._current.get(chat_id)

    def list_queue(self, chat_id: int) -> list[Track]:
        return list(self._queue.get(chat_id, []))

    def clear(self, chat_id: int) -> None:
        self._queue[chat_id] = deque()
        self._current[chat_id] = None


queue = QueueManager()
