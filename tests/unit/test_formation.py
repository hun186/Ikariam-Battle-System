from ikariam_battle.battlefield import SMALL_LAND, STANDARD_RENUMBERING, deploy
from ikariam_battle.models import Army, ArmyUnit
from ikariam_battle.units import UnitRegistry


def test_pdf_standard_renumbering_sequences():
    # PDF pp. 3, 9 (§1.2, §2.2).
    assert STANDARD_RENUMBERING["first"] == (6, 4, 2, 1, 3, 5, 7)
    assert STANDARD_RENUMBERING["third"] == (5, 3, 1, 2, 4)
    assert STANDARD_RENUMBERING["balloon"] == (1, 2)
    assert STANDARD_RENUMBERING["anti-balloon"] == (2, 1)


def test_small_field_deployment_has_capacity_and_reserve():
    waves = deploy(Army((ArmyUnit("hoplite", 100),)), UnitRegistry.load(), SMALL_LAND)
    assert [(slot.number, slot.units) for slot in waves[0].slots] == [(2, 30), (1, 30), (3, 30)]
    assert waves[0].reserve == 10
    assert waves[0].alive == 100
