import json
from decimal import Decimal
from importlib.resources import files

from ikariam_battle.economy import MilitaryEconomyProfile
from ikariam_battle.units import UnitRegistry


def _evidence():
    return json.loads(
        files("ikariam_battle.data.calibration")
        .joinpath("naval-units-official-help-2026-10-05.json")
        .read_text(encoding="utf-8")
    )


def test_official_help_naval_units_match_runtime_numeric_profiles():
    registry=UnitRegistry.load()
    evidence=_evidence()
    assert len(evidence["units"])==11
    for row in evidence["units"]:
        unit=registry.get(row["id"])
        assert unit.hit_points==row["hp"]
        assert unit.base_armor==row["armor"]
        assert unit.size==row["size"]
        for wr in row["weapons"]:
            weapon=next(w for w in unit.weapons if w.id==wr["runtime_id"])
            assert weapon.damage==wr["damage"]
            assert weapon.ammunition==wr["ammo"]
            assert weapon.accuracy==wr["accuracy"]["quantized_percent"]


def test_official_help_naval_accuracy_bars_quantize_to_runtime_values():
    for row in _evidence()["units"]:
        for weapon in row["weapons"]:
            a=weapon["accuracy"]
            quantized=round((100*a["fill_px"]/a["track_px"])/5)*5
            assert quantized==a["quantized_percent"]


def test_rocket_ship_secondary_accuracy_is_official_70_percent():
    registry=UnitRegistry.load()
    rocket=registry.get("rocket_ship")
    secondary=next(w for w in rocket.weapons if w.id=="secondary")
    assert secondary.damage==400
    assert secondary.accuracy==70


def test_naval_economy_breakdown_and_general_scores_match_official_help():
    economy=MilitaryEconomyProfile.load()
    evidence={row["id"]:row for row in _evidence()["units"]}
    for unit_id,expected in evidence.items():
        entry=economy.units[unit_id]
        assert entry.resource_cost_basis==expected["resource_cost_basis"]
        assert entry.resource_cost_basis_total==expected["resource_cost_basis_total"]
        assert entry.general_score==Decimal(expected["general_score"])
        assert entry.general_score==Decimal(entry.resource_cost_basis_total)/Decimal(50)
        assert entry.upkeep_gold==expected["upkeep_gold"]
        assert entry.population==expected["population"]


def test_key_naval_general_scores():
    economy=MilitaryEconomyProfile.load()
    assert economy.score("ram_ship")==Decimal("5")
    assert economy.score("ballista_ship")==Decimal("6.8")
    assert economy.score("steam_ram")==Decimal("24")
    assert economy.score("rocket_ship")==Decimal("28")
    assert economy.score("diving_boat")==Decimal("20.2")
    assert economy.score("tender")==Decimal("16")
