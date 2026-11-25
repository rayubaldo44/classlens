"""Keyed process-local locks that retain entries only while referenced."""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from threading import Lock, RLock


@dataclass
class _SyncEntry:
    lock: RLock = field(default_factory=RLock)
    users: int = 0


class SyncKeyedLocks:
    def __init__(self) -> None:
        self._entries: dict[str, _SyncEntry] = {}
        self._guard = Lock()

    def __len__(self) -> int:
        with self._guard:
            return len(self._entries)

    @contextmanager
    def hold(self, key: str):
        with self._guard:
            entry = self._entries.setdefault(key, _SyncEntry())
            entry.users += 1
        try:
            with entry.lock:
                yield
        finally:
            with self._guard:
                entry.users -= 1
                if entry.users == 0:
                    del self._entries[key]


@dataclass
class _AsyncEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class AsyncKeyedLocks:
    def __init__(self) -> None:
        self._entries: dict[tuple[asyncio.AbstractEventLoop, str], _AsyncEntry] = {}
        self._guard = Lock()

    def __len__(self) -> int:
        with self._guard:
            return len(self._entries)

    @asynccontextmanager
    async def hold(self, key: str):
        scoped_key = (asyncio.get_running_loop(), key)
        with self._guard:
            entry = self._entries.setdefault(scoped_key, _AsyncEntry())
            entry.users += 1
        try:
            async with entry.lock:
                yield
        finally:
            with self._guard:
                entry.users -= 1
                if entry.users == 0:
                    del self._entries[scoped_key]
