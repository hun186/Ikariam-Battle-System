from copy import deepcopy

from ikariam_battle.battlefield import (
 LAND_BATTLEFIELDS, Battlefield, LAND_MINI, LineGeometry, battlefield, deploy,
)
from ikariam_battle.formation import FormationRules, build_initial_formation, eligible_runtime_lines, plan_initial_formation
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


EXPECTED_GEOMETRY = {
 'land-mini': {
  'first': ((2,1,3),30), 'second': ((2,1,3),30), 'third': ((1,),30),
  'balloon': ((1,),10), 'anti-balloon': ((1,),10)},
 'land-small': {
  'first': ((4,2,1,3,5),30), 'second': ((4,2,1,3,5),30), 'flank': ((2,1),30),
  'third': ((1,2),30), 'balloon': ((1,),20), 'anti-balloon': ((1,),20)},
 'land-medium': {
  'first': ((6,4,2,1,3,5,7),30), 'second': ((6,4,2,1,3,5,7),30),
  'flank': ((4,2,1,3),30), 'third': ((3,1,2),30),
  'balloon': ((1,),30), 'anti-balloon': ((1,),30)},
 'land-large': {
  'first': ((6,4,2,1,3,5,7),40), 'second': ((6,4,2,1,3,5,7),40),
  'flank': ((6,4,2,1,3,5),30), 'third': ((3,1,2,4),30),
  'balloon': ((1,2),20), 'anti-balloon': ((2,1),20)},
 'land-max': {
  'first': ((6,4,2,1,3,5,7),50), 'second': ((6,4,2,1,3,5,7),50),
  'flank': ((6,4,2,1,3,5),40), 'third': ((5,3,1,2,4),30),
  'balloon': ((1,2),30), 'anti-balloon': ((2,1),30)},
}


@pytest.mark.parametrize('field_id',EXPECTED_GEOMETRY)
def test_all_land_fields_have_exact_slot_space_and_physical_order(field_id):
 field=battlefield(field_id)
 assert field is LAND_BATTLEFIELDS[field_id]
 assert {name:(line.physical_order,line.slot_space) for name,line in field.lines.items()} == EXPECTED_GEOMETRY[field_id]


@pytest.mark.parametrize(('field_id','expected'),[
 ('land-small', {'hoplite':30,'steam_giant':10,'swordsman':30,'sulphur_carabineer':7,
                 'catapult':6,'bombardier':10,'gyrocopter':20}),
 ('land-medium', {'hoplite':30,'sulphur_carabineer':7,'bombardier':15,'gyrocopter':30}),
 ('land-large', {'hoplite':40,'steam_giant':13,'swordsman':30,'sulphur_carabineer':10,
                 'bombardier':10,'gyrocopter':20}),
 ('land-max', {'hoplite':50,'steam_giant':16,'swordsman':40,'sulphur_carabineer':12,
               'catapult':6,'bombardier':15,'gyrocopter':30}),
])
def test_representative_per_slot_capacity_is_space_divided_by_unit_size(field_id,expected):
 registry=UnitRegistry.load(); field=battlefield(field_id)
 line_for={'hoplite':'first','steam_giant':'first','swordsman':'flank',
           'sulphur_carabineer':'second','catapult':'third',
           'bombardier':'balloon','gyrocopter':'anti-balloon'}
 assert {unit:field.lines[line_for[unit]].slot_space // registry.get(unit).size
         for unit in expected} == expected


@pytest.mark.parametrize(('field_id','unit','quantity','line','slot_units'),[
 ('land-small','bombardier',20,'balloon',[10]),
 ('land-small','gyrocopter',40,'anti-balloon',[20]),
 ('land-large','bombardier',30,'balloon',[10,10]),
 ('land-large','gyrocopter',50,'anti-balloon',[20,20]),
 ('land-max','bombardier',40,'balloon',[15,15]),
 ('land-max','gyrocopter',70,'anti-balloon',[30,30]),
])
def test_air_units_deploy_to_each_available_slot(field_id,unit,quantity,line,slot_units):
 wave=deploy(army(unit,quantity),UnitRegistry.load(),battlefield(field_id))[0]
 assert [slot.units for slot in wave.slots if slot.line==line]==slot_units


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


def test_land_mini_front_fallback_consumes_light_and_leaves_reserve_without_flank_slots():
 waves=deploy(Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30},
  {'unit_id':'swordsman','quantity':100}]}),UnitRegistry.load(),LAND_MINI)
 swordsman=next(w for w in waves if w.unit.unit_id=='swordsman')
 assert sum(s.units for s in swordsman.slots)==60 and swordsman.reserve==40


def test_front_before_flank_order_on_narrow_synthetic_geometry():
 field=Battlefield('test-only','land',{
  'first':LineGeometry('first',(2,1,3),30),
  'flank':LineGeometry('flank',(1,),30)},'TEST_ONLY')
 wave=build_initial_formation(army('swordsman',100),UnitRegistry.load(),field)[0]
 assert [(s.line,s.units) for s in wave.slots]==[
  ('first',30),('first',30),('first',30),('flank',10)]
 assert wave.reserve==0


def test_planner_is_pure_and_registry_metadata_is_immutable():
 registry=UnitRegistry.load(); before=registry.get('swordsman')
 plan=plan_initial_formation(Army.from_dict({'units':[{'unit_id':'swordsman','quantity':1}]}),registry,LAND_MINI)
 assert plan.placements[0].runtime_line=='first'
 assert registry.get('swordsman')==before and before.native_line=='flank'


def test_formation_profile_records_standard_order_and_unknown_combat_boundary():
 rules=FormationRules.load()
 assert rules.metadata['implementation_status']=='ALL_LAND_GEOMETRIES_PLANNER_IMPLEMENTED_COMBAT_GUARDED'
 assert rules.lines['first']['implementation_status']=='IMPLEMENTED_FOR_ALL_LAND_GEOMETRIES'
 assert rules.lines['flank']['implementation_status']=='NATIVE_SLOTS_LAND_SMALL_THROUGH_MAX'
 assert rules.lines['first']['deployment_order_authority']=='battlefield_geometry.damage_priority'
 assert rules.lines['first']['standard_physical_damage_labels_evidence']==[6,4,2,1,3,5,7]
 assert rules.lines['first']['class_precedence']==['heavy_infantry','light_infantry']
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' in rules.unknowns


def modified_rules(mutator):
 source=FormationRules.load(); lines=deepcopy(source.lines); mutator(lines)
 return FormationRules(source.metadata,lines,source.unknowns)


def test_first_line_profile_eligibility_is_executable():
 rules=modified_rules(lambda lines: lines['first'].update(
  eligible_semantic_classes=['heavy_infantry'],class_precedence=['heavy_infantry'],
  fallback_semantic_classes=[]))
 plan=plan_initial_formation(army('swordsman',30),UnitRegistry.load(),LAND_MINI,rules)
 assert plan.placements==() and plan.reserves[('swordsman','wave-1')]==30


def test_first_line_fallback_eligibility_is_executable_but_native_light_remains_eligible():
 rules=modified_rules(lambda lines: lines['first'].update(fallback_semantic_classes=[]))
 swordsman=plan_initial_formation(army('swordsman',30),UnitRegistry.load(),LAND_MINI,rules)
 spearman=plan_initial_formation(army('spearman',30),UnitRegistry.load(),LAND_MINI,rules)
 assert swordsman.placements==() and spearman.placements[0].runtime_line=='first'


def test_eligible_runtime_lines_includes_profile_fallback_but_not_unrelated_lines():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 assert eligible_runtime_lines(registry.get('swordsman'),rules,LAND_MINI)==('first',)
 assert eligible_runtime_lines(registry.get('catapult'),rules,LAND_MINI)==('third',)
 assert eligible_runtime_lines(registry.get('doctor'),rules,LAND_MINI)==()


def test_deployment_order_authority_cannot_silently_diverge():
 rules=modified_rules(lambda lines: lines['first'].update(deployment_order_authority='profile.inline'))
 with pytest.raises(ScenarioError,match='unsupported deployment order authority'):
  plan_initial_formation(army('hoplite',30),UnitRegistry.load(),LAND_MINI,rules)


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


def test_land_max_full_heavy_front_puts_light_in_native_flank_not_reserve():
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':350},
  {'unit_id':'swordsman','quantity':240},
 ]}),UnitRegistry.load(),field)
 hoplite=next(w for w in waves if w.unit.unit_id=='hoplite')
 swordsman=next(w for w in waves if w.unit.unit_id=='swordsman')
 assert sum(slot.units for slot in hoplite.slots if slot.line=='first')==350
 assert [(slot.line,slot.units) for slot in swordsman.slots]==[('flank',40)]*6
 assert swordsman.reserve==0


def test_land_max_front_deploys_center_out_by_pdf_damage_priority():
 registry=UnitRegistry.load(); field=LAND_BATTLEFIELDS['land-max']
 wave=deploy(army('hoplite',101),registry,field)[0]
 assert [(slot.damage_position,slot.physical_position,slot.units) for slot in wave.slots]==[
  (1,4,50),(2,3,50),(3,5,1)]


def test_round_start_repacks_same_wave_survivors_center_first_before_rr():
 registry=UnitRegistry.load(); field=LAND_BATTLEFIELDS['land-max']
 wave=deploy(army('hoplite',350),registry,field)[0]
 for slot in wave.slots:
  slot.units=3 if slot.damage_position==7 else 0
  slot.damage=10 if slot.damage_position==7 else 0
 wave.reserve=100
 events=[]; applied={}
 _prepare_round_start([wave],events,2,'attacker',applied)

 occupied=[slot for slot in wave.slots if slot.units]
 assert [(slot.damage_position,slot.physical_position,slot.units) for slot in occupied]==[
  (1,4,50),(2,3,50),(3,5,3)]
 assert wave.reserve==0
 assert sum(slot.damage for slot in wave.slots)+wave.reserve_damage==10
 assert next(slot for slot in wave.slots if slot.damage_position==1).damage>0
 assert all(slot.damage==0 for slot in wave.slots if not slot.units)
 assert any(event.type=='slot_repacked' for event in events)
