from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from importlib.resources import files
import json
from typing import Any


@dataclass(frozen=True)
class BarbarianUnit:
    id: str
    display_name: str
    semantic_class: str
    native_line: str
    first_appearance_level: int
    last_appearance_level: int | None
    equivalent_player_unit: str | None
    hit_points: int | None
    base_armor: int | None
    damage: int | None
    accuracy: int | None
    ammunition: int | None
    size: int | None
    provenance: dict[str, Any]

    def public(self) -> dict[str, Any]:
        numerically_supported = (
            self.hit_points is not None
            and self.base_armor is not None
            and self.damage is not None
            and self.size is not None
        )
        return {
            "id": self.id,
            "display_name": self.display_name,
            "domain": "land",
            "army_kind": "barbarian",
            "role": "combat",
            "support_effect": None,
            "battlefield_class": self.native_line,
            "semantic_class": self.semantic_class,
            "native_line": self.native_line,
            "unit_class": None,
            "first_appearance_level": self.first_appearance_level,
            "last_appearance_level": self.last_appearance_level,
            "equivalent_player_unit": self.equivalent_player_unit,
            "hit_points": self.hit_points,
            "base_armor": self.base_armor,
            "damage": self.damage,
            "accuracy": self.accuracy,
            "ammunition": self.ammunition,
            "size": self.size,
            "weapons": [{
                "id": "primary",
                "damage": self.damage,
                "ammunition": self.ammunition,
                "trigger": "primary",
                "accuracy": self.accuracy,
            }],
            "numerically_supported": numerically_supported,
            "counts_toward_garrison_limit": True,
            "resource_cost_basis_total": 0,
            "general_score": "0",
            "selectable_by_player": False,
            "selectable_in_simulator": True,
            "simulation_ready": numerically_supported,
            "provenance": self.provenance,
        }


class BarbarianRegistry:
    def __init__(self, definitions: dict[str, BarbarianUnit], metadata: dict[str, Any]):
        self._definitions = definitions
        self.metadata = metadata

    @classmethod
    def load(cls, profile: str = "barbarian-village-current") -> "BarbarianRegistry":
        resource = files("ikariam_battle.data.barbarians").joinpath(f"{profile}.json")
        raw = json.loads(resource.read_text(encoding="utf-8"))
        definitions = {}
        for row in raw["units"]:
            definitions[row["id"]] = BarbarianUnit(
                id=row["id"],
                display_name=row["display_name"],
                semantic_class=row["semantic_class"],
                native_line=row["native_line"],
                first_appearance_level=row["first_appearance_level"],
                last_appearance_level=row.get("last_appearance_level"),
                equivalent_player_unit=row.get("equivalent_player_unit"),
                hit_points=row.get("hp"),
                base_armor=row.get("base_armor"),
                damage=row.get("damage"),
                accuracy=row.get("accuracy"),
                ammunition=row.get("ammunition"),
                size=row.get("size"),
                provenance=row["provenance"],
            )
        return cls(definitions, raw["metadata"])

    def get(self, unit_id: str) -> BarbarianUnit:
        return self._definitions[unit_id]

    def all(self) -> tuple[BarbarianUnit, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def public(self) -> list[dict[str, Any]]:
        return [unit.public() for unit in self.all()]



@dataclass(frozen=True)
class BarbarianFleetWeapon:
    id: str
    display_name: str
    damage: int
    accuracy: int
    ammunition: int | None
    trigger: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class BarbarianFleetUnit:
    id: str
    display_name: str
    official_class: str
    semantic_class: str
    native_line: str
    unit_class: str
    equivalent_player_unit: str | None
    hit_points: int
    base_armor: int
    speed: int
    size: int
    weapons: tuple[BarbarianFleetWeapon, ...]
    provenance: dict[str, Any]

    @property
    def primary_weapon(self) -> BarbarianFleetWeapon:
        return self.weapons[0]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "official_class": self.official_class,
            "domain": "naval",
            "army_kind": "barbarian",
            "role": "combat",
            "support_effect": None,
            "battlefield_class": self.native_line,
            "semantic_class": self.semantic_class,
            "native_line": self.native_line,
            "unit_class": self.unit_class,
            "equivalent_player_unit": self.equivalent_player_unit,
            "hit_points": self.hit_points,
            "base_armor": self.base_armor,
            "speed": self.speed,
            "size": self.size,
            "damage": self.primary_weapon.damage,
            "accuracy": self.primary_weapon.accuracy,
            "ammunition": self.primary_weapon.ammunition,
            "weapons": [
                {
                    "id": weapon.id,
                    "display_name": weapon.display_name,
                    "damage": weapon.damage,
                    "accuracy": weapon.accuracy,
                    "ammunition": weapon.ammunition,
                    "trigger": weapon.trigger,
                }
                for weapon in self.weapons
            ],
            "numerically_supported": True,
            "counts_toward_garrison_limit": True,
            "resource_cost_basis_total": 0,
            "general_score": "0",
            "selectable_by_player": False,
            "selectable_in_simulator": True,
            "simulation_ready": True,
            "first_appearance_level": None,
            "last_appearance_level": None,
            "provenance": self.provenance,
        }


class BarbarianFleetRegistry:
    def __init__(
        self,
        definitions: dict[str, BarbarianFleetUnit],
        metadata: dict[str, Any],
    ):
        self._definitions = definitions
        self.metadata = metadata

    @classmethod
    def load(
        cls, profile: str = "barbarian-fleet-official-help"
    ) -> "BarbarianFleetRegistry":
        resource = files("ikariam_battle.data.barbarians").joinpath(
            f"{profile}.json"
        )
        raw = json.loads(resource.read_text(encoding="utf-8"))
        definitions: dict[str, BarbarianFleetUnit] = {}
        for row in raw["units"]:
            weapons = tuple(
                BarbarianFleetWeapon(
                    id=weapon["id"],
                    display_name=weapon["display_name"],
                    damage=weapon["damage"],
                    accuracy=weapon["accuracy"],
                    ammunition=weapon.get("ammunition"),
                    trigger=weapon["trigger"],
                    provenance=weapon.get("provenance", {}),
                )
                for weapon in row["weapons"]
            )
            definitions[row["id"]] = BarbarianFleetUnit(
                id=row["id"],
                display_name=row["display_name"],
                official_class=row["official_class"],
                semantic_class=row["semantic_class"],
                native_line=row["native_line"],
                unit_class=row["unit_class"],
                equivalent_player_unit=row.get("equivalent_player_unit"),
                hit_points=row["hp"],
                base_armor=row["base_armor"],
                speed=row["speed"],
                size=row["size"],
                weapons=weapons,
                provenance=row["provenance"],
            )
        return cls(definitions, raw["metadata"])

    def get(self, unit_id: str) -> BarbarianFleetUnit:
        return self._definitions[unit_id]

    def all(self) -> tuple[BarbarianFleetUnit, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def public(self) -> list[dict[str, Any]]:
        return [unit.public() for unit in self.all()]

    def composition_for_stage(self, stage: int) -> dict[str, int]:
        """Return the empirical level-50+ fleet composition for one substage."""
        if isinstance(stage, bool) or not isinstance(stage, int) or stage < 1:
            raise ValueError("Barbarian Fleet stage must be an integer >= 1")
        model = self.metadata.get("high_level_composition_model")
        if not isinstance(model, dict):
            raise ValueError("Barbarian Fleet high-level composition model unavailable")
        growth = Decimal(str(model["ship_growth_per_stage"]))
        scale = Decimal(1) + growth * Decimal(stage - 1)
        result: dict[str, int] = {}
        for row in model["base_stage_1"]:
            base = Decimal(int(row["quantity"]))
            result[str(row["unit_id"])] = int(
                (base * scale).to_integral_value(rounding=ROUND_CEILING)
            )
        return result

    def reward_multiplier_for_stage(self, stage: int) -> Decimal:
        """Return the spreadsheet-observed linear reward multiplier."""
        if isinstance(stage, bool) or not isinstance(stage, int) or stage < 1:
            raise ValueError("Barbarian Fleet stage must be an integer >= 1")
        model = self.metadata.get("high_level_composition_model")
        if not isinstance(model, dict):
            raise ValueError("Barbarian Fleet high-level composition model unavailable")
        growth = Decimal(str(model["reward_growth_per_stage"]))
        return Decimal(1) + growth * Decimal(stage - 1)
