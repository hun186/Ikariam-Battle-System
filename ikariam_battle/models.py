from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScenarioError(ValueError):
    """Raised when a scenario violates the public contract."""


class Policy(str, Enum):
    STRICT = "strict"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class ArmyUnit:
    unit_id: str
    quantity: int
    attack_upgrade: int = 0
    defense_upgrade: int = 0
    wave_id: str = "wave-1"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ArmyUnit":
        try:
            result = cls(
                unit_id=str(value["unit_id"]), quantity=int(value["quantity"]),
                attack_upgrade=int(value.get("attack_upgrade", 0)),
                defense_upgrade=int(value.get("defense_upgrade", 0)),
                wave_id=str(value.get("wave_id", "wave-1")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ScenarioError(f"invalid army unit: {exc}") from exc
        if result.quantity < 0 or not 0 <= result.attack_upgrade <= 3 or not 0 <= result.defense_upgrade <= 3:
            raise ScenarioError("quantity must be non-negative and upgrades must be 0..3")
        return result


@dataclass(frozen=True)
class Army:
    units: tuple[ArmyUnit, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Army":
        raw = value.get("units") if isinstance(value, dict) else None
        if not isinstance(raw, list) or not raw:
            raise ScenarioError("army.units must be a non-empty list")
        units = tuple(ArmyUnit.from_dict(item) for item in raw)
        if not any(item.quantity for item in units):
            raise ScenarioError("an army must contain at least one unit")
        return cls(units)


@dataclass(frozen=True)
class Effects:
    attacker_hephaistos: bool = False
    defender_hephaistos: bool = False


@dataclass(frozen=True)
class Scenario:
    attacker: Army
    defender: Army
    ruleset: str = "paper-2020"
    policy: Policy = Policy.STRICT
    battlefield: str = "small-land"
    max_rounds: int = 10
    effects: Effects = Effects()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Scenario":
        if not isinstance(value, dict):
            raise ScenarioError("request body must be an object")
        try:
            policy = Policy(value.get("policy", "strict"))
            max_rounds = int(value.get("max_rounds", 10))
            effects = value.get("effects", {})
            result = cls(
                attacker=Army.from_dict(value["attacker"]), defender=Army.from_dict(value["defender"]),
                ruleset=str(value.get("ruleset", "paper-2020")), policy=policy,
                battlefield=str(value.get("battlefield", "small-land")), max_rounds=max_rounds,
                effects=Effects(bool(effects.get("attacker_hephaistos", False)), bool(effects.get("defender_hephaistos", False))),
            )
        except KeyError as exc:
            raise ScenarioError(f"missing field: {exc.args[0]}") from exc
        except ValueError as exc:
            raise ScenarioError(str(exc)) from exc
        if result.ruleset != "paper-2020" or result.battlefield != "small-land":
            raise ScenarioError("supported ruleset/battlefield: paper-2020 / small-land")
        if not 1 <= result.max_rounds <= 100:
            raise ScenarioError("max_rounds must be 1..100")
        return result


@dataclass
class Slot:
    number: int
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
    total_damage: int = 0

    @property
    def alive(self) -> int:
        return self.reserve + sum(slot.units for slot in self.slots)
