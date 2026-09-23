from ikariam_battle.profiles import ForgeProfile, SupportProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry


def test_review_supplied_current_values_and_field_provenance():
    r=UnitRegistry.load()
    expected={'hoplite':(1120,360,20,None),'sulphur_carabineer':(240,580,0,3),
              'steam_ram':(11520,3320,320,None),'rocket_ship':(1300,7600,120,2)}
    for key,(hp,damage,armor,ammo) in expected.items():
        unit=r.get(key)
        assert (unit.hit_points,unit.primary_weapon.damage,unit.base_armor,unit.primary_weapon.ammunition)==(hp,damage,armor,ammo)
        assert unit.provenance['hp']['source_type']=='REVIEW_SUPPLIED'
        assert unit.provenance['hp']['community_crosscheck_needed'] is True
    assert r.get('rocket_ship').weapons[1].damage == 400


def test_registry_contains_all_major_land_and_naval_units():
    r=UnitRegistry.load()
    assert len(r.all()) == 26
    assert {'doctor','cook','tender'} <= {u.id for u in r.all() if u.role=='support'}


def test_workshop_level_twelve_bonuses():
    p=WorkshopProfile.load()
    assert p.bonus('land',12)==60
    assert p.bonus('naval',12)==120


def test_forge_exact_levels():
    p=ForgeProfile.load()
    assert [(str(p.effect(i).damage_multiplier),p.effect(i).armor_bonus) for i in range(6)] == [
        ('1',0),('1.075',0),('1.075',10),('1.1',10),('1.125',20),('1.15',20)]


def test_support_capacity_is_derived_not_claimed_absolute():
    p=SupportProfile.load()
    assert p.raw['legacy_capacity']==200 and p.raw['healing_capacity_multiplier']==20
    assert p.derived_capacity==4000
    assert p.raw['derived_capacity_provenance']['source_type']=='DERIVED'
