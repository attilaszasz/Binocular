"""Short thread-safe start boundary. Never hold its lock across I/O or execution."""

from __future__ import annotations

from threading import Lock


class AutomaticSkipped(Exception):
    """Neutral automatic skip; not a failed scrape."""


class AutomaticAdmission:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[int, tuple[bool, int]] = {}

    def revision(self, module_id: int) -> int:
        with self._lock:
            return self._states.get(module_id, (False, 0))[1]

    def activate(self, module_id: int, expected: int | None = None) -> None:
        with self._lock:
            active, generation = self._states.get(module_id, (False, 0))
            if expected is not None and expected != generation:
                return
            if not active:
                self._states[module_id] = (True, generation + 1)

    def pause(self, module_id: int) -> None:
        with self._lock:
            _, generation = self._states.get(module_id, (False, 0))
            self._states[module_id] = (False, generation + 1)

    def ticket(self, module_id: int) -> int | None:
        with self._lock:
            active, generation = self._states.get(module_id, (False, 0))
            return generation if active else None

    def claim(self, module_id: int, generation: int) -> bool:
        with self._lock:
            return self._states.get(module_id) == (True, generation)
