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

    @property
    def formation_order_key(self) -> tuple[int, str, str, str, int, int]:
        """Deterministic precedence shared by initial placement and rebuilds."""
        return (
            self.arrival_round, self.batch_id, self.unit_id, self.wave_id,
            self.attack_upgrade, self.armor_upgrade,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ArmyUnit":
        row = _object(value, "army unit")
        if not isinstance(row.get("unit_id"), str) or not row["unit_id"]:
            raise ScenarioError("unit_id must be a non-empty string")
        has_wave = "wave_id" in row
        has_batch = "entry_batch_id" in row
        explicit_wave = row.get("wave_id") if has_wave else None
        explicit_batch = row.get("entry_batch_id") if has_batch else None
        if has_wave and (not isinstance(explicit_wave, str) or not explicit_wave):
            raise ScenarioError("wave_id must be a non-empty string")
        if has_batch and (not isinstance(explicit_batch, str) or not explicit_batch):
            raise ScenarioError("entry_batch_id must be a non-empty string")
        if has_batch:
            entry_batch_id = explicit_batch
        elif has_wave:
            entry_batch_id = explicit_wave
        else:
            entry_batch_id = "batch-1"
        # Preserve the historical implicit wave-1 contract for callers that
        # omit both identity fields. Explicitly supplied invalid values are
        # rejected above rather than treated as missing.
        if has_wave:
            wave_id = explicit_wave
        elif has_batch:
            wave_id = f"{entry_batch_id}::{row['unit_id']}"
        else:
            wave_id = "wave-1"
        return cls(row["unit_id"], _integer(row.get("quantity"), "quantity"), wave_id,
                   _integer(row.get("attack_upgrade", 0), "attack_upgrade"),
                   _integer(row.get("armor_upgrade", 0), "armor_upgrade"),
                   entry_batch_id,
                   _integer(row.get("arrival_round", 0), "arrival_round", 0, MAX_ROUNDS))


@dataclass(frozen=True)
class Army:
    units: tuple[ArmyUnit, ...]
    forge_level: int = 0
    army_kind: str = "player"

    @classmethod
    def from_dict(cls, value: Any) -> "Army":
        data = _object(value, "army")
        army_kind = data.get("army_kind", "player")
        if army_kind not in {"player", "barbarian"}:
            raise ScenarioError("army_kind must be player or barbarian")
        raw = data.get("units")
        if not isinstance(raw, list) or not raw:
            raise ScenarioError("army.units must be a non-empty list")
        parsed = [ArmyUnit.from_dict(item) for item in raw]
        if not any(item.quantity for item in parsed):
            raise ScenarioError("an army must contain at least one unit")
        forge_level = _integer(data.get("forge_level", 0), "forge_level", 0, 5)
        if army_kind == "barbarian":
            if forge_level != 0:
                raise ScenarioError("barbarian armies do not use Forge levels")
            if any(item.attack_upgrade or item.armor_upgrade for item in parsed):
                raise ScenarioError("barbarian armies do not use Workshop upgrades")
            if any(item.arrival_round != 0 for item in parsed):
                raise ScenarioError("barbarian armies do not use delayed entry batches")
            if len({item.batch_id for item in parsed}) != 1:
                raise ScenarioError("barbarian armies use one fixed entry batch")
            waves_by_unit: dict[str, set[str]] = {}
            for item in parsed:
                waves_by_unit.setdefault(item.unit_id, set()).add(item.wave_id)
            if any(len(waves) != 1 for waves in waves_by_unit.values()):
                raise ScenarioError("barbarian unit types cannot be split across waves")
        upgrades: dict[str, tuple[int, int]] = {}
        batch_rounds: dict[str, int] = {}
        wave_batches: dict[tuple[str, str], str] = {}
        for item in parsed:
            pair = (item.attack_upgrade, item.armor_upgrade)
            if item.unit_id in upgrades and upgrades[item.unit_id] != pair:
                raise ScenarioError(f"conflicting Workshop upgrades for {item.unit_id}")
            upgrades[item.unit_id] = pair
            if item.batch_id in batch_rounds and batch_rounds[item.batch_id] != item.arrival_round:
                raise ScenarioError(f"entry batch {item.batch_id} has conflicting arrival_round values")
            batch_rounds[item.batch_id] = item.arrival_round
            wave_key = (item.unit_id, item.wave_id)
            if wave_key in wave_batches and wave_batches[wave_key] != item.batch_id:
                raise ScenarioError(
                    f"wave_id {item.wave_id} for {item.unit_id} cannot be reused across entry batches"
                )
            wave_batches[wave_key] = item.batch_id
        # State is unit-specific even when multiple unit types share one arrival
        # batch. Duplicate presentation rows aggregate only when both identities
        # and upgrades/timing agree.
        totals: dict[tuple[str, str, int, int, str, int], int] = {}
        for item in parsed:
            key = (item.unit_id, item.wave_id, item.attack_upgrade, item.armor_upgrade,
                   item.batch_id, item.arrival_round)
            totals[key] = totals.get(key, 0) + item.quantity
        units = tuple(sorted(
            (
                ArmyUnit(unit, quantity, wave, attack, armor, batch, arrival)
                for (unit, wave, attack, armor, batch, arrival), quantity in totals.items()
            ),
            key=lambda item: item.formation_order_key,
        ))
        return cls(units, forge_level, army_kind)


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
