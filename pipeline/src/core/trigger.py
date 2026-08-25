from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CooldownTracker:
    cooldown_seconds: float
    _last_fired: dict[int, float] = field(default_factory=dict)

    def can_fire(self, marker_id: int, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        last = self._last_fired.get(marker_id)
        if last is None:
            return True
        return (now - last) >= self.cooldown_seconds

    def mark_fired(self, marker_id: int, now: float | None = None) -> None:
        self._last_fired[marker_id] = now if now is not None else time.monotonic()

    def time_until_ready(self, marker_id: int, now: float | None = None) -> float:
        now = now if now is not None else time.monotonic()
        last = self._last_fired.get(marker_id)
        if last is None:
            return 0.0
        return max(0.0, self.cooldown_seconds - (now - last))
