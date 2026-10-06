from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import files
import json
from typing import Mapping


@dataclass(frozen=True)
class UnitEconomy:
    resource_cost_basis_total: int
    general_score: Decimal
    resource_cost_basis: dict[str, int]
    upkeep_gold: int | None = None
    population: int | None = None


class MilitaryEconomyProfile:
    def __init__(self, units: dict[str, UnitEconomy], metadata: dict):
        self.units = units
        self.metadata = metadata

    @classmethod
    def load(cls, name: str = "military-economy-current") -> "MilitaryEconomyProfile":
        raw = json.loads(
            files("ikariam_battle.data.economy").joinpath(f"{name}.json").read_text(encoding="utf-8")
        )
        units: dict[str, UnitEconomy] = {}
        for unit_id, row in raw["units"].items():
            basis = int(row["resource_cost_basis_total"])
            score = Decimal(str(row["general_score"]))
            breakdown = {
                key: int(value)
                for key, value in row.get("resource_cost_basis", {}).items()
            }
            if breakdown and sum(breakdown.values()) != basis:
                raise ValueError(
                    f"economy profile mismatch for {unit_id}: "
                    f"resource breakdown={sum(breakdown.values())} but total={basis}"
                )
            derived = Decimal(basis) / Decimal(50)
            if score != derived:
                raise ValueError(
                    f"economy profile mismatch for {unit_id}: general_score={score} but basis/50={derived}"
                )
            units[unit_id] = UnitEconomy(
                basis,
                score,
                breakdown,
                int(row["upkeep_gold"]) if row.get("upkeep_gold") is not None else None,
                int(row["population"]) if row.get("population") is not None else None,
            )
        return cls(units, raw["metadata"])

    def score(self, unit_id: str) -> Decimal:
        try:
            return self.units[unit_id].general_score
        except KeyError as exc:
            raise ValueError(f"missing military economy data for unit_id: {unit_id}") from exc

    def resource_cost_basis_total(self, unit_id: str) -> int:
        try:
            return self.units[unit_id].resource_cost_basis_total
        except KeyError as exc:
            raise ValueError(f"missing military economy data for unit_id: {unit_id}") from exc

    def resource_cost_basis_loss(self, casualties: Mapping[str, int]) -> int:
        return sum(
            self.resource_cost_basis_total(unit_id) * int(quantity)
            for unit_id, quantity in casualties.items()
            if int(quantity) != 0
        )

    def score_loss(self, casualties: Mapping[str, int]) -> Decimal:
        return Decimal(self.resource_cost_basis_loss(casualties)) / Decimal(50)

    def public(self) -> dict[str, dict[str, int | str]]:
        return {
            unit_id: {
                "resource_cost_basis_total": entry.resource_cost_basis_total,
                "resource_cost_basis": dict(entry.resource_cost_basis),
                "general_score": format(entry.general_score, "f"),
                "upkeep_gold": entry.upkeep_gold,
                "population": entry.population,
            }
            for unit_id, entry in sorted(self.units.items())
        }
