from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    round: int
    phase: str
    type: str
    side: str | None
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"round": self.round, "phase": self.phase, "type": self.type, "side": self.side, "details": self.details}
