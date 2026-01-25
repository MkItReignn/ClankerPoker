"""Mock transport for testing and front-end isolation."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType

from src.application.poker.events import PublishedEvent


class MockTransport:
    """Mock transport for testing and front-end development.

    Can optionally write events to a JSONL file for front-end testing.
    """

    def __init__(
        self,
        output_file: str | Path | None = None,
        store_events: bool = True,
    ) -> None:
        self._output_file = Path(output_file) if output_file else None
        self._store_events = store_events
        self._events: list[PublishedEvent] = []
        self._file_handle = None

        if self._output_file:
            self._output_file.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(self._output_file, "w", encoding="utf-8")

    async def __aenter__(self) -> "MockTransport":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    def __del__(self) -> None:
        if self._file_handle:
            self._file_handle.close()

    @property
    def events(self) -> list[PublishedEvent]:
        return self._events.copy()

    def get_events_by_type(self, event_type: str) -> list[PublishedEvent]:
        return [e for e in self._events if e.event_type == event_type]

    def clear(self) -> None:
        self._events.clear()

    async def publish(self, event: PublishedEvent) -> None:
        if self._store_events:
            self._events.append(event)

        if self._file_handle:
            json_line = json.dumps(event.to_dict(), default=str)
            self._file_handle.write(json_line + "\n")
            self._file_handle.flush()

    async def publish_batch(self, events: list[PublishedEvent]) -> None:
        for event in events:
            await self.publish(event)

    async def close(self) -> None:
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


class InMemoryTransport:
    """Simple in-memory transport for unit testing."""

    def __init__(self) -> None:
        self._events: list[PublishedEvent] = []

    @property
    def events(self) -> list[PublishedEvent]:
        return self._events.copy()

    @property
    def event_count(self) -> int:
        return len(self._events)

    def get_last_event(self) -> PublishedEvent | None:
        return self._events[-1] if self._events else None

    def get_events_by_type(self, event_type: str) -> list[PublishedEvent]:
        return [e for e in self._events if e.event_type == event_type]

    def clear(self) -> None:
        self._events.clear()

    async def publish(self, event: PublishedEvent) -> None:
        self._events.append(event)

    async def publish_batch(self, events: list[PublishedEvent]) -> None:
        self._events.extend(events)

    async def close(self) -> None:
        pass
