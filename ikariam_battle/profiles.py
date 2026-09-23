from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import files
import json


def _load(folder: str, name: str) -> dict:
    return json.loads(files(f"ikariam_battle.data.{folder}").joinpath(f"{name}.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class WorkshopProfile:
    land_increment: int
    naval_increment: int
    metadata: dict

    @classmethod
    def load(cls, name: str = "v14-workshop") -> "WorkshopProfile":
        raw = _load("rules", name)
        return cls(raw["increments"]["land"], raw["increments"]["naval"], raw["metadata"])

    def bonus(self, domain: str, level: int) -> int:
        return level * (self.land_increment if domain == "land" else self.naval_increment)


@dataclass(frozen=True)
class ForgeEffect:
    damage_multiplier: Decimal
    armor_bonus: int


class ForgeProfile:
    def __init__(self, levels: dict[int, ForgeEffect], metadata: dict):
        self.levels, self.metadata = levels, metadata

    @classmethod
    def load(cls, name: str = "v14-hephaistos") -> "ForgeProfile":
        raw = _load("rules", name)
        return cls({int(k): ForgeEffect(Decimal(str(v["damage_multiplier"])), v["armor_bonus"]) for k, v in raw["levels"].items()}, raw["metadata"])

    def effect(self, level: int) -> ForgeEffect:
        return self.levels[level]


class SupportProfile:
    def __init__(self, raw: dict): self.raw = raw
    @classmethod
    def load(cls, name: str = "v17-support-healing") -> "SupportProfile": return cls(_load("rules", name))
    @property
    def derived_capacity(self) -> int: return self.raw["legacy_capacity"] * self.raw["healing_capacity_multiplier"]
