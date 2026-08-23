from __future__ import annotations

import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any


class LocalEventBus:
    def __init__(self, capacity: int = 500) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._sequence = 0
        self._lock = threading.Lock()

    def publish(self, event_type: str, project_id: str | None, payload: dict[str, Any]) -> int:
        with self._lock:
            self._sequence += 1
            self._events.append(
                {
                    "sequence": self._sequence,
                    "event_type": event_type,
                    "project_id": project_id,
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "payload": payload,
                }
            )
            return self._sequence

    def after(self, sequence: int, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [event.copy() for event in self._events if event["sequence"] > sequence][:limit]
