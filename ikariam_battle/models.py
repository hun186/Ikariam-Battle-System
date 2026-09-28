from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


DEFAULT_MAX_ROUNDS = 100
MAX_ROUNDS = 1000


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
    attack_upgrade: int = 0
    armor_upgrade: int = 0
    # entry_batch_id is the real arrival-group identity: different unit types may
    # share it when they enter the battle together. wave_id remains the
    # unit-specific state identity used for ammo/damage ownership.
    entry_batch_id: str | None = None
    arrival_round: int = 0

    @property
    def batch_id(self) -> str:
        return self.entry_batch_id or self.wave_id

    @classmethod
    def from_dict(cls, value: Any) -> "ArmyUnit":
        row = _object(value, "army unit")
        if not isinstance(row.get("unit_id"), str) or not row["unit_id"]:
            raise ScenarioError("unit_id must be a non-empty string")
        explicit_wave = row.get("wave_id")
        entry_batch_id = row.get("entry_batch_id", explicit_wave or "batch-1")
        if not isinstance(entry_batch_id, str) or not entry_batch_id:
            raise ScenarioError("entry_batch_id must be a non-empty string")
        wave_id = explicit_wave or f"{entry_batch_id}::{row['unit_id']}"
        if not isinstance(wave_id, str) or not wave_id:
            raise ScenarioError("wave_id must be a non-empty string")
        return cls(row["unit_id"], _integer(row.get("quantity"), "quantity"), wave_id,
                   _integer(row.get("attack_upgrade", 0), "attack_upgrade"),
                   _integer(row.get("armor_upgrade", 0), "armor_upgrade"),
                   entry_batch_id,
                   _integer(row.get("arrival_round", 0), "arrival_round", 0, MAX_ROUNDS))


@dataclass(frozen=True)
class Army:
    units: tuple[ArmyUnit, ...]
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
        upgrades: dict[str, tuple[int, int]] = {}
        batch_rounds: dict[str, int] = {}
        for item in parsed:
            pair = (item.attack_upgrade, item.armor_upgrade)
            if item.unit_id in upgrades and upgrades[item.unit_id] != pair:
                raise ScenarioError(f"conflicting Workshop upgrades for {item.unit_id}")
            upgrades[item.unit_id] = pair
            if item.batch_id in batch_rounds and batch_rounds[item.batch_id] != item.arrival_round:
                raise ScenarioError(f"entry batch {item.batch_id} has conflicting arrival_round values")
            batch_rounds[item.batch_id] = item.arrival_round
        # State is unit-specific even when multiple unit types share one arrival
        # batch. Duplicate presentation rows aggregate only when both identities
        # and upgrades/timing agree.
        totals: dict[tuple[str, str, int, int, str, int], int] = {}
        for item in parsed:
            key = (item.unit_id, item.wave_id, item.attack_upgrade, item.armor_upgrade,
                   item.batch_id, item.arrival_round)
            totals[key] = totals.get(key, 0) + item.quantity
        units = tuple(ArmyUnit(unit, quantity, wave, attack, armor, batch, arrival)
                      for (unit, wave, attack, armor, batch, arrival), quantity in sorted(totals.items()))
        return cls(units, _integer(data.get("forge_level", 0), "forge_level", 0, 5))


@dataclass(frozen=True)
class Profiles:
    mechanics: str = "battle-system-paper-2020"
    unit_stats: str = "infinite-horizons-current"
    workshop: str = "v14-workshop"
    forge: str = "v14-hephaistos"
    support: str = "v17-support-healing"
    targeting: str = "legacy-community-land-targeting"
    battle_end: str = "legacy-community-battle-end"
    formation: str = "formation-land"
    # Appended after the original eight fields so existing positional callers
    # retain their historical argument mapping.
    economy: str = "military-economy-current"

    @classmethod
    def from_dict(cls, value: Any) -> "Profiles":
        data = _object(value, "profiles")
        result = cls(
            mechanics=str(data.get("mechanics", cls.mechanics)),
            unit_stats=str(data.get("unit_stats", cls.unit_stats)),
            workshop=str(data.get("workshop", cls.workshop)),
            forge=str(data.get("forge", cls.forge)),
            support=str(data.get("support", cls.support)),
            targeting=str(data.get("targeting", cls.targeting)),
            battle_end=str(data.get("battle_end", cls.battle_end)),
            formation=str(data.get("formation", cls.formation)),
            economy=str(data.get("economy", cls.economy)),
        )
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
    battlefield: str = "land-mini"
    max_rounds: int = DEFAULT_MAX_ROUNDS

    @classmethod
    def from_dict(cls, value: Any) -> "Scenario":
        data = _object(value, "request body")
        try:
            policy = Policy(data.get("policy", "strict"))
        except ValueError as exc:
            raise ScenarioError("policy must be strict or experimental") from exc
        battlefield = data.get("battlefield", "land-mini")
        if not isinstance(battlefield, str) or battlefield not in {"land-mini", "land-small", "land-medium", "land-large", "land-max", "naval-mini"}:
            raise ScenarioError("unsupported battlefield id")
        try:
            return cls(Army.from_dict(data["attacker"]), Army.from_dict(data["defender"]),
                       Profiles.from_dict(data.get("profiles", {})), policy, battlefield,
                       _integer(data.get("max_rounds", DEFAULT_MAX_ROUNDS), "max_rounds", 1, MAX_ROUNDS))
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
    ammo_pool_shots: int | None = None
    support_units: int = 0
    # Immutable normal-Phase-A denominator for UI/reporting.  The live pool is
    # deliberately kept on the wave (entry batch), never on a side or slot.
    ammo_capacity_shots: int | None = None

    @property
    def alive(self) -> int:
        return self.reserve + self.support_units + sum(slot.units for slot in self.slots)
