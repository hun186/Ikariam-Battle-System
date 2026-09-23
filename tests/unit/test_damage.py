from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry


def test_trace_contains_workshop_and_forge_components():
    r=UnitRegistry.load(); w=WorkshopProfile.load(); f=ForgeProfile.load()
    t=calculate_damage(r.get('sulphur_carabineer'),r.get('hoplite'),12,12,5,5,w,f,RoundingPolicy.FLOOR)
    assert t.workshop_damage_bonus==60 and t.target_workshop_armor_bonus==60
    assert t.forge_damage_multiplier=='1.15' and t.target_forge_armor_bonus==20
    assert set(t.as_dict()) >= {'base_damage','pre_forge_damage','post_forge_damage','net_damage_before_rounding','final_damage'}


def test_rounding_policies_actually_diverge_without_claiming_truth():
    r=UnitRegistry.load(); w=WorkshopProfile.load(); f=ForgeProfile.load()
    args=(r.get('sulphur_carabineer'),r.get('hoplite'),0,0,1,0,w,f)
    assert calculate_damage(*args,RoundingPolicy.FLOOR).final_damage == 603
    assert calculate_damage(*args,RoundingPolicy.NEAREST).final_damage == 604
