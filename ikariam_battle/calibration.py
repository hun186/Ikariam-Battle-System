from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Scenario, ScenarioError, _integer, _object


@dataclass(frozen=True)
class ObservedSlot:
    side: str
    line: str
    damage_position: int
    casualties: int | None = None
    damage_percent: int | None = None
    life_percent: int | None = None


@dataclass(frozen=True)
class BattleReportFixture:
    game_version: str
    round_number: int
    scenario: Scenario
    observations: tuple[ObservedSlot, ...]

    @classmethod
    def from_dict(cls, value: Any) -> "BattleReportFixture":
        data = _object(value, "calibration fixture")
        if not isinstance(data.get("game_version"), str): raise ScenarioError("game_version must be a string")
        observations = []
        raw = data.get("observations")
        if not isinstance(raw, list): raise ScenarioError("observations must be a list")
        for item in raw:
            row = _object(item, "observation")
            observations.append(ObservedSlot(str(row["side"]), str(row["line"]),
                _integer(row["damage_position"], "damage_position", 1),
                None if "casualties" not in row else _integer(row["casualties"], "casualties"),
                None if "damage_percent" not in row else _integer(row["damage_percent"], "damage_percent",0,100),
                None if "life_percent" not in row else _integer(row["life_percent"], "life_percent",0,100)))
        return cls(data["game_version"], _integer(data["round_number"], "round_number",1),
                   Scenario.from_dict(data["scenario"]), tuple(observations))


def damage_interval_from_report(percent: int, alive_hit_points: int) -> tuple[int, int]:
    """Integer interval compatible with an observed damage percentage rounded up."""
    if not 0 <= percent <= 100 or alive_hit_points < 0: raise ValueError("invalid percentage/HP")
    if percent == 0: return (0, 0)
    lower = ((percent - 1) * alive_hit_points) // 100 + 1
    upper = (percent * alive_hit_points) // 100
    return lower, upper
