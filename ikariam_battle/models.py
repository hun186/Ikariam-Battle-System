from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScenarioError(ValueError):
    pass


class Policy(str, Enum):
    STRICT = "strict"
    EXPERIMENTAL = "experimental"


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioError(f"{name} must be an object")
    return value


def _integer(value: Any, name: str, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        limit = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise ScenarioError(f"{name} must be {limit}")
    return value


@dataclass(frozen=True)
class ArmyUnit:
    unit_id: str
    quantity: int
    wave_id: str = "wave-1"

    @classmethod
    def from_dict(cls, value: Any) -> "ArmyUnit":
        row = _object(value, "army unit")
        if not isinstance(row.get("unit_id"), str) or not row["unit_id"]:
            raise ScenarioError("unit_id must be a non-empty string")
        wave_id = row.get("wave_id", "wave-1")
        if not isinstance(wave_id, str) or not wave_id:
            raise ScenarioError("wave_id must be a non-empty string")
        return cls(row["unit_id"], _integer(row.get("quantity"), "quantity"), wave_id)


@dataclass(frozen=True)
class Workshop:
    attack_level: int = 0
    armor_level: int = 0

    @classmethod
    def from_dict(cls, value: Any) -> "Workshop":
        data = _object(value, "workshop")
        return cls(_integer(data.get("attack_level", 0), "workshop.attack_level"),
                   _integer(data.get("armor_level", 0), "workshop.armor_level"))


@dataclass(frozen=True)
class Army:
    units: tuple[ArmyUnit, ...]
    workshop: Workshop = Workshop()
    forge_level: int = 0

    @classmethod
    def from_dict(cls, value: Any) -> "Army":
        data = _object(value, "army")
        raw = data.get("units")
        if not isinstance(raw, list) or not raw:
            raise ScenarioError("army.units must be a non-empty list")
        parsed = [ArmyUnit.from_dict(item) for item in raw]
        if not any(item.quantity for item in parsed):
            raise ScenarioError("an army must contain at least one unit")
        # A wave is identified by (unit_id, wave_id); duplicate UI/API rows are
        # presentation only and cannot change mechanics.
        totals: dict[tuple[str, str], int] = {}
        for item in parsed:
            key = (item.unit_id, item.wave_id)
            totals[key] = totals.get(key, 0) + item.quantity
        units = tuple(ArmyUnit(unit, quantity, wave) for (unit, wave), quantity in sorted(totals.items()))
        return cls(units, Workshop.from_dict(data.get("workshop", {})),
                   _integer(data.get("forge_level", 0), "forge_level", 0, 5))


@dataclass(frozen=True)
class Profiles:
    mechanics: str = "battle-system-paper-2020"
    unit_stats: str = "infinite-horizons-current"
    workshop: str = "v14-workshop"
    forge: str = "v14-hephaistos"
    support: str = "v17-support-healing"

    @classmethod
    def from_dict(cls, value: Any) -> "Profiles":
        data = _object(value, "profiles")
        result = cls(str(data.get("mechanics", cls.mechanics)), str(data.get("unit_stats", cls.unit_stats)),
                     str(data.get("workshop", cls.workshop)), str(data.get("forge", cls.forge)),
                     str(data.get("support", cls.support)))
        expected = cls()
        if result != expected:
            raise ScenarioError(f"only the current profile bundle is supported: {expected}")
        return result


@dataclass(frozen=True)
class Scenario:
    attacker: Army
    defender: Army
    profiles: Profiles = Profiles()
    policy: Policy = Policy.STRICT
    battlefield: str = "small-land"
    max_rounds: int = 10

    @classmethod
    def from_dict(cls, value: Any) -> "Scenario":
        data = _object(value, "request body")
        try:
            policy = Policy(data.get("policy", "strict"))
        except ValueError as exc:
            raise ScenarioError("policy must be strict or experimental") from exc
        battlefield = data.get("battlefield", "small-land")
        if not isinstance(battlefield, str) or battlefield not in {"small-land", "small-naval"}:
            raise ScenarioError("battlefield must be small-land or small-naval")
        try:
            return cls(Army.from_dict(data["attacker"]), Army.from_dict(data["defender"]),
                       Profiles.from_dict(data.get("profiles", {})), policy, battlefield,
                       _integer(data.get("max_rounds", 10), "max_rounds", 1, 100))
        except KeyError as exc:
            raise ScenarioError(f"missing field: {exc.args[0]}") from exc


@dataclass
class Slot:
    slot_id: str
    line: str
    physical_position: int
    damage_position: int
    unit_id: str
    wave_id: str
    units: int
    capacity: int
    damage: int = 0


@dataclass
class Wave:
    unit: ArmyUnit
    reserve: int
    slots: list[Slot] = field(default_factory=list)
    reserve_damage: int = 0
    ammo_remaining: int | None = None

    @property
    def alive(self) -> int:
        return self.reserve + sum(slot.units for slot in self.slots)
