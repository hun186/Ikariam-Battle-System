from ikariam_battle.battlefield import LAND_MINI, deploy
from ikariam_battle.formation import FormationRules, plan_initial_formation
import pytest

from ikariam_battle.engine import _prepare_round_start
from ikariam_battle.models import Army, ArmyUnit, ScenarioError, Slot, Wave
from ikariam_battle.units import UnitRegistry


def army(unit,quantity=100):
 return Army.from_dict({'units':[{'unit_id':unit,'quantity':quantity}]})


def test_land_mini_exact_lines_slots_and_no_flank():
 assert {line:len(g.physical_order) for line,g in LAND_MINI.lines.items()} == {
  'first':3,'second':3,'third':1,'balloon':1,'anti-balloon':1}
 assert 'flank' not in LAND_MINI.lines


def test_physical_layout_and_center_first_deployment():
 line=LAND_MINI.lines['first']
 assert line.physical_order==(2,1,3) and line.damage_priority==(1,2,3)
 slot=deploy(army('hoplite',1),UnitRegistry.load(),LAND_MINI)[0].slots[0]
 assert (slot.damage_position,slot.physical_position)==(1,2)


def test_slot_space_divided_by_unit_size():
 registry=UnitRegistry.load()
 expected={'hoplite':30,'steam_giant':10,'sulphur_carabineer':7,'catapult':6,
           'gyrocopter':10,'bombardier':5}
 for unit,capacity in expected.items():
  wave=deploy(army(unit),registry,LAND_MINI)[0]
  assert wave.slots[0].capacity==capacity
  assert wave.slots[0].units==capacity


def test_light_infantry_falls_back_to_front_when_no_heavy_is_available():
 wave=deploy(army('swordsman',30),UnitRegistry.load(),LAND_MINI)[0]
 assert [(slot.line,slot.units) for slot in wave.slots]==[('first',30)] and wave.reserve==0
 assert UnitRegistry.load().get('swordsman').native_line=='flank'


def test_heavy_sufficient_keeps_light_out_of_front():
 waves=deploy(Army.from_dict({'units':[{'unit_id':'hoplite','quantity':90},
  {'unit_id':'swordsman','quantity':30}]}),UnitRegistry.load(),LAND_MINI)
 assert {slot.unit_id for wave in waves for slot in wave.slots if slot.line=='first'}=={'hoplite'}
 assert next(w for w in waves if w.unit.unit_id=='swordsman').reserve==30


def test_partial_heavy_owns_partial_slot_then_light_fills_other_front_slots():
 waves=deploy(Army.from_dict({'units':[{'unit_id':'hoplite','quantity':8},
  {'unit_id':'swordsman','quantity':60}]}),UnitRegistry.load(),LAND_MINI)
 slots=sorted((s for w in waves for s in w.slots if s.line=='first'),key=lambda s:s.damage_position)
 assert [(s.unit_id,s.units,s.damage_position) for s in slots]==[
  ('hoplite',8,1),('swordsman',30,2),('swordsman',30,3)]


def test_front_fallback_consumes_light_before_unavailable_mini_flank():
 waves=deploy(Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30},
  {'unit_id':'swordsman','quantity':100}]}),UnitRegistry.load(),LAND_MINI)
 swordsman=next(w for w in waves if w.unit.unit_id=='swordsman')
 assert sum(s.units for s in swordsman.slots)==60 and swordsman.reserve==40


def test_planner_is_pure_and_registry_metadata_is_immutable():
 registry=UnitRegistry.load(); before=registry.get('swordsman')
 plan=plan_initial_formation(Army.from_dict({'units':[{'unit_id':'swordsman','quantity':1}]}),registry,LAND_MINI)
 assert plan.placements[0].runtime_line=='first'
 assert registry.get('swordsman')==before and before.native_line=='flank'


def test_formation_profile_records_standard_order_and_unknown_combat_boundary():
 rules=FormationRules.load()
 assert rules.lines['first']['standard_deployment_order']==[6,4,2,1,3,5,7]
 assert rules.lines['first']['class_precedence']==['heavy_infantry','light_infantry']
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' in rules.unknowns


def test_land_mini_air_deployment_is_capped_at_ten_space():
 registry=UnitRegistry.load()
 gyro=deploy(army('gyrocopter',50),registry,LAND_MINI)[0]
 bomber=deploy(army('bombardier',50),registry,LAND_MINI)[0]
 assert (gyro.slots[0].units,gyro.reserve)==(10,40)
 assert (bomber.slots[0].units,bomber.reserve)==(5,45)


def test_duplicate_same_wave_rows_normalize():
 one=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':60,'wave_id':'w','attack_upgrade':12,'armor_upgrade':8}]})
 split=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30,'wave_id':'w','attack_upgrade':12,'armor_upgrade':8},{'unit_id':'hoplite','quantity':30,'wave_id':'w','attack_upgrade':12,'armor_upgrade':8}]})
 assert one==split


def test_ammunition_pool_is_scoped_to_entry_wave():
 waves=deploy(Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42,'wave_id':'batch-a'}]}),UnitRegistry.load(),LAND_MINI)
 assert waves[0].ammo_pool_shots==42*3
 assert waves[0].ammo_capacity_shots==42*3


def test_different_entry_waves_do_not_share_ammunition():
 registry=UnitRegistry.load()
 army=Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42,'wave_id':'batch-a'},
                               {'unit_id':'sulphur_carabineer','quantity':21,'wave_id':'batch-b'}]})
 waves=deploy(army,registry,LAND_MINI)
 waves[0].ammo_pool_shots=2
 assert [(w.unit.wave_id,w.ammo_pool_shots,w.ammo_capacity_shots) for w in waves]==[
  ('batch-a',2,126),('batch-b',63,63)]


def test_wave_model_can_represent_future_multi_line_slots_without_enabling_fallback():
 wave=Wave(ArmyUnit('sulphur_carabineer',42,'batch-a'),33,[
  Slot('second-1','second',2,1,'sulphur_carabineer','batch-a',2,7),
  Slot('first-1','first',2,1,'sulphur_carabineer','batch-a',7,7)],ammo_pool_shots=2,
  ammo_capacity_shots=126)
 assert wave.alive==42 and {slot.line for slot in wave.slots}=={'first','second'}


def test_multiline_wave_cannot_silently_enter_refill_or_redistribution():
 wave=Wave(ArmyUnit('sulphur_carabineer',14,'batch-a'),0,[
  Slot('second-1','second',2,1,'sulphur_carabineer','batch-a',7,7,3),
  Slot('first-1','first',2,1,'sulphur_carabineer','batch-a',7,7,5)],
  ammo_pool_shots=2,ammo_capacity_shots=42)
 before=[(slot.units,slot.damage) for slot in wave.slots]
 with pytest.raises(ScenarioError,match='UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS'):
  _prepare_round_start([wave],[],2,'attacker',{})
 assert [(slot.units,slot.damage) for slot in wave.slots]==before


def test_spearman_taxonomy_separates_semantic_class_from_native_line():
 spearman=UnitRegistry.load().get('spearman')
 assert spearman.semantic_class=='light_infantry'
 assert spearman.native_line=='first' and spearman.battlefield_class=='first'
