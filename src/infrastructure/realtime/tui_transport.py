from __future__ import annotations

import asyncio

from src.application.poker.events import PublishedEvent


class TuiEventTransport:
    """Queue-based transport for TUI consumption.

    Implements EventTransport protocol. Publishes events to an asyncio.Queue
    that the PokerViewerApp consumes in its event loop.

    Uses None as a sentinel value to signal end of event stream.
    """

    def __init__(self, queue: asyncio.Queue[PublishedEvent | None]) -> None:
        self._queue: asyncio.Queue[PublishedEvent | None] = queue
        self._closed: bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def publish(self, event: PublishedEvent) -> None:
        if not self._closed:
            await self._queue.put(event)

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._queue.put(None)
