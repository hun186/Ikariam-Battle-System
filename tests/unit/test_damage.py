from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.models import Army
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry


def test_same_army_unit_specific_levels_drive_different_traces():
 army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30,'attack_upgrade':12},{'unit_id':'swordsman','quantity':20,'attack_upgrade':3}]})
 levels={u.unit_id:u.attack_upgrade for u in army.units}; r=UnitRegistry.load(); w=WorkshopProfile.load(); f=ForgeProfile.load()
 hop=calculate_damage(r.get('hoplite'),r.get('hoplite'),levels['hoplite'],0,0,0,w,f,RoundingPolicy.FLOOR)
 sword=calculate_damage(r.get('swordsman'),r.get('hoplite'),levels['swordsman'],0,0,0,w,f,RoundingPolicy.FLOOR)
 assert hop.workshop_attack_level==12 and hop.workshop_damage_bonus==60
 assert sword.workshop_attack_level==3 and sword.workshop_damage_bonus==15


def test_rounding_policies_diverge_without_claiming_truth():
 r=UnitRegistry.load(); w=WorkshopProfile.load(); f=ForgeProfile.load(); args=(r.get('sulphur_carabineer'),r.get('hoplite'),0,0,1,0,w,f)
 assert calculate_damage(*args,RoundingPolicy.FLOOR).final_damage==603
 assert calculate_damage(*args,RoundingPolicy.NEAREST).final_damage==604
