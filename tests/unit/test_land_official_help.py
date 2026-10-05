import json
from decimal import Decimal
from importlib.resources import files

from ikariam_battle.economy import MilitaryEconomyProfile
from ikariam_battle.units import UnitRegistry


def _evidence():
    return json.loads(
        files("ikariam_battle.data.calibration")
        .joinpath("land-units-official-help-2026-10-05.json")
        .read_text(encoding="utf-8")
    )


def test_official_help_land_units_match_runtime_numeric_profiles():
    registry=UnitRegistry.load()
    evidence=_evidence()
    assert len(evidence["units"])==15
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


def test_official_help_accuracy_bars_quantize_to_runtime_values():
    for row in _evidence()["units"]:
        for weapon in row["weapons"]:
            a=weapon["accuracy"]
            quantized=round((100*a["fill_px"]/a["track_px"])/5)*5
            assert quantized==a["quantized_percent"]


def test_land_economy_breakdown_matches_help_and_score_formula():
    economy=MilitaryEconomyProfile.load()
    evidence={row["id"]:row for row in _evidence()["units"]}
    assert set(evidence) <= set(economy.units)
    for unit_id,expected in evidence.items():
        entry=economy.units[unit_id]
        assert entry.resource_cost_basis==expected["resource_cost_basis"]
        assert sum(entry.resource_cost_basis.values())==entry.resource_cost_basis_total
        assert entry.general_score==Decimal(entry.resource_cost_basis_total)/Decimal(50)
        assert entry.upkeep_gold==expected["upkeep_gold"]
        assert entry.population==expected["population"]


def test_key_official_help_resource_examples():
    economy=MilitaryEconomyProfile.load()
    assert economy.units["sulphur_carabineer"].resource_cost_basis=={
        "wood":50,"wine":0,"marble":0,"crystal":0,"sulfur":150
    }
    assert economy.units["mortar"].resource_cost_basis=={
        "wood":300,"wine":0,"marble":0,"crystal":0,"sulfur":1250
    }
    assert economy.units["doctor"].resource_cost_basis["crystal"]==450
    assert economy.units["cook"].resource_cost_basis["wine"]==150
