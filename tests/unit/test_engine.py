from collections import defaultdict
from copy import deepcopy
import pytest
from ikariam_battle import simulate
from ikariam_battle.battlefield import LAND_BATTLEFIELDS, LAND_MINI, NAVAL_BATTLEFIELDS, deploy
from ikariam_battle.engine import (
 _arrival_waves, _cross_wave_rebuild_requirements, _formation_shots, _healing_status, _ir_trigger, _plan_fire, _preflight,
 _prepare_round_start, _redistribute, _resolve_volleys, _sr_trigger, _target,
)
from ikariam_battle.formation import FormationRules
from ikariam_battle.models import Army, ArmyUnit, Policy, Scenario, ScenarioError, Slot, Wave
from ikariam_battle.profiles import ForgeProfile, SupportProfile, TargetingProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry
from ikariam_battle.weapon_selection import select_active_weapon


def scenario(policy='experimental',rounds=5):
 return {'policy':policy,'battlefield':'land-mini','max_rounds':rounds,
  'attacker':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':60,'attack_upgrade':12,'armor_upgrade':8}]},
  'defender':{'forge_level':0,'units':[{'unit_id':'hoplite','quantity':60,'attack_upgrade':4,'armor_upgrade':6}]}}


def test_strict_refuses_accuracy_targeting_and_other_unknowns():
 r=simulate(scenario('strict')); rules={e['details']['rule_id'] for e in r['events'] if e['type']=='unsupported_mechanic'}
 assert r['status']=='inconclusive' and r['rounds_completed']==0
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-IR-TRIGGER','UNKNOWN-SR-TRIGGER'} <= rules


def test_experimental_names_accuracy_targeting_and_is_reproducible():
 first=simulate(scenario()); assert first==simulate(scenario())
 ids={a['id'] for a in first['assumptions']}
 assert {'EXP-D-KILL-SEQUENTIAL-001','EXP-ACCURACY-CONCENTRATION-001',
         'EXP-IR-DISABLED-001','EXP-SR-DISABLED-001'} <= ids
 d_kill=next(a for a in first['assumptions'] if a['id']=='EXP-D-KILL-SEQUENTIAL-001')
 assert 'selected by the active targeting/Accuracy policy' in d_kill['description']
 assert 'most-damaged current unit' not in d_kill['description']
 assert 'EXP-TARGET-LEGACY-001' not in ids
 assert 'EXP-AMMO-PARTIAL-ORDER-001' not in ids
 assert len(ids)==len(first['assumptions'])
 assert any(e['type']=='damage_calculation' and e['details']['workshop_attack_level']==12 for e in first['events'])


def test_typed_scenario_rejects_invalid_wall_level_like_dict_input():
 attacker=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30}]})
 defender=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30}]})
 for bad in (49,True):
  typed=Scenario(attacker,defender,policy=Policy.EXPERIMENTAL,battlefield='land-mini',max_rounds=1,wall_level=bad)
  with pytest.raises(ScenarioError,match='wall_level must be 0..48'):
   simulate(typed)


def test_strict_positive_wall_level_stops_at_explicit_wall_boundary():
 s=scenario('strict'); s['wall_level']=20
 result=simulate(s)
 rules={e['details'].get('rule_id') for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert result['status']=='inconclusive' and result['rounds_completed']==0
 assert 'UNKNOWN-TOWN-WALL-COMBAT' in rules
 assert result['wall_status']=={
  'level':20,'damage':4500,'accuracy':None,'hit_points':19800,'armor':1440,
  'segments':3,'status':'unsupported_boundary',
  'combat_model_status':'INPUT_CAPTURED_COMBAT_UNSUPPORTED',
  'rule_id':'UNKNOWN-TOWN-WALL-COMBAT','effect_applied':False,
  'active':True,'inactive_reason':None,
 }
 assert any('Strict Town Wall combat is guarded' in warning for warning in result['warnings'])
 assert not any('Experimental Town Wall combat is enabled' in warning for warning in result['warnings'])


def test_experimental_active_wall_early_exit_reports_capability_not_strict_boundary():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':1,
  'wall_level':20,
  'attacker':{'units':[{'unit_id':'mortar','quantity':6}]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':90}]},
 }
 result=simulate(s)
 assert result['rounds_completed']==0
 assert result['outcome']=='defender'
 wall=result['wall_status']
 assert wall['status']=='not_reached'
 assert wall['combat_model_status']=='EXPERIMENTAL_EXECUTABLE_WITH_GUARDS'
 assert wall['effect_applied'] is False
 assert wall['active'] is True
 assert wall['breached_positions']==[]
 assert wall['flanks_locked'] is True
 assert len(wall['sections_state'])==3
 assert all(section['damage']==0 and not section['destroyed'] for section in wall['sections_state'])
 assert not any(
  e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for e in result['events']
 )


def test_experimental_mortars_breach_active_wall_and_unlock_flanks():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':1,
  'wall_level':1,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':90},
   {'unit_id':'mortar','quantity':6},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':90}]},
 }
 result=simulate(s)
 assert any('Experimental Town Wall combat is enabled' in warning for warning in result['warnings'])
 rules={e['details'].get('rule_id') for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-TOWN-WALL-COMBAT' not in rules
 breaches=[e for e in result['events'] if e['type']=='wall_section_breached']
 assert [e['details']['damage_position'] for e in breaches]==[1,2,3]
 assert result['wall_status']['status']=='breached'
 assert result['wall_status']['breached_positions']==[1,2,3]
 assert result['wall_status']['flanks_locked'] is False
 assert result['wall_status']['combat_model_status']=='EXPERIMENTAL_EXECUTABLE_WITH_GUARDS'
 assert {'EXP-WALL-FOCUS-DAMAGE-PRIORITY-001',
         'EXP-WALL-ARTILLERY-SUCCESSFUL-HIT-001'} <= {
          item['id'] for item in result['assumptions']
         }


def test_intact_wall_does_not_expose_rear_ground_formations():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':1,
  'wall_level':48,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':90},
   {'unit_id':'sulphur_carabineer','quantity':21},
  ]},
  'defender':{'units':[
   {'unit_id':'hoplite','quantity':90},
   {'unit_id':'sulphur_carabineer','quantity':21},
  ]},
 }
 result=simulate(s)
 assert result['wall_status']['flanks_locked'] is True
 assert result['wall_status']['breached_positions']==[]
 assert all(section['damage']==0 for section in result['wall_status']['sections_state'])
 assert result['final_state']['defender']['remaining']['sulphur_carabineer']==21
 assert not any(
  e['type']=='damage'
  and e['side']=='attacker'
  and e['details'].get('target_line') in {'second','third','flank'}
  for e in result['events']
 )


def test_surviving_wall_keeps_battle_alive_after_defender_first_is_eliminated():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':2,
  'wall_level':23,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'mortar','quantity':24,'attack_upgrade':6},
   {'unit_id':'battering_ram','quantity':6,'attack_upgrade':6},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':1}]},
 }
 result=simulate(s)

 first_round=next(row for row in result['rounds'] if row['round']==1)
 assert first_round['defender']['continuation_state']=='not_sustaining'
 round_one_breaches=[
  e['details']['damage_position']
  for e in result['events']
  if e['type']=='wall_section_breached' and e['round']==1
 ]
 assert round_one_breaches==[1,2,3,4]
 assert not any(
  e['type']=='battle_termination' and e['round']==1
  for e in result['events']
 )
 assert result['rounds_completed']>=2


def test_nonpenetrating_artillery_ticket_does_not_time_travel_past_later_wall_breach():
 s={
  'policy':'experimental','battlefield':'land-small','max_rounds':1,
  'wall_level':23,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':150},
   {'unit_id':'mortar','quantity':6,'attack_upgrade':6},
   {'unit_id':'battering_ram','quantity':6,'attack_upgrade':6},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':150}]},
 }
 result=simulate(s)

 breaches=[e for e in result['events'] if e['type']=='wall_section_breached']
 assert breaches and breaches[0]['details']['damage_position']==1

 # Mortar row 6 creates the first breach. The five earlier Ram tickets were
 # unable to penetrate the intact wall and must not be replayed after that
 # breach; only the row-6 Ram ticket may continue to the newly exposed First.
 ram_damage=[
  e for e in result['events']
  if e['type']=='damage'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]
 assert sum(e['details']['firing_units'] for e in ram_damage)==1
 ram_withheld=[
  e for e in result['events']
  if e['type']=='shots_withheld_no_damageable_target'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]
 assert sum(e['details']['count'] for e in ram_withheld)==5


def test_wall_fallthrough_keeps_frozen_address_book_after_exposed_slot_dies():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'wall_level':23,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'mortar','quantity':24,'attack_upgrade':6},
   {'unit_id':'battering_ram','quantity':6,'attack_upgrade':6},
  ]},
  'defender':{'units':[
   {'unit_id':'hoplite','quantity':1},
   {'unit_id':'steam_giant','quantity':1},
  ]},
 }
 result=simulate(s)

 ram_damage=[
  e for e in result['events']
  if e['type']=='damage'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]
 empty=[
  e for e in result['events']
  if e['type']=='shot_addressed_empty_slot'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]
 # The first Ram ticket sees only the first breached position and freezes
 # that one-position address book. It kills that target; later Ram tickets
 # must keep addressing the now-empty frozen position instead of renumbering
 # onto subsequently breached/live First slots.
 assert sum(e['details']['firing_units'] for e in ram_damage)==1
 assert any(e['details']['target_damage_position']==1 for e in empty)


def test_wall_full_breach_preserves_existing_fallthrough_book_for_leftovers():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'wall_level':23,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'mortar','quantity':24,'attack_upgrade':1000},
   {'unit_id':'battering_ram','quantity':6},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':350}]},
 }
 result=simulate(s)

 breaches=[
  e['details']['damage_position']
  for e in result['events']
  if e['type']=='wall_section_breached' and e['round']==1
 ]
 assert breaches==[1,2,3,4,5,6,7]

 ram_targets=[
  e['details']['target_damage_position']
  for e in result['events']
  if e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
  and e['type'] in {'damage','shot_addressed_empty_slot'}
 ]
 # The first Ram ticket falls through while only positions 1-4 are exposed,
 # freezing that address set. Mortars then fully breach the wall before later
 # Ram rows resolve; those leftovers must retain the earlier book rather than
 # rebuilding against all seven newly exposed First positions.
 assert ram_targets
 assert set(ram_targets) <= {1,2,3,4}
 assert 6 not in ram_targets


def test_equivalent_nonpenetrating_artillery_share_wall_fallthrough_address_book():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'wall_level':40,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'mortar','quantity':18},
   {'unit_id':'catapult','quantity':6},
   {'unit_id':'battering_ram','quantity':6},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':1}]},
 }
 result=simulate(s)

 catapult_damage=[
  e for e in result['events']
  if e['type']=='damage'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='catapult'
 ]
 ram_empty=[
  e for e in result['events']
  if e['type']=='shot_addressed_empty_slot'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]
 ram_withheld=[
  e for e in result['events']
  if e['type']=='shots_withheld_no_damageable_target'
  and e['side']=='attacker'
  and e['details'].get('source_unit_id')=='battering_ram'
 ]

 # Three Mortar columns breach the first Lv40 wall section on row 5.
 # Catapult and Ram are both nonpenetrating against the wall but have the
 # same legal First-wave set. Catapult freezes position 1 and kills its sole
 # Hoplite; the following Ram ticket must reuse that same book and address
 # the now-empty position rather than rebuilding/withholding.
 assert sum(e['details']['firing_units'] for e in catapult_damage)==1
 assert any(e['details']['target_damage_position']==1 for e in ram_empty)
 # Rows 1-4 occur before the Mortars create the first breach, so those Ram
 # tickets are correctly withheld. After the breach, the later Ram tickets
 # must use the frozen shared book and therefore are not withheld.
 assert sum(e['details']['count'] for e in ram_withheld)==4


def test_over_limit_player_defense_starts_on_land_max_with_wall_suppressed():
 s=scenario(rounds=1)
 s['town_hall_level']=1
 s['wall_level']=1
 s['defender']['units']=[{'unit_id':'hoplite','quantity':351}]
 result=simulate(s)
 g=result['garrison_status']
 assert g['garrison_limit']==350
 assert g['counted_defenders']==351
 assert g['open_field'] is True
 assert g['effective_battlefield']=='land-max'
 assert result['wall_status']['status']=='suppressed'
 assert result['wall_status']['inactive_reason']=='open_field_garrison_limit'
 assert not any(
  e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for e in result['events']
 )


def test_same_geometry_wall_reactivates_before_terminal_defender_loss():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':2,
  'town_hall_level':1,'wall_level':1,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'mortar','quantity':30,'attack_upgrade':1000},
   {'unit_id':'hoplite','quantity':350,'attack_upgrade':1000},
  ]},
  'defender':{'forge_level':0,'units':[
   {'unit_id':'hoplite','quantity':351}
  ]},
 }
 result=simulate(s)

 changes=[
  e for e in result['events']
  if e['type']=='garrison_state_change'
  and e['details'].get('direction')=='exit_open_field'
 ]
 assert changes and changes[0]['round']==1
 assert changes[0]['details']['counted_defenders']<=350
 assert changes[0]['details']['wall_reappears'] is True
 assert changes[0]['details']['wall_state']=='fresh_intact_sections'
 assert not any(
  e['type']=='battle_termination'
  and e['round']==1
  and e['details'].get('losing_side')=='defender'
  for e in result['events']
 )
 assert result['rounds_completed']>=2
 assert result['wall_status']['status']!='suppressed'


def test_defender_arrival_crossing_limit_detects_enter_open_field_transition():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':2,
  'town_hall_level':1,'wall_level':0,
  'attacker':{'units':[{'unit_id':'hoplite','quantity':90}]},
  'defender':{'units':[
   {'unit_id':'hoplite','quantity':299,'entry_batch_id':'g0','arrival_round':0},
   {'unit_id':'hoplite','quantity':10,'entry_batch_id':'g1','arrival_round':1},
  ]},
 }
 result=simulate(s)
 transition=next(
  e for e in result['events']
  if e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION'
 )
 assert transition['round']==1
 assert transition['details']['direction']=='enter_open_field'
 assert transition['details']['counted_defenders']==309
 assert transition['details']['garrison_limit']==300
 assert transition['details']['from_battlefield']=='land-mini'
 assert transition['details']['to_battlefield']=='land-max'
 assert result['status']=='inconclusive'


def test_enter_open_field_is_noop_when_already_land_max_without_wall():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'town_hall_level':1,'wall_level':0,
  'attacker':{'units':[{'unit_id':'hoplite','quantity':100}]},
  'defender':{'units':[
   {'unit_id':'hoplite','quantity':100,'entry_batch_id':'g0','arrival_round':0},
   {'unit_id':'hoplite','quantity':201,'entry_batch_id':'g1','arrival_round':1},
  ]},
 }
 result=simulate(s)
 assert not any(
  e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION'
  for e in result['events']
 )
 changes=[
  e for e in result['events']
  if e['type']=='garrison_state_change'
  and e['details'].get('direction')=='enter_open_field'
 ]
 assert changes
 assert changes[-1]['details']['counted_defenders']==301
 assert changes[-1]['details']['battlefield']=='land-max'
 assert result['garrison_status']['transition_reached'] is True
 assert result['garrison_status']['transition_blocked'] is False
 assert result['garrison_status']['transition']['direction']=='enter_open_field'
 assert result['garrison_status']['transition']['counted_defenders']==301


def test_terminal_victory_precedes_unneeded_open_field_exit_transition():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':2,
  'town_hall_level':1,'wall_level':0,
  'attacker':{'forge_level':5,'units':[
   # Fill all three firing formations evenly so stable per-formation target
   # addressing cannot leave a partially addressed defender slot alive.
   {'unit_id':'mortar','quantity':42,'attack_upgrade':1000},
   {'unit_id':'sulphur_carabineer','quantity':49,'attack_upgrade':1000},
   {'unit_id':'hoplite','quantity':350,'attack_upgrade':1000},
  ]},
  'defender':{'forge_level':0,'units':[
   {'unit_id':'hoplite','quantity':301}
  ]},
 }
 result=simulate(s)
 assert result['status']=='completed'
 assert result['outcome']=='attacker'
 assert not any(
  e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION'
  for e in result['events']
 )
 assert any(
  e['type']=='battle_termination'
  and e['details'].get('losing_side')=='defender'
  for e in result['events']
 )


def test_open_field_exit_threshold_is_detected_after_defender_casualties():
 s={
  'policy':'experimental','battlefield':'land-mini','max_rounds':3,
  'town_hall_level':1,'wall_level':0,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':350,'attack_upgrade':60}
  ]},
  'defender':{'forge_level':0,'units':[
   {'unit_id':'hoplite','quantity':301}
  ]},
 }
 result=simulate(s)
 transitions=[
  e for e in result['events']
  if e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION'
 ]
 assert transitions
 transition=transitions[-1]
 assert transition['details']['direction']=='exit_open_field'
 assert transition['details']['counted_defenders']<=300
 assert transition['details']['from_battlefield']=='land-max'
 assert transition['details']['to_battlefield']=='land-mini'
 assert result['status']=='inconclusive'
 assert result['garrison_status']['transition_reached'] is True


def test_same_geometry_open_field_exit_reactivates_wall_without_garrison_boundary():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':2,
  'town_hall_level':25,'wall_level':3,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':700,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'swordsman','quantity':480,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'sulphur_carabineer','quantity':168,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'mortar','quantity':60,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'bombardier','quantity':60,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'gyrocopter','quantity':120,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'cook','quantity':15,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'doctor','quantity':15,'entry_batch_id':'attacker-batch-1'},
  ]},
  'defender':{'forge_level':5,'units':[
   {'unit_id':'steam_giant','quantity':224,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'swordsman','quantity':480,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'archer','quantity':700,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'slinger','quantity':100,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'sulphur_carabineer','quantity':60,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'catapult','quantity':60,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'mortar','quantity':36,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'bombardier','quantity':60,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'gyrocopter','quantity':120,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'cook','quantity':15,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'doctor','quantity':15,'entry_batch_id':'defender-batch-1'},
  ]},
 }
 result=simulate(s)
 assert result['garrison_status']['garrison_limit']==1650
 assert result['garrison_status']['open_field'] is True
 changes=[
  e for e in result['events']
  if e['type']=='garrison_state_change'
  and e['details'].get('direction')=='exit_open_field'
 ]
 assert changes
 assert changes[0]['round']==1
 assert changes[0]['details']['battlefield']=='land-max'
 assert changes[0]['details']['wall_reappears'] is True
 assert changes[0]['details']['wall_state']=='fresh_intact_sections'
 assert not any(
  e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION'
  for e in result['events']
 )
 assert result['rounds_completed']>=2
 assert any(e['type']=='wall_damage' and e['round']==2 for e in result['events'])


def test_barbarian_over_limit_uses_same_open_field_threshold_rule():
 s={
  'policy':'experimental','battlefield':'land-small','max_rounds':1,
  'barbarian_village_level':10,'wall_level':1,
  'attacker':{'army_kind':'player','units':[{'unit_id':'hoplite','quantity':150}]},
  'defender':{'army_kind':'barbarian','forge_level':0,'units':[
   {'unit_id':'barbarian_clubman','quantity':801}
  ]},
 }
 result=simulate(s)
 g=result['garrison_status']
 assert g['settlement_kind']=='barbarian_village'
 assert g['barbarian_village_level']==10
 assert g['garrison_limit']==800
 assert g['counted_defenders']==801
 assert g['open_field'] is True
 assert g['effective_battlefield']=='land-max'


def test_zero_wall_level_keeps_existing_unit_vs_unit_execution_path():
 s=scenario(rounds=1); s['wall_level']=0
 result=simulate(s)
 assert result['wall_status']['status']=='not_present'
 assert result['wall_status']['segments']==0
 assert not any(
  e['type']=='unsupported_mechanic' and e['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for e in result['events']
 )


def test_symmetric_case_has_no_attacker_first_bias():
 s=scenario(); s['defender']=deepcopy(s['attacker']); r=simulate(s)
 assert r['casualties']['attacker']==r['casualties']['defender']


def test_carabineer_ammunition_is_pooled_shots_not_round_counter():
 registry=UnitRegistry.load(); attacker_army=Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42}]})
 defender_army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':90}]})
 attacker=deploy(attacker_army,registry,LAND_MINI); defender=deploy(defender_army,registry,LAND_MINI); events=[]
 assert attacker[0].ammo_pool_shots==126 and sum(s.units for s in attacker[0].slots)==21
 for round_no in range(1,5):
  plans=_plan_fire(attacker,deepcopy(defender),registry,WorkshopProfile.load(),ForgeProfile.load(),TargetingProfile.load(),events,round_no,'attacker',attacker_army,defender_army,{})
  assert plans and {plan['weapon_id'] for plan in plans}=={'primary'}
 assert attacker[0].ammo_pool_shots==42
 assert not any(e.type=='ammo_exhausted' for e in events)


def test_partial_ammo_assumption_is_applied_only_when_partial_volley_occurs():
 registry=UnitRegistry.load(); attacker_army=Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42}]}); defender_army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':90}]})
 attacker=deploy(attacker_army,registry,LAND_MINI); defender=deploy(defender_army,registry,LAND_MINI)
 attacker[0].ammo_pool_shots=5; events=[]; applied={}
 _plan_fire(attacker,defender,registry,WorkshopProfile.load(),ForgeProfile.load(),TargetingProfile.load(),events,1,'attacker',attacker_army,defender_army,applied)
 assert list(applied).count('EXP-AMMO-PARTIAL-ORDER-001')==1


def target_wave(unit,line,units=10,reserve=0):
 slot=Slot(f'{line}-1',line,1,1,unit,'w',units,30)
 return Wave(ArmyUnit(unit,units+reserve,'w'),reserve,[slot])


def test_reserve_only_priority_class_is_skipped_for_deployed_target():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=Wave(ArmyUnit('sulphur_carabineer',7),7)
 reserve_flank=Wave(ArmyUnit('swordsman',10),10,[])
 ranged=target_wave('archer','second')
 target,target_class=_target(source,[reserve_flank,ranged],registry,targeting)
 assert target is ranged and target_class=='second'


def test_swordsman_targets_deployed_flank_before_front():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=Wave(ArmyUnit('swordsman',10),10)
 front=target_wave('hoplite','first'); flank=target_wave('swordsman','flank')
 targets=[front,flank]
 target,target_class=_target(source,targets,registry,targeting)
 assert target_class=='flank' and target is flank


def test_target_priority_uses_runtime_line_not_legacy_class():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=target_wave('swordsman','first')
 front=target_wave('hoplite','first'); flank=target_wave('swordsman','flank')
 target,target_class=_target(source,[front,flank],registry,targeting)
 assert target_class=='first' and target is front


def test_destroyed_deployed_wave_is_not_targetable():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load(); source=Wave(ArmyUnit('swordsman',10),10)
 dead_flank=target_wave('swordsman','flank',0); front=target_wave('hoplite','first')
 target,target_class=_target(source,[dead_flank,front],registry,targeting)
 assert target is front and target_class=='first'


def test_support_unknowns_distinguish_healing_and_morale():
 registry=UnitRegistry.load()
 doctor=deploy(Army.from_dict({'units':[{'unit_id':'doctor','quantity':1}]}),registry,LAND_MINI)
 cook=deploy(Army.from_dict({'units':[{'unit_id':'cook','quantity':1}]}),registry,LAND_MINI)
 assert _preflight(doctor,registry,FormationRules.load(),LAND_MINI)==['UNKNOWN-HEALING-ALLOCATION']
 assert _preflight(cook,registry,FormationRules.load(),LAND_MINI)==['UNKNOWN-MORALE-SUPPORT']
 s=scenario(); s['attacker']['units'].append({'unit_id':'cook','quantity':15}); r=simulate(s)
 assert 'EXP-MORALE-NONE-001' in {a['id'] for a in r['assumptions']}
 assert 'EXP-HEAL-NONE-001' not in {a['id'] for a in r['assumptions']}
 morale=r['morale_status']
 assert morale['modeled'] is False
 assert morale['strict_rule_id']=='UNKNOWN-MORALE-SUPPORT'
 assert morale['experimental_assumption_id']=='EXP-MORALE-NONE-001'
 assert morale['sides']['attacker']=={'cook_count':15,'status':'ignored_by_named_assumption','effect_applied':False}
 assert morale['sides']['defender']=={'cook_count':0,'status':'not_present','effect_applied':False}

 strict=scenario('strict'); strict['attacker']['units'].append({'unit_id':'cook','quantity':15}); blocked=simulate(strict)
 assert blocked['status']=='inconclusive' and blocked['rounds_completed']==0
 assert blocked['morale_status']['sides']['attacker']['status']=='unsupported_boundary'
 assert blocked['morale_status']['sides']['attacker']['effect_applied'] is False


 hard_blocked={
  'policy':'experimental','battlefield':'land-small','max_rounds':2,
  'attacker':{'units':[
   {'unit_id':'swordsman','quantity':180},
   {'unit_id':'cook','quantity':15},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':150}]},
 }
 stopped=simulate(hard_blocked)
 hard_rules={e['details'].get('rule_id') for e in stopped['events'] if e['type']=='unsupported_mechanic'}
 assert {'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS','UNKNOWN-MORALE-SUPPORT'} <= hard_rules
 assert stopped['assumptions']==[]
 assert stopped['morale_status']['sides']['attacker']=={
  'cook_count':15,'status':'not_reached','effect_applied':False
 }


def test_support_is_deployed_separately_not_reported_as_reserve():
 s=scenario('strict'); s['attacker']['units'].append({'unit_id':'doctor','quantity':4})
 state=simulate(s)['initial_state']['attacker']
 assert state['deployed_support']=={'doctor':4}
 assert state['reserve'].get('doctor',0)==0


def test_single_weapon_light_fallback_has_no_specific_strict_blocker():
 s=scenario('strict'); s['attacker']['units']=[{'unit_id':'swordsman','quantity':30}]
 strict=simulate(s)
 rules={e['details']['rule_id'] for e in strict['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-IR-TRIGGER','UNKNOWN-SR-TRIGGER'} <= rules
 s['policy']='experimental'; experimental=simulate(s)
 assert any(e['type']=='attacking_matrix' for e in experimental['events'])


def test_homogeneous_swordsman_front_fires_primary_at_runtime_first_priority():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'swordsman','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
 result=simulate(s)
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 deployment=next(e for e in result['events'] if e['type']=='deployment' and e['side']=='attacker')
 assert deployment['details']['line']=='first'
 matrix=next(e for e in result['events'] if e['type']=='attacking_matrix' and e['side']=='attacker')
 assert matrix['details']['target_class']=='first'
 assert matrix['details']['weapon_id']=='primary'
 damage=next(e for e in result['events'] if e['type']=='damage_calculation' and e['side']=='attacker')
 assert damage['details']['weapon_id']=='primary'


def test_round_start_refills_before_rr_uses_following_deployment():
 wave=Wave(ArmyUnit('hoplite',40,'w'),20,[Slot('first-1','first',2,1,'hoplite','w',20,30,20)],0,None)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  [wave],UnitRegistry.load(),FormationRules.load(),LAND_MINI)
 events=[]; _prepare_round_start([wave],events,2,'attacker',{})
 assert (wave.slots[0].units,wave.slots[0].damage,wave.reserve,wave.reserve_damage)==(30,15,10,5)


def test_reserve_only_same_line_wave_fills_open_slot_without_cross_wave_boundary():
 from ikariam_battle.engine import _cross_wave_rebuild_requirements
 registry=UnitRegistry.load(); rules=FormationRules.load()
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':90,'wave_id':'wave-a'},
  {'unit_id':'hoplite','quantity':90,'wave_id':'wave-b'}]}),registry,LAND_MINI)
 assert _preflight(waves,registry,rules,LAND_MINI)==[]
 assert _cross_wave_rebuild_requirements(waves,registry,rules,LAND_MINI)==[]
 deployed=next(w for w in waves if w.unit.wave_id=='wave-a')
 reserve=next(w for w in waves if w.unit.wave_id=='wave-b')
 for slot in deployed.slots:
  slot.units=0
 deployed.slots[0].units=30; deployed.slots[1].units=30; deployed.reserve=0
 # Same-unit, same-line replacement is now an executable round-start rule, so
 # the guard must project it instead of reporting an unsupported requirement.
 assert _cross_wave_rebuild_requirements(waves,registry,rules,LAND_MINI)==[]
 events=[]; applied={}
 _prepare_round_start(
  waves,events,2,'attacker',applied,registry,rules,LAND_MINI,
 )
 assert sum(slot.units for slot in reserve.slots)==30
 assert reserve.reserve==60
 assert any(
  event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  and event.details.get('from_wave_id')=='wave-a'
  and event.details.get('to_wave_id')=='wave-b'
  for event in events
 )


def test_supported_same_batch_heavy_handoff_prevents_premature_round_end_loss():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'attack_upgrade':200}]},
    'defender':{'units':[
      {'unit_id':'steam_giant','quantity':30,'wave_id':'front','entry_batch_id':'d-batch'},
      {'unit_id':'steam_giant','quantity':10,'wave_id':'reserve','entry_batch_id':'d-batch'},
    ]}}
 result=simulate(s)
 assert result['rounds_completed']>=2
 assert not any(
  event['type']=='battle_termination'
  and event['round']==1
  and event['details'].get('losing_side')=='defender'
  for event in result['events']
 )
 assert any(
  event['type']=='slot_handoff'
  and event['round']==2
  and event['side']=='defender'
  and event['details'].get('to_wave_id')=='reserve'
  for event in result['events']
 )


def test_same_unit_long_range_cross_batch_fills_existing_second_slots_and_keeps_ammo_separate():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'sulphur_carabineer','quantity':132,
   'entry_batch_id':'attacker-batch-1'},
  {'unit_id':'sulphur_carabineer','quantity':60,
   'entry_batch_id':'attacker-batch-2'},
 ]}),registry,field)
 first=next(w for w in waves if w.unit.batch_id=='attacker-batch-1')
 second=next(w for w in waves if w.unit.batch_id=='attacker-batch-2')
 # Reproduce the uploaded Round-5 boundary: batch 1 has 59 survivors total,
 # while batch 2 is still a pristine reserve-only wave with 180 shots.
 first.reserve=15
 for slot,units in zip(sorted(first.slots,key=lambda s:s.damage_position),
                       [6,6,6,6,6,7,7]):
  slot.units=units
  slot.damage=units
 first.ammo_pool_shots=49
 second.reserve=60
 second.ammo_pool_shots=180
 before_damage={
  first.unit.wave_id:first.reserve_damage+sum(slot.damage for slot in first.slots),
  second.unit.wave_id:second.reserve_damage+sum(slot.damage for slot in second.slots),
 }
 events=[]; applied={}
 _prepare_round_start(
  waves,events,6,'attacker',applied,registry,rules,field,
 )
 first_positions=sorted(
  (slot.damage_position,slot.units) for slot in first.slots if slot.units)
 second_positions=sorted(
  (slot.damage_position,slot.units) for slot in second.slots if slot.units)
 assert first_positions==[(1,12),(2,12),(3,12),(4,12),(5,1)]
 assert second_positions==[(6,12),(7,12)]
 assert first.reserve==10
 assert second.reserve==36
 assert first.ammo_pool_shots==49
 assert second.ammo_pool_shots==180
 assert any(
  event.type=='ammo_limited_deployment'
  and event.details.get('wave_id')==second.unit.wave_id
  and event.details.get('deployed_units')==24
  and event.details.get('reserve_units')==36
  for event in events
 )
 assert first.reserve_damage+sum(slot.damage for slot in first.slots)==before_damage[first.unit.wave_id]
 assert second.reserve_damage+sum(slot.damage for slot in second.slots)==before_damage[second.unit.wave_id]
 assert any(
  event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  and event.details.get('line')=='second'
  and event.details.get('from_wave_id')==first.unit.wave_id
  and event.details.get('to_wave_id')==second.unit.wave_id
  for event in events
 )
 assert _cross_wave_rebuild_requirements(waves,registry,rules,field)==[]


def test_exhausted_earlier_long_range_releases_second_slots_to_later_ammo_wave():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'sulphur_carabineer','quantity':60,
   'entry_batch_id':'attacker-batch-1'},
  {'unit_id':'sulphur_carabineer','quantity':60,
   'entry_batch_id':'attacker-batch-2'},
 ]}),registry,field)
 first=next(w for w in waves if w.unit.batch_id=='attacker-batch-1')
 second=next(w for w in waves if w.unit.batch_id=='attacker-batch-2')
 assert sorted(slot.damage_position for slot in first.slots if slot.units)==[1,2,3,4,5]
 assert sorted(slot.damage_position for slot in second.slots if slot.units)==[6,7]
 assert second.reserve==36
 first.ammo_pool_shots=0
 second.ammo_pool_shots=180

 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,6,'attacker',applied,registry,rules,field,
 )
 assert boundary is False
 assert {slot.line for slot in first.slots if slot.units}=={'first'}
 assert sum(slot.units for slot in first.slots if slot.line=='first')==60
 assert sum(slot.units for slot in second.slots if slot.line=='second')==60
 assert second.reserve==0
 assert sorted(
  slot.damage_position for slot in second.slots
  if slot.line=='second' and slot.units
 )==[1,2,3,4,5]
 assert second.ammo_pool_shots==180
 assert _cross_wave_rebuild_requirements(waves,registry,rules,field)==[]


def test_initial_and_round_start_same_unit_precedence_do_not_swap_full_slots():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 army=Army.from_dict({'units':[
  {'unit_id':'sulphur_carabineer','quantity':12,
   'entry_batch_id':'batch-a','wave_id':'wave-z'},
  {'unit_id':'sulphur_carabineer','quantity':12,
   'entry_batch_id':'batch-b','wave_id':'wave-a'},
 ]})
 assert [item.batch_id for item in army.units]==['batch-a','batch-b']
 waves=deploy(army,registry,field)
 before={
  slot.damage_position:wave.unit.wave_id
  for wave in waves for slot in wave.slots if slot.units
 }
 assert before=={1:'wave-z',2:'wave-a'}
 events=[]; applied={}
 _prepare_round_start(
  waves,events,1,'attacker',applied,registry,rules,field,
 )
 after={
  slot.damage_position:wave.unit.wave_id
  for wave in waves for slot in wave.slots if slot.units
 }
 assert after==before
 assert not any(
  event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  for event in events
 )


def test_same_unit_multiple_initial_waves_on_one_line_are_supported():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'sulphur_carabineer','quantity':24,
   'entry_batch_id':'batch-1'},
  {'unit_id':'sulphur_carabineer','quantity':24,
   'entry_batch_id':'batch-2'},
 ]}),registry,field)
 deployed=[wave for wave in waves if any(slot.units for slot in wave.slots)]
 assert len(deployed)==2
 assert 'UNKNOWN-MULTIPLE-TARGET-WAVES' not in _preflight(
  waves,registry,rules,field)


def test_uploaded_multi_batch_scenario_continues_past_round_five_cross_wave_boundary():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':6,
    'attacker':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':600,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'steam_giant','quantity':160,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'swordsman','quantity':280,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'sulphur_carabineer','quantity':132,
       'entry_batch_id':'attacker-batch-1','attack_upgrade':3},
      {'unit_id':'sulphur_carabineer','quantity':60,
       'entry_batch_id':'attacker-batch-2','attack_upgrade':3},
    ]},
    'defender':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':500,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'steam_giant','quantity':192,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'steam_giant','quantity':128,'entry_batch_id':'defender-batch-2'},
      {'unit_id':'swordsman','quantity':320,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'sulphur_carabineer','quantity':156,
       'entry_batch_id':'defender-batch-1'},
    ]}}
 result=simulate(s)
 assert result['rounds_completed']>=6
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
  and any(
   req.get('wave_id')=='attacker-batch-2::sulphur_carabineer'
   for req in event['details'].get('requirements',[])
  )
  for event in result['events']
 )
 assert any(
  event['type']=='slot_handoff'
  and event['details'].get('reason')=='same_unit_same_line_wave_replacement'
  and event['details'].get('to_wave_id')=='attacker-batch-2::sulphur_carabineer'
  for event in result['events']
 )


def test_same_batch_heavy_front_compacts_across_mixed_waves_without_internal_gap():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 hoplite=Wave(
  ArmyUnit('hoplite',46,'hop',entry_batch_id='batch-1'),0,
  [
   Slot('first-1','first',field.lines['first'].physical_position(1),1,
        'hoplite','hop',32,50,100),
   Slot('first-2','first',field.lines['first'].physical_position(2),2,
        'hoplite','hop',14,50,200),
  ],
 )
 steam=Wave(
  ArmyUnit('steam_giant',68,'steam',entry_batch_id='batch-1'),8,
  [
   Slot('first-3','first',field.lines['first'].physical_position(3),3,
        'steam_giant','steam',11,16,300),
   Slot('first-4','first',field.lines['first'].physical_position(4),4,
        'steam_giant','steam',11,16,400),
   Slot('first-5','first',field.lines['first'].physical_position(5),5,
        'steam_giant','steam',12,16,500),
   Slot('first-6','first',field.lines['first'].physical_position(6),6,
        'steam_giant','steam',13,16,600),
   Slot('first-7','first',field.lines['first'].physical_position(7),7,
        'steam_giant','steam',13,16,700),
  ],
  reserve_damage=800,
 )
 before_damage={
  'hop':hoplite.reserve_damage+sum(slot.damage for slot in hoplite.slots),
  'steam':steam.reserve_damage+sum(slot.damage for slot in steam.slots),
 }
 events=[]; applied={}
 _prepare_round_start(
  [hoplite,steam],events,5,'attacker',applied,registry,rules,field,
 )
 by_position={
  slot.damage_position:slot
  for wave in (hoplite,steam) for slot in wave.slots
 }
 assert by_position[1].wave_id=='hop'
 assert by_position[1].units==46
 assert by_position[2].wave_id=='steam'
 assert [by_position[position].units for position in (2,3,4,5,6,7)]==[
  16,16,16,16,4,0
 ]
 assert hoplite.reserve==0 and steam.reserve==0
 assert hoplite.reserve_damage+sum(slot.damage for slot in hoplite.slots)==before_damage['hop']
 assert steam.reserve_damage+sum(slot.damage for slot in steam.slots)==before_damage['steam']
 assert any(
  event.type=='slot_handoff'
  and event.details.get('damage_position')==2
  and event.details.get('from_wave_id')=='hop'
  and event.details.get('to_wave_id')=='steam'
  for event in events
 )


def test_round_five_debug_scenario_keeps_center_first_heavy_front_contiguous():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':5,
    'attacker':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':350,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'steam_giant','quantity':112,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'swordsman','quantity':280,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'sulphur_carabineer','quantity':132,'entry_batch_id':'attacker-batch-1'},
    ]},
    'defender':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':350,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'steam_giant','quantity':128,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'swordsman','quantity':320,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'sulphur_carabineer','quantity':156,'entry_batch_id':'defender-batch-1'},
    ]}}
 result=simulate(s)
 round5=next(row for row in result['rounds'] if row['round']==5)
 attacker_front={
  slot['damage_position']:slot
  for slot in round5['attacker']['slots'] if slot['line']=='first'
 }
 # Regression from ikariam-round-5-debug.json: damage position 2 used to be
 # absent while an outer Steam-Giant slot at position 7 still held the tail.
 assert 2 in attacker_front
 assert any(
  event['type']=='slot_handoff'
  and event['round']==5
  and event['side']=='attacker'
  and event['details'].get('damage_position')==2
  and event['details'].get('to_unit_id')=='steam_giant'
  for event in result['events']
 )


def test_same_unit_cross_batch_heavy_replacement_prevents_premature_round_end_loss():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'attack_upgrade':200}]},
    'defender':{'units':[
      {'unit_id':'steam_giant','quantity':30,
       'wave_id':'front','entry_batch_id':'d-batch-1'},
      {'unit_id':'steam_giant','quantity':10,
       'wave_id':'reserve','entry_batch_id':'d-batch-2'},
    ]}}
 result=simulate(s)
 assert result['rounds_completed']>=2
 assert not any(
  event['type']=='battle_termination'
  and event['round']==1
  and event['details'].get('losing_side')=='defender'
  for event in result['events']
 )
 assert any(
  event['type']=='slot_handoff'
  and event['round']==2
  and event['side']=='defender'
  and event['details'].get('reason')=='same_unit_same_line_wave_replacement'
  and event['details'].get('to_wave_id')=='reserve'
  for event in result['events']
 )


def test_same_batch_heavy_reserve_takes_over_open_front_slots_and_battle_continues():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':3,
    'attacker':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':500,'entry_batch_id':'attacker-batch-1','arrival_round':0},
      {'unit_id':'steam_giant','quantity':48,'entry_batch_id':'attacker-batch-1','arrival_round':0},
      {'unit_id':'swordsman','quantity':280,'entry_batch_id':'attacker-batch-1','arrival_round':0},
      {'unit_id':'sulphur_carabineer','quantity':36,'entry_batch_id':'attacker-batch-1','arrival_round':0},
    ]},
    'defender':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':500,'entry_batch_id':'defender-batch-1','arrival_round':0},
      {'unit_id':'steam_giant','quantity':48,'entry_batch_id':'defender-batch-1','arrival_round':0},
      {'unit_id':'swordsman','quantity':280,'entry_batch_id':'defender-batch-1','arrival_round':0},
      {'unit_id':'sulphur_carabineer','quantity':24,'entry_batch_id':'defender-batch-1','arrival_round':0},
    ]}}
 result=simulate(s)
 assert result['rounds_completed']>=3
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
  and event['round']<=2
  for event in result['events']
 )
 round3=next(row for row in result['rounds'] if row['round']==3)
 attacker_steam=[
  slot for slot in round3['attacker']['slots']
  if slot['line']=='first' and slot['unit_id']=='steam_giant'
 ]
 defender_steam=[
  slot for slot in round3['defender']['slots']
  if slot['line']=='first' and slot['unit_id']=='steam_giant'
 ]
 assert attacker_steam and defender_steam
 assert all(slot['capacity']==16 for slot in attacker_steam+defender_steam)
 assert any(
  event['type']=='slot_handoff'
  and event['details'].get('reason')=='same_batch_heavy_front_replacement'
  for event in result['events']
 )
 assert any(
  event['type']=='attacking_matrix'
  and event['round']==3
  and event['details'].get('unit_id')=='steam_giant'
  for event in result['events']
 )


def test_different_entry_batch_heavy_reserve_still_hits_cross_wave_boundary():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a-hop','arrival_round':0},
      {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'a-steam','arrival_round':0},
    ]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90}]}}
 result=simulate(s)
 # Different arrival batches are intentionally not covered by the narrow
 # same-batch heavy handoff rule.
 assert any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
  for event in result['events']
 )


def test_reserve_light_fallback_candidate_does_not_block_a_full_front_at_preflight():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90},
                         {'unit_id':'swordsman','quantity':30}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert result['initial_state']['defender']['reserve']['swordsman']==30
 preflight=[e for e in result['events'] if e['type']=='unsupported_mechanic' and e['round']==0]
 assert not any(e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' for e in preflight)
 assert any(e['type']=='attacking_matrix' for e in result['events'])


def test_round_start_moves_whole_light_wave_from_flank_into_open_first_slots():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'steam_giant','quantity':224},
  {'unit_id':'swordsman','quantity':240},
 ]}),registry,field)
 steam=next(w for w in waves if w.unit.unit_id=='steam_giant')
 swords=next(w for w in waves if w.unit.unit_id=='swordsman')
 steam.reserve=0
 for slot in steam.slots:
  slot.units=16 if slot.damage_position in {1,2,3} else 0
  slot.damage=0
 swords.reserve=0
 for slot in swords.slots:
  slot.units=40 if slot.damage_position in {1,2,3} else 0
  slot.damage=210 if slot.damage_position in {2,3} else 0
 before_damage=sum(slot.damage for slot in swords.slots)
 events=[]; applied={}
 _prepare_round_start(waves,events,4,'defender',applied,registry,rules,field)
 assert sum(slot.units for slot in swords.slots)==120
 assert {slot.line for slot in swords.slots if slot.units}=={'first'}
 assert [slot.damage_position for slot in swords.slots if slot.units]==[4,5,6]
 assert swords.reserve==0
 assert swords.reserve_damage+sum(slot.damage for slot in swords.slots)==before_damage
 assert any(
  event.type=='formation_fallback'
  and event.side=='defender'
  and event.details.get('unit_id')=='swordsman'
  and event.details.get('to_line')=='first'
  and event.details.get('whole_wave') is True
  for event in events
 )


def test_light_fallback_preserves_damage_owned_by_replaced_empty_first_slot():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':350,'wave_id':'front'},
  {'unit_id':'swordsman','quantity':240,'wave_id':'light'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 light=next(w for w in waves if w.unit.wave_id=='light')
 front.reserve=0
 for slot in front.slots:
  slot.units=slot.capacity if slot.damage_position in {1,2,3} else 0
  slot.damage=0
 # Position 4 is empty after compaction but still owns persistent damage from
 # the surviving Hoplite wave. The Light fallback will reuse this position.
 next(slot for slot in front.slots if slot.damage_position==1).damage=1136
 next(slot for slot in front.slots if slot.damage_position==4).damage=424
 light.reserve=0
 for slot in light.slots:
  slot.units=slot.capacity if slot.damage_position in {1,2,3} else 0
  slot.damage=0
 before_by_wave={
  wave.unit.wave_id: wave.reserve_damage+sum(slot.damage for slot in wave.slots)
  for wave in waves
 }
 assert before_by_wave=={'front':1560,'light':0}
 events=[]; applied={}
 _prepare_round_start(waves,events,3,'defender',applied,registry,rules,field)
 after_by_wave={
  wave.unit.wave_id: wave.reserve_damage+sum(slot.damage for slot in wave.slots)
  for wave in waves
 }
 assert after_by_wave==before_by_wave
 assert sum(after_by_wave.values())==1560
 assert {slot.line for slot in light.slots if slot.units}=={'first'}
 assert 4 in {slot.damage_position for slot in light.slots if slot.units}


def test_comprehensive_preset_does_not_stop_at_round_four_when_swordsmen_can_fill_first():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':5,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':700,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'swordsman','quantity':480,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'sulphur_carabineer','quantity':168,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'mortar','quantity':60,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'bombardier','quantity':60,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'gyrocopter','quantity':120,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'cook','quantity':15,'entry_batch_id':'attacker-batch-1'},
   {'unit_id':'doctor','quantity':15,'entry_batch_id':'attacker-batch-1'},
  ]},
  'defender':{'forge_level':5,'units':[
   {'unit_id':'steam_giant','quantity':224,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'swordsman','quantity':480,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'archer','quantity':700,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'catapult','quantity':60,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'bombardier','quantity':60,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'gyrocopter','quantity':120,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'cook','quantity':15,'entry_batch_id':'defender-batch-1'},
   {'unit_id':'doctor','quantity':15,'entry_batch_id':'defender-batch-1'},
  ]},
 }
 result=simulate(s)
 assert result['rounds_completed']>=5
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['round']==4
  and event['details'].get('rule_id')=='UNKNOWN-FORMATION-FALLBACK'
  for event in result['events']
 )
 assert any(
  event['type']=='formation_fallback'
  and event['round']==4
  and event['side']=='defender'
  and event['details'].get('unit_id')=='swordsman'
  and event['details'].get('to_line')=='first'
  for event in result['events']
 )


def test_light_fallback_releases_native_slots_for_later_same_unit_wave():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'steam_giant','quantity':224,'wave_id':'heavy'},
  {'unit_id':'swordsman','quantity':100,'wave_id':'s1'},
  {'unit_id':'swordsman','quantity':200,'wave_id':'s2'},
 ]}),registry,field)
 heavy=next(w for w in waves if w.unit.wave_id=='heavy')
 s1=next(w for w in waves if w.unit.wave_id=='s1')
 s2=next(w for w in waves if w.unit.wave_id=='s2')
 heavy.reserve=0
 for slot in heavy.slots:
  slot.units=16 if slot.damage_position in {1,2,3} else 0
  slot.damage=0
 # Initial deployment already gives s1 40/40/20 in native center slots.
 assert sum(slot.units for slot in s1.slots)==100
 s1.reserve=0
 s2.reserve=80
 for slot in s2.slots:
  slot.units=40 if slot.damage_position in {4,5,6} else 0
 events=[]; applied={}
 _prepare_round_start(waves,events,4,'defender',applied,registry,rules,field)
 assert {slot.line for slot in s1.slots if slot.units}=={'first'}
 flank=[slot for slot in s2.slots if slot.line=='flank' and slot.units]
 assert [slot.damage_position for slot in flank]==[1,2,3,4,5]
 assert all(slot.units==40 for slot in flank)
 assert s2.reserve==0


def test_reserve_only_light_wave_does_not_bypass_cross_wave_rebuild_boundary():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-mini']
 heavy=Wave(
  ArmyUnit('hoplite',30,'heavy'),0,
  [Slot('first-1','first',2,1,'hoplite','heavy',0,30,0)],
 )
 swords=Wave(ArmyUnit('swordsman',30,'reserve-light'),30,[])
 events=[]; applied={}
 _prepare_round_start([heavy,swords],events,2,'defender',applied,registry,rules,field)
 assert swords.slots==[]
 assert swords.reserve==30
 requirements=_cross_wave_rebuild_requirements([heavy,swords],registry,rules,field)
 assert any(
  row['unit_id']=='swordsman'
  and row['wave_id']=='reserve-light'
  and row['runtime_line']=='first'
  for row in requirements
 )


def test_partial_light_cross_line_fallback_remains_guarded():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'steam_giant','quantity':224},
  {'unit_id':'swordsman','quantity':240},
 ]}),registry,field)
 steam=next(w for w in waves if w.unit.unit_id=='steam_giant')
 swords=next(w for w in waves if w.unit.unit_id=='swordsman')
 steam.reserve=0
 for slot in steam.slots:
  slot.units=16 if slot.damage_position in {1,2,3} else 0
 swords.reserve=0
 # 240 surviving Swordsmen need five First slots, but only four are open.
 for slot in swords.slots:
  slot.units=40
 events=[]; applied={}
 _prepare_round_start(waves,events,4,'defender',applied,registry,rules,field)
 assert {slot.line for slot in swords.slots if slot.units}=={'flank'}
 assert not any(event.type=='formation_fallback' for event in events)


def test_unrelated_reserve_is_not_cross_wave_rebuild_candidate():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 deployed=target_wave('hoplite','first',30)
 reserve=Wave(ArmyUnit('catapult',6,'reserve'),6)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  [deployed,reserve],registry,rules,LAND_MINI)


def test_support_only_state_is_not_cross_wave_rebuild_candidate():
 registry=UnitRegistry.load()
 waves=deploy(Army.from_dict({'units':[{'unit_id':'doctor','quantity':4}]}),registry,LAND_MINI)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  waves,registry,FormationRules.load(),LAND_MINI)


def test_domain_and_unsupported_geometry_rejections():
 s=scenario(); s['attacker']['units']=[{'unit_id':'rocket_ship','quantity':1}]
 with pytest.raises(ScenarioError): simulate(s)
 s=scenario(); s['battlefield']='naval-mini'
 with pytest.raises(ScenarioError,match='reserved'): simulate(s)


def test_land_medium_homogeneous_combat_uses_seven_front_slots_and_fires():
 s={'policy':'experimental','battlefield':'land-medium','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':210}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':210}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert len([slot for slot in result['initial_state']['attacker']['slots'] if slot['line']=='first'])==7
 assert any(event['type']=='attacking_matrix' for event in result['events'])
 assert 'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS' not in {
  event['details'].get('rule_id') for event in result['events']}


def test_larger_field_multiline_light_wave_remains_guarded():
 s={'policy':'experimental','battlefield':'land-small','max_rounds':1,
    'attacker':{'units':[{'unit_id':'swordsman','quantity':180}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':150}]}}
 result=simulate(s)
 assert {slot['line'] for slot in result['initial_state']['attacker']['slots']}=={'first','flank'}
 assert result['rounds_completed']==0
 assert 'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS' in {
  event['details'].get('rule_id') for event in result['events']}


def test_typed_scenario_army_order_is_canonical_for_mixed_front_combat():
 hoplite=ArmyUnit('hoplite',1,'wave-1',entry_batch_id='batch-1')
 steam=ArmyUnit('steam_giant',100,'wave-1',entry_batch_id='batch-1')
 defender=Army((ArmyUnit('hoplite',60,'wave-1',entry_batch_id='batch-1'),),0,'player')
 first=simulate(Scenario(
  attacker=Army((hoplite,steam),0,'player'),defender=defender,
  policy=Policy.EXPERIMENTAL,battlefield='land-max',max_rounds=1,
 ))
 reversed_order=simulate(Scenario(
  attacker=Army((steam,hoplite),0,'player'),defender=defender,
  policy=Policy.EXPERIMENTAL,battlefield='land-max',max_rounds=1,
 ))
 parsed=simulate({
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':1},
   {'unit_id':'steam_giant','quantity':100},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':60}]},
 })
 assert first==reversed_order
 assert first==parsed


def test_larger_field_mixed_heavy_and_light_front_executes_one_shared_am():
 s={'policy':'experimental','battlefield':'land-medium','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':30},
                         {'unit_id':'swordsman','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':210}]}}
 result=simulate(s)
 rules={event['details'].get('rule_id') for event in result['events']
        if event['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' not in rules
 assert result['rounds_completed']==1
 matrices=[event for event in result['events']
           if event['type']=='attacking_matrix' and event['side']=='attacker'
           and event['details'].get('firing_phase')=='first']
 assert {event['details']['unit_id'] for event in matrices}=={'hoplite','swordsman'}


def test_larger_field_cross_wave_reserve_candidate_waits_while_line_is_full():
 s={'policy':'experimental','battlefield':'land-small','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':150,'wave_id':'a'},
                         {'unit_id':'hoplite','quantity':1,'wave_id':'b'}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':150}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in {
  event['details'].get('rule_id') for event in result['events'] if event['round']==0}


def test_snapshots_preserve_line_positions_and_ammo_pool():
 r=simulate(scenario('strict')); slot=next(s for s in r['initial_state']['attacker']['slots'] if s['damage_position']==1)
 assert (slot['line'],slot['physical_position'])==('first',2)
 assert 'ammo_pool_shots' in slot


def test_tooltip_hp_is_derived_from_current_survivors_only():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load(); hp=registry.get('hoplite').hit_points
 wave=Wave(ArmyUnit('hoplite',12,'batch'),0,[Slot('first-1','first',2,1,'hoplite','batch',10,30,2*hp)],
           ammo_capacity_shots=None)
 slot=_snapshot([wave],registry,BattleEndProfile.load())['slots'][0]
 assert slot['hit_points_percent']==80


def test_tooltip_ammo_is_shared_wave_derived_state():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load()
 wave=Wave(ArmyUnit('sulphur_carabineer',14,'batch'),0,[
  Slot('second-1','second',2,1,'sulphur_carabineer','batch',7,7),
  Slot('second-2','second',1,2,'sulphur_carabineer','batch',7,7)],
  ammo_pool_shots=21,ammo_capacity_shots=42)
 state=_snapshot([wave],registry,BattleEndProfile.load())
 assert [slot['munition_percent'] for slot in state['slots']]==[50,50]
 assert state['waves'][0]['munition_percent']==50


def test_support_and_air_survive_but_main_can_retarget_artillery_after_front_dies():
 for unit,quantity in [('doctor',4),('gyrocopter',10)]:
  s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
     'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
     'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':unit,'quantity':quantity}]}}
  result=simulate(s); state=result['final_state']['defender']
  assert result['outcome']=='attacker' and result['rounds_completed']==1
  assert state['remaining'][unit]==quantity and state['main_line_holding_total']==0
  assert state['fallback_candidate_total']==0 and state['continuation_state']=='not_sustaining'
  assert result['casualties']['defender'].get(unit,0)==0
  event=next(e for e in result['events'] if e['type']=='battle_termination')
  assert event['details']['surviving_non_sustaining']['defender']=={unit:quantity}

 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'catapult','quantity':6}]}}
 result=simulate(s)
 assert result['outcome']=='attacker' and result['rounds_completed']==1
 assert result['final_state']['defender']['remaining'].get('catapult',0)==0
 assert result['casualties']['defender'].get('catapult')==6
 catapult_hits=[e for e in result['events'] if e['type']=='damage'
                and e['side']=='attacker' and e['details'].get('target_unit_id')=='catapult']
 assert catapult_hits and {e['details']['firing_phase'] for e in catapult_hits}=={'first'}


def test_initial_long_range_requires_fallback_and_is_not_sustaining():
 s={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'sulphur_carabineer','quantity':7}]}}
 result=simulate(s)
 assert result['initial_state']['defender']['main_line_holding_total']==0
 assert result['initial_state']['defender']['fallback_candidate_total']==7
 assert result['initial_state']['defender']['continuation_state']=='fallback_required'
 assert 'UNKNOWN-FORMATION-FALLBACK' in {e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}


def test_final_sustaining_unit_dies_in_round_two_without_empty_round_three():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':10}]}}
 result=simulate(s)
 assert result['outcome']=='attacker' and result['rounds_completed']==2
 assert max(round_state['round'] for round_state in result['rounds'])==2


def test_initial_non_sustaining_timing_is_strict_boundary_and_named_experimental_policy():
 s={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'doctor','quantity':4}]}}
 strict=simulate(s)
 assert 'UNKNOWN-INITIAL-BATTLE-END-TIMING' in {e['details']['rule_id'] for e in strict['events'] if e['type']=='unsupported_mechanic'}
 s['policy']='experimental'; experimental=simulate(s)
 assert experimental['outcome']=='attacker' and experimental['rounds_completed']==0
 assert [a['id'] for a in experimental['assumptions']].count('EXP-BATTLE-END-ROUND-BOUNDARY-001')==1


def test_front_alive_with_carabineer_is_sustaining():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90},{'unit_id':'sulphur_carabineer','quantity':7}]}}
 state=simulate(s)['rounds'][1]['defender']
 assert state['main_line_holding_total']>0 and state['fallback_candidate_total']==7
 assert state['continuation_state']=='sustaining'


def test_dynamic_front_collapse_retargets_later_main_shots_into_long_range():
 quantity=7
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},
                         {'unit_id':'sulphur_carabineer','quantity':quantity}]}}
 result=simulate(s); state=result['final_state']['defender']
 assert result['status']=='completed' and result['outcome']=='attacker'
 assert result['rounds_completed']==1 and state['continuation_state']=='not_sustaining'
 assert state['fallback_candidate_total']==0
 assert result['casualties']['defender'].get('sulphur_carabineer')==quantity
 assert any(e['type']=='damage' and e['side']=='defender'
            and e['details'].get('source_unit_id')=='sulphur_carabineer'
            and e['details'].get('firing_phase')=='second' for e in result['events'])
 assert any(e['type']=='damage' and e['side']=='attacker'
            and e['details'].get('target_unit_id')=='sulphur_carabineer'
            and e['details'].get('firing_phase')=='first' for e in result['events'])


def test_mixed_runtime_front_is_represented_and_fires_by_runtime_line():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':8},{'unit_id':'swordsman','quantity':30}]}}
 result=simulate(s); front=result['initial_state']['defender']['slots']
 assert {(slot['unit_id'],slot['line']) for slot in front}=={('hoplite','first'),('swordsman','first')}
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' not in rules
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 assert result['rounds_completed']==1
 assert {'hoplite','swordsman'} <= {
  e['details']['unit_id'] for e in result['events']
  if e['type']=='attacking_matrix' and e['side']=='defender'
  and e['details'].get('firing_phase')=='first'
 }


def test_both_sides_without_main_line_is_not_an_unqualified_draw():
 s={'policy':'experimental','battlefield':'land-mini',
    'attacker':{'units':[{'unit_id':'doctor','quantity':1}]},
    'defender':{'units':[{'unit_id':'catapult','quantity':1}]}}
 result=simulate(s)
 assert result['status']=='inconclusive' and result['outcome']=='inconclusive'
 assert 'UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME' in {e['details'].get('rule_id') for e in result['events']}


def test_round_cap_emits_explicit_safety_event():
 s=scenario(rounds=2)
 s['attacker']['units'][0]['quantity']=100000
 s['defender']['units'][0]['quantity']=100000
 result=simulate(s)
 cap=[e for e in result['events'] if e['type']=='safety_limit_reached']
 assert result['status']=='inconclusive' and result['outcome']=='inconclusive'
 assert result['rounds_completed']==2
 assert len(cap)==1 and cap[0]['round']==2
 assert cap[0]['details']=={'reason':'max_rounds_reached','limit':2}


def test_round_combat_statistics_track_dealt_taken_and_cumulative_damage():
 result=simulate(scenario())
 assert result['rounds'][0]['combat_statistics']['attacker']=={
  'damage_dealt':0,'damage_taken':0,'cumulative_damage_dealt':0,'cumulative_damage_taken':0,
  'healing':0,'cumulative_healing':0,
 }
 assert result['rounds'][0]['combat_statistics']['defender']=={
  'damage_dealt':0,'damage_taken':0,'cumulative_damage_dealt':0,'cumulative_damage_taken':0,
  'healing':0,'cumulative_healing':0,
 }
 prev={'attacker':(0,0),'defender':(0,0)}
 for row in result['rounds']:
  stats=row['combat_statistics']
  assert stats['attacker']['damage_dealt']==stats['defender']['damage_taken']
  assert stats['defender']['damage_dealt']==stats['attacker']['damage_taken']
  for side in ('attacker','defender'):
   assert stats[side]['cumulative_damage_dealt']>=prev[side][0]
   assert stats[side]['cumulative_damage_taken']>=prev[side][1]
   prev[side]=(stats[side]['cumulative_damage_dealt'],stats[side]['cumulative_damage_taken'])
 final=result['rounds'][-1]['combat_statistics']
 for side in ('attacker','defender'):
  assert final[side]['cumulative_damage_dealt']==result['combat_statistics'][side]['gross_damage_dealt']
  assert final[side]['cumulative_damage_taken']==result['combat_statistics'][side]['gross_damage_taken']
  assert result['combat_statistics'][side]['gross_healing']==0


def test_doctor_healing_executes_full_clear_subset_and_reports_real_amount():
 s=scenario(); s['attacker']['units'].append({'unit_id':'doctor','quantity':100}); result=simulate(s)
 healing=result['healing_status']
 assert healing['modeled'] is False
 assert healing['partial_model'] is True
 assert healing['model_status']=='EXACT_FULL_CLEAR_SUBSET_ONLY'
 assert healing['derived_capacity_per_doctor']==4000
 assert healing['capacity_is_allocation_formula'] is False
 assert healing['timing_contract']=='per_round_before_next_round_combat'
 assert healing['healing_rr_order']=='UNKNOWN_EXCEPT_FULL_CLEAR_IS_ORDER_INVARIANT'
 side=healing['sides']['attacker']
 assert side['doctor_count']==100
 assert side['status']=='applied_exact_subset'
 assert side['effect_applied'] is True
 assert side['healing_amount']>0
 assert side['engine_healing_applied']==side['healing_amount']
 assert 'EXP-HEAL-NONE-001' not in {a['id'] for a in result['assumptions']}
 assert result['combat_statistics']['attacker']['gross_healing']==side['healing_amount']
 assert result['combat_statistics']['attacker']['engine_healing_applied']==side['healing_amount']
 doctor_events=[
  e for e in result['events']
  if e['type']=='healing' and e['side']=='attacker'
  and e['details'].get('support_unit_id')=='doctor'
 ]
 assert doctor_events
 assert sum(e['details'].get('healing',0) for e in doctor_events)==side['healing_amount']
 assert any(row['combat_statistics']['attacker']['healing']>0 for row in result['rounds'])
 assert result['rounds'][-1]['combat_statistics']['attacker']['cumulative_healing']==side['healing_amount']

 strict=scenario('strict'); strict['attacker']['units'].append({'unit_id':'doctor','quantity':2}); blocked=simulate(strict)
 assert blocked['healing_status']['sides']['attacker']['status']=='unsupported_boundary'
 assert blocked['healing_status']['sides']['attacker']['healing_amount'] is None


def test_doctor_healing_full_clear_only_affects_human_combat_damage():
 registry=UnitRegistry.load(); support=SupportProfile.load()
 doctor=Wave(ArmyUnit('doctor',1,'doctor'),0,[],0,None,1)
 hoplite=Wave(ArmyUnit('hoplite',30,'hop'),0,
              [Slot('first-1','first',2,1,'hoplite','hop',30,30,1000)])
 steam=Wave(ArmyUnit('steam_giant',10,'steam'),0,
            [Slot('first-2','first',3,2,'steam_giant','steam',10,10,1000)])
 events=[]; applied={}
 _prepare_round_start(
  [doctor,hoplite,steam],events,2,'attacker',applied,
  registry=registry,support=support,
 )
 assert hoplite.slots[0].damage==0
 assert steam.slots[0].damage==1000
 heal=next(event for event in events if event.type=='healing')
 assert heal.details['healing']==1000
 assert heal.details['capacity']==4000
 assert heal.details['affected_units']=={'hoplite':1000}
 assert heal.details['eligibility']=='land_human_combat'
 assert 'EXP-HEAL-NONE-001' not in applied


def test_doctor_healing_reports_distinct_unit_state_identities_for_same_wave_id():
 registry=UnitRegistry.load(); support=SupportProfile.load()
 doctor=Wave(ArmyUnit('doctor',1,'doctor'),0,[],0,None,1)
 hoplite=Wave(ArmyUnit('hoplite',30,'wave-1'),0,
              [Slot('first-1','first',2,1,'hoplite','wave-1',30,30,100)])
 swords=Wave(ArmyUnit('swordsman',30,'wave-1'),0,
             [Slot('flank-1','flank',2,1,'swordsman','wave-1',30,30,200)])
 events=[]; applied={}
 _prepare_round_start(
  [doctor,hoplite,swords],events,2,'attacker',applied,
  registry=registry,support=support,
 )
 heal=next(event for event in events if event.type=='healing')
 assert heal.details['healing']==300
 assert heal.details['affected_units']=={'hoplite':100,'swordsman':200}
 assert heal.details['affected_waves']==[
  {'unit_id':'hoplite','wave_id':'wave-1','healing':100},
  {'unit_id':'swordsman','wave_id':'wave-1','healing':200},
 ]
 assert hoplite.slots[0].damage==0
 assert swords.slots[0].damage==0


def test_doctor_partial_healing_stays_named_assumption_when_capacity_is_insufficient():
 registry=UnitRegistry.load(); support=SupportProfile.load()
 doctor=Wave(ArmyUnit('doctor',1,'doctor'),0,[],0,None,1)
 hoplite=Wave(ArmyUnit('hoplite',30,'hop'),0,
              [Slot('first-1','first',2,1,'hoplite','hop',30,30,5000)])
 events=[]; applied={}
 _prepare_round_start(
  [doctor,hoplite],events,2,'attacker',applied,
  registry=registry,support=support,
 )
 assert hoplite.slots[0].damage==5000
 assert 'EXP-HEAL-NONE-001' in applied
 unresolved=next(event for event in events if event.type=='healing_allocation_unresolved')
 assert unresolved.details['capacity']==4000
 assert unresolved.details['eligible_damage']==5000
 assert unresolved.details['action']=='no_partial_healing_applied'
 assert not any(event.type=='healing' for event in events)




def test_tender_full_clear_uses_current_4000_capacity_for_naval_damage():
 registry=UnitRegistry.load(); support=SupportProfile.load()
 tender=Wave(ArmyUnit('tender',1,'tender'),0,[],0,None,1)
 ram=Wave(
  ArmyUnit('ram_ship',10,'ram'),0,
  [Slot('flank-1','flank',2,1,'ram_ship','ram',10,10,3500)],
 )
 events=[]; applied={}
 _prepare_round_start(
  [tender,ram],events,2,'attacker',applied,
  registry=registry,support=support,
 )
 assert ram.slots[0].damage==0
 heal=next(
  event for event in events
  if event.type=='healing' and event.details.get('support_unit_id')=='tender'
 )
 assert heal.details['tender_count']==1
 assert heal.details['capacity']==4000
 assert heal.details['healing']==3500
 assert heal.details['eligibility']=='all_naval_combat'
 assert 'EXP-TENDER-HEAL-NONE-001' not in applied


def test_tender_insufficient_capacity_does_not_invent_partial_allocation():
 registry=UnitRegistry.load(); support=SupportProfile.load()
 tender=Wave(ArmyUnit('tender',1,'tender'),0,[],0,None,1)
 ram=Wave(
  ArmyUnit('ram_ship',10,'ram'),0,
  [Slot('flank-1','flank',2,1,'ram_ship','ram',10,10,4500)],
 )
 events=[]; applied={}
 _prepare_round_start(
  [tender,ram],events,2,'attacker',applied,
  registry=registry,support=support,
 )
 assert ram.slots[0].damage==4500
 assert 'EXP-TENDER-HEAL-NONE-001' in applied
 assert applied['EXP-TENDER-HEAL-NONE-001']['description'].startswith('When Tender capacity cannot clear')
 unresolved=next(
  event for event in events
  if event.type=='healing_allocation_unresolved'
  and event.details.get('support_unit_id')=='tender'
 )
 assert unresolved.details['capacity']==4000
 assert unresolved.details['eligible_damage']==4500


def test_art_of_warfare_firing_order_profile_and_artillery_targets_are_exact():
 t=TargetingProfile.load()
 assert t.firing_order==('anti-balloon','balloon','third','flank','second','first')
 assert t.priorities['third']==('first','flank')
 assert 'second' not in t.priorities['third'] and 'third' not in t.priorities['third']


def test_user_observed_full_swordsman_flank_mkill_hypothesis_matches_round_one():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'swordsman','quantity':240,'attack_upgrade':24,'armor_upgrade':26},
  ]},
  'defender':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'swordsman','quantity':240,'attack_upgrade':18,'armor_upgrade':18},
  ]},
 }
 result=simulate(s)
 round_one=next(row for row in result['rounds'] if row['round']==1)

 def flank(state):
  return sorted(
   (slot for slot in state['slots'] if slot['line']=='flank'),
   key=lambda slot:slot['physical_position'],
  )

 attacker_flank=flank(round_one['attacker'])
 defender_flank=flank(round_one['defender'])

 assert [slot['casualties'] for slot in attacker_flank]==[18,21,21,21,21,18]
 assert [slot['casualties'] for slot in defender_flank]==[18,24,24,24,24,18]
 assert [slot['damage'] for slot in attacker_flank]==[0,42,42,42,42,0]
 assert [slot['damage'] for slot in defender_flank]==[0,12,12,12,12,0]
 assert [slot['hit_points_percent'] for slot in attacker_flank[1:5]]==[99.39]*4
 assert [slot['hit_points_percent'] for slot in defender_flank[1:5]]==[99.79]*4
 assert attacker_flank[0]['hit_points_percent']==100
 assert attacker_flank[-1]['hit_points_percent']==100
 assert defender_flank[0]['hit_points_percent']==100
 assert defender_flank[-1]['hit_points_percent']==100

 ids={item['id'] for item in result['assumptions']}
 assert 'EXP-SWORDSMAN-SYMMETRIC-2HIT-ROW-PM-MKILL-001' in ids
 modeled=[
  event for event in result['events']
  if event['type']=='damage'
  and event['details'].get('resolution')=='swordsman_symmetric_two_hit_row_pm_mkill'
 ]
 assert len(modeled)==8
 assert {event['details']['target_damage_position'] for event in modeled}=={1,2,3,4}
 assert all(set(event['details'].get('formation_source_column_hits',
                                     event['details']['source_column_hits']).values())=={7}
            for event in modeled)
 assert {
  (event['details']['baseline_casualties'],
   event['details']['casualties'],
   event['details']['recovered_overkill'],
   event['details']['persistent_damage'])
  for event in modeled if event['side']=='attacker'
 }=={(21,24,1092,12)}
 assert {
  (event['details']['baseline_casualties'],
   event['details']['casualties'],
   event['details']['recovered_overkill'],
   event['details']['persistent_damage'])
  for event in modeled if event['side']=='defender'
 }=={(21,21,42,42)}
 assert {
  (event['details']['mkill_hit_damage'],
   event['details']['mkill_retained_overkill_events'],
   event['details']['mkill_recovered_overkill'])
  for event in modeled if event['side']=='attacker'
 }=={(258,7,1092)}
 assert {
  (event['details']['mkill_hit_damage'],
   event['details']['mkill_retained_overkill_events'],
   event['details']['mkill_recovered_overkill'])
  for event in modeled if event['side']=='defender'
 }=={(183,7,42)}

 outer=[
  event for event in result['events']
  if event['type']=='damage'
  and event['details'].get('source_unit_id')=='swordsman'
  and event['details'].get('target_unit_id')=='swordsman'
  and event['details'].get('target_damage_position') in {5,6}
 ]
 assert len(outer)==4
 assert all(event['details']['resolution']=='sequential_d_kill_baseline' for event in outer)
 assert all(set(event['details']['source_column_hits'].values())=={6} for event in outer)


def test_swordsman_mkill_hypothesis_generalizes_by_damage_not_upgrade_fixture():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':1,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'swordsman','quantity':240,'attack_upgrade':23,'armor_upgrade':25},
  ]},
  'defender':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':350},
   {'unit_id':'swordsman','quantity':240,'attack_upgrade':17,'armor_upgrade':17},
  ]},
 }
 result=simulate(s)
 assert 'EXP-SWORDSMAN-SYMMETRIC-2HIT-ROW-PM-MKILL-001' in {
  item['id'] for item in result['assumptions']
 }
 modeled=[
  event for event in result['events']
  if event['type']=='damage'
  and event['details'].get('resolution')=='swordsman_symmetric_two_hit_row_pm_mkill'
 ]
 assert modeled
 assert all(set(event['details']['source_column_hits'].values())=={7} for event in modeled)
 assert all('baseline_overkill_discarded' in event['details'] for event in modeled)


def test_swordsman_full_flank_mkill_is_invariant_to_same_unit_wave_split():
 def make(split):
  swords=(
   [{'unit_id':'swordsman','quantity':240,'attack_upgrade':24,'armor_upgrade':26}]
   if not split else
   [
    {'unit_id':'swordsman','quantity':120,'wave_id':'s1','entry_batch_id':'b1',
     'attack_upgrade':24,'armor_upgrade':26},
    {'unit_id':'swordsman','quantity':120,'wave_id':'s2','entry_batch_id':'b2',
     'attack_upgrade':24,'armor_upgrade':26},
   ]
  )
  return {
   'policy':'experimental','battlefield':'land-max','max_rounds':1,
   'attacker':{'forge_level':5,'units':[
    {'unit_id':'hoplite','quantity':350},*swords,
   ]},
   'defender':{'forge_level':5,'units':[
    {'unit_id':'hoplite','quantity':350},
    {'unit_id':'swordsman','quantity':240,'attack_upgrade':18,'armor_upgrade':18},
   ]},
  }

 def signature(result):
  state=next(row for row in result['rounds'] if row['round']==1)['defender']
  return [
   (slot['physical_position'],slot['units'],slot['casualties'],
    slot['damage'],slot['hit_points_percent'])
   for slot in sorted(
    (slot for slot in state['slots'] if slot['line']=='flank'),
    key=lambda slot:slot['physical_position'],
   )
  ]

 single=simulate(make(False))
 split=simulate(make(True))
 assert signature(single)==signature(split)
 assert single['casualties']['defender']['swordsman']==split['casualties']['defender']['swordsman']


def test_flank_phase_can_kill_long_range_before_long_range_fires():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84}]}}
 result=simulate(s)
 assert result['casualties']['defender'].get('sulphur_carabineer')==84
 assert not any(e['type']=='damage' and e['side']=='defender'
                and e['details'].get('source_unit_id')=='sulphur_carabineer'
                for e in result['events'])


def test_artillery_fires_before_flank_and_hits_front_only_while_front_exists():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84},
                         {'unit_id':'mortar','quantity':30}]}}
 result=simulate(s)
 mortar_events=[e for e in result['events'] if e['type']=='damage'
                and e['side']=='defender' and e['details'].get('source_unit_id')=='mortar']
 assert mortar_events
 assert {e['details']['target_line'] for e in mortar_events}=={'first'}
 assert sum(e['details']['casualties'] for e in mortar_events)==30
 assert not any(e['type']=='damage' and e['side']=='defender'
                and e['details'].get('source_unit_id')=='sulphur_carabineer'
                for e in result['events'])
 phases=[e['details']['firing_phase'] for e in result['events']
         if e['type']=='formation_fire_phase']
 assert phases.index('third') < phases.index('flank')


def test_same_formation_both_sides_keep_phase_start_firing_eligibility():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]}}
 result=simulate(s)
 sword_damage=[e for e in result['events'] if e['type']=='damage'
               and e['details'].get('source_unit_id')=='swordsman']
 assert {e['side'] for e in sword_damage}=={'attacker','defender'}
 attacker_losses=result['casualties']['attacker'].get('swordsman',0)
 defender_losses=result['casualties']['defender'].get('swordsman',0)
 assert attacker_losses>0
 assert attacker_losses==defender_losses


def test_zero_quantity_support_rows_do_not_create_blockers_or_assumptions():
 for support,blocker,assumption,status_key,count_key in (
  ('doctor','UNKNOWN-HEALING-ALLOCATION','EXP-HEAL-NONE-001','healing_status','doctor_count'),
  ('cook','UNKNOWN-MORALE-SUPPORT','EXP-MORALE-NONE-001','morale_status','cook_count'),
 ):
  s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
     'attacker':{'units':[{'unit_id':'hoplite','quantity':30},
                          {'unit_id':support,'quantity':0}]},
     'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
  result=simulate(s)
  rules={e['details'].get('rule_id') for e in result['events']
         if e['type']=='unsupported_mechanic'}
  ids={a['id'] for a in result['assumptions']}
  assert blocker not in rules
  assert assumption not in ids
  side=result[status_key]['sides']['attacker']
  assert side[count_key]==0 and side['status']=='not_present'


def test_mixed_source_am_merges_columns_in_row_major_order():
 volleys=[
  {'source_unit':'catapult','row_numbers':[1,1,2,2],
   'source_damage_positions':[1,2,1,2]},
  {'source_unit':'battering_ram','row_numbers':[1,2],
   'source_damage_positions':[3,3]},
 ]
 shots=_formation_shots(volleys)
 assert [(volleys[index]['source_unit'],row,source_position)
         for index,row,source_position in shots]==[
  ('catapult',1,1),('catapult',1,2),('battering_ram',1,3),
  ('catapult',2,1),('catapult',2,2),('battering_ram',2,3),
 ]


def test_mixed_source_waves_share_one_frozen_target_address_book():
 registry=UnitRegistry.load()
 hoplite_hp=registry.get('hoplite').hit_points
 hoplite=Wave(
  ArmyUnit('hoplite',1,'hop'),0,
  [Slot('first-1','first',1,1,'hoplite','hop',1,30,hoplite_hp-1)],
 )
 steam=Wave(
  ArmyUnit('steam_giant',1,'steam'),0,
  [Slot('first-2','first',2,2,'steam_giant','steam',1,10,0)],
 )
 queues={
  ('hoplite','hop','first-1'):[hoplite_hp-1],
  ('steam_giant','steam','first-2'):[0],
 }
 volleys=[
  {'side':'attacker','source_unit':'swordsman','source_wave':'sword',
   'runtime_line':'flank','weapon_id':'primary','attack_upgrade':0,
   'row_numbers':[1],'source_damage_positions':[1]},
  {'side':'attacker','source_unit':'spearman','source_wave':'spear',
   'runtime_line':'flank','weapon_id':'primary','attack_upgrade':0,
   'row_numbers':[1,2],'source_damage_positions':[2,2]},
 ]
 casualties=defaultdict(int); slot_casualties=defaultdict(int); events=[]
 _resolve_volleys(
  volleys,[hoplite,steam],queues,registry,WorkshopProfile.load(),ForgeProfile.load(),
  TargetingProfile.load(),events,1,
  Army((ArmyUnit('swordsman',1,'sword'),ArmyUnit('spearman',2,'spear')),0),
  Army((ArmyUnit('hoplite',1,'hop'),ArmyUnit('steam_giant',1,'steam')),0),
  casualties,slot_casualties,{},
 )
 # Swordsman row 1 kills target position 1. Spearman row 1 still addresses
 # position 1 from the shared formation address book instead of renumbering
 # Steam Giant to the first/only surviving target column.
 wasted=[event for event in events if event.type=='shot_addressed_empty_slot']
 assert wasted
 assert wasted[0].details['source_unit_id']=='spearman'
 assert wasted[0].details['target_damage_position']==1
 assert casualties.get('hoplite')==1
 assert casualties.get('steam_giant',0)==0


def test_barbarian_mixed_artillery_debug_shape_reaches_combat():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'army_kind':'player','forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':650}]},
    'defender':{'army_kind':'barbarian','forge_level':0,'units':[
      {'unit_id':'barbarian_axe_swinger','quantity':650,
       'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_catapult','quantity':24,
       'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_ram','quantity':6,
       'entry_batch_id':'defender-barbarian-garrison'},
    ]}}
 result=simulate(s)
 rules={e['details'].get('rule_id') for e in result['events']
        if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' not in rules
 assert result['rounds_completed']==1
 assert {'barbarian_catapult','barbarian_ram'} <= {
  e['details'].get('source_unit_id') for e in result['events']
  if e['type']=='damage' and e['side']=='defender'
  and e['details'].get('firing_phase')=='third'
 }


def test_uploaded_barbarian_deployment_shape_no_longer_stops_at_round_zero():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'army_kind':'player','forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':650,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'steam_giant','quantity':32,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'spearman','quantity':150,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'swordsman','quantity':280,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'sulphur_carabineer','quantity':36,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'battering_ram','quantity':12,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'bombardier','quantity':75,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'gyrocopter','quantity':90,'entry_batch_id':'attacker-batch-1'},
    ]},
    'defender':{'army_kind':'barbarian','forge_level':0,'units':[
      {'unit_id':'barbarian_axe_swinger','quantity':650,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_clubman','quantity':350,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_knifeman','quantity':80,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_axe_thrower','quantity':350,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_catapult','quantity':24,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_ram','quantity':6,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_dirigible','quantity':45,'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_fighter','quantity':60,'entry_batch_id':'defender-barbarian-garrison'},
    ]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert not any(e['round']==0 and e['type']=='unsupported_mechanic'
                for e in result['events'])
 assert {'barbarian_catapult','barbarian_ram'} <= {
  e['details'].get('source_unit_id') for e in result['events']
  if e['type']=='damage' and e['side']=='defender'
  and e['details'].get('firing_phase')=='third'
 }


def test_barbarian_clubman_and_axe_swinger_share_heavy_front_without_mixed_am_blocker():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'army_kind':'player','units':[{'unit_id':'hoplite','quantity':350}]},
    'defender':{'army_kind':'barbarian','units':[
      {'unit_id':'barbarian_axe_swinger','quantity':300,
       'entry_batch_id':'defender-barbarian-garrison'},
      {'unit_id':'barbarian_clubman','quantity':50,
       'entry_batch_id':'defender-barbarian-garrison'},
    ]}}
 result=simulate(s)
 front=[slot for slot in result['initial_state']['defender']['slots']
        if slot['line']=='first']
 assert {slot['unit_id'] for slot in front}=={
  'barbarian_axe_swinger','barbarian_clubman'}
 assert all(slot['semantic_class']=='heavy_infantry' for slot in front)
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' not in {
  e['details'].get('rule_id') for e in result['events']
  if e['type']=='unsupported_mechanic'
 }
 assert result['rounds_completed']==1


def test_am_slot_addresses_stay_fixed_when_target_slot_empties_mid_volley():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':4}]},
    'defender':{'units':[{'unit_id':'spearman','quantity':31}]}}
 result=simulate(s)

 # land-mini deploys 31 Spearmen as damage-position 1:30 and 2:1.
 # Four Hoplite rows address 1,2,1,2. Once position 2 empties, row 4
 # remains addressed to position 2 instead of being redirected to position 1.
 assert result['casualties']['defender'].get('spearman')==3
 wasted=[e for e in result['events']
         if e['type']=='shot_addressed_empty_slot' and e['side']=='attacker']
 assert len(wasted)==1
 assert wasted[0]['details']['target_damage_position']==2
 assert wasted[0]['details']['action']=='address_preserved_no_retarget'

 matrix=next(e for e in result['events']
             if e['type']=='attacking_matrix'
             and e['side']=='attacker'
             and e['details'].get('source_unit_id','hoplite')=='hoplite')
 trace=matrix['details']['trace']
 assert trace['target_damage_positions']==[1,2]
 assert trace['hits_by_damage_position']=={1:2,2:2}
 assert trace['empty_addressed_shots_by_damage_position']=={2:1}


def test_mixed_first_formation_keeps_frozen_addresses_after_one_wave_dies_mid_volley():
 registry=UnitRegistry.load()
 hoplite_hp=registry.get('hoplite').hit_points
 hoplite=Wave(
  ArmyUnit('hoplite',1,'hop',entry_batch_id='batch-1'),0,
  [Slot('first-1','first',1,1,'hoplite','hop',1,30,hoplite_hp-1)],
 )
 steam=Wave(
  ArmyUnit('steam_giant',1,'steam',entry_batch_id='batch-1'),0,
  [Slot('first-2','first',2,2,'steam_giant','steam',1,10,0)],
 )
 queues={
  ('hoplite','hop','first-1'):[hoplite_hp-1],
  ('steam_giant','steam','first-2'):[0],
 }
 volleys=[{
  'side':'attacker',
  'source_unit':'swordsman',
  'source_wave':'source-wave',
  'runtime_line':'flank',
  'weapon_id':'primary',
  'attack_upgrade':0,
  'row_numbers':[1,2,1],
 }]
 casualties=defaultdict(int)
 slot_casualties=defaultdict(int)
 events=[]
 _resolve_volleys(
  volleys,[hoplite,steam],queues,registry,WorkshopProfile.load(),ForgeProfile.load(),
  TargetingProfile.load(),events,1,
  Army((ArmyUnit('swordsman',3,'source-wave'),),0),
  Army((ArmyUnit('hoplite',1,'hop',entry_batch_id='batch-1'),
        ArmyUnit('steam_giant',1,'steam',entry_batch_id='batch-1')),0),
  casualties,slot_casualties,{},
 )
 assert casualties.get('hoplite')==1
 assert casualties.get('steam_giant',0)==0
 wasted=[event for event in events if event.type=='shot_addressed_empty_slot']
 assert len(wasted)==1
 assert wasted[0].details['target_damage_position']==1
 assert wasted[0].details['target_wave']=='hop'
 matrices=[event for event in events if event.type=='attacking_matrix']
 by_wave={event.details['target_wave']:event.details for event in matrices}
 assert set(by_wave)=={'hop','steam'}
 assert by_wave['hop']['target_unit_id']=='hoplite'
 assert by_wave['steam']['target_unit_id']=='steam_giant'
 assert by_wave['hop']['trace']['target_damage_positions']==[1]
 assert by_wave['steam']['trace']['target_damage_positions']==[2]
 assert by_wave['hop']['trace']['formation_target_damage_positions']==[1,2]
 assert by_wave['steam']['trace']['formation_target_damage_positions']==[1,2]


def test_same_batch_heavy_handoff_runs_before_rr_and_conserves_reserve_damage():
 from ikariam_battle.engine import _prepare_round_start
 registry=UnitRegistry.load(); rules=FormationRules.load()
 owner=Wave(
  ArmyUnit('hoplite',0,'hop',entry_batch_id='batch-1'),0,
  [Slot('first-1','first',2,1,'hoplite','hop',0,30,0)],
 )
 steam=Wave(
  ArmyUnit('steam_giant',10,'steam',entry_batch_id='batch-1'),10,[],
  reserve_damage=100,
 )
 events=[]; applied={}
 _prepare_round_start(
  [owner,steam],events,2,'attacker',applied,
  registry,rules,LAND_MINI,
 )
 assert owner.slots==[]
 assert len(steam.slots)==1
 assert steam.slots[0].line=='first'
 assert steam.slots[0].capacity==10
 assert steam.slots[0].units==10
 assert steam.reserve==0
 assert steam.reserve_damage==0
 assert steam.slots[0].damage==100
 assert steam.reserve_damage + sum(slot.damage for slot in steam.slots)==100
 assert any(event.type=='slot_handoff' for event in events)
 assert any(event.type=='redistribution' for event in events)


def test_round_snapshot_keeps_destroyed_slot_identity_and_round_casualties():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}
 result=simulate(s)
 slot=next(row for row in result['rounds'][1]['defender']['slots']
           if row['unit_id']=='hoplite' and row['line']=='first')
 assert slot['units']==0
 assert slot['hit_points_percent']==0
 assert slot['casualties']==1


def test_snapshot_exposes_batch_reserve_damage_and_hp_percent():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load()
 hp=registry.get('hoplite').hit_points
 wave=Wave(ArmyUnit('hoplite',40,'reserve-batch'),10,
           [Slot('first-1','first',2,1,'hoplite','reserve-batch',30,30)],
           reserve_damage=2*hp)
 state=_snapshot([wave],registry,BattleEndProfile.load())
 batch=state['waves'][0]
 assert batch['reserve']==10
 assert batch['reserve_damage']==2*hp
 assert batch['reserve_hit_points_percent']==80


def test_round_start_rr_spreads_persistent_damage_into_reserve_without_healing():
 from ikariam_battle.engine import _prepare_round_start, _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load(); battle_end=BattleEndProfile.load()
 wave=Wave(
  ArmyUnit('hoplite',40,'rr-reserve'),10,
  [Slot('first-1','first',2,1,'hoplite','rr-reserve',30,30,400)],
 )
 events=[]; applied={}
 _prepare_round_start([wave],events,2,'attacker',applied)
 assert wave.slots[0].damage==300
 assert wave.reserve_damage==100
 state=_snapshot([wave],registry,battle_end)
 batch=state['waves'][0]
 assert batch['reserve_damage']==100
 assert batch['reserve_hit_points_percent'] < 100
 rr=next(event for event in events if event.type=='redistribution')
 assert rr.details['total_wave_damage']==400
 assert rr.details['reserve_damage']==100
 assert rr.details['damage_conserved'] is True


def test_full_clear_doctor_can_keep_reserve_hp_at_100_before_rr():
 from ikariam_battle.engine import _prepare_round_start, _snapshot
 from ikariam_battle.profiles import BattleEndProfile, SupportProfile
 registry=UnitRegistry.load(); battle_end=BattleEndProfile.load()
 doctor=Wave(ArmyUnit('doctor',15,'doctor'),0,[],0,None,15)
 wave=Wave(
  ArmyUnit('hoplite',40,'rr-reserve'),10,
  [Slot('first-1','first',2,1,'hoplite','rr-reserve',30,30,400)],
 )
 events=[]; applied={}
 _prepare_round_start(
  [doctor,wave],events,2,'attacker',applied,
  registry=registry,support=SupportProfile.load(),
 )
 assert wave.slots[0].damage==0
 assert wave.reserve_damage==0
 state=_snapshot([wave],registry,battle_end)
 assert state['waves'][0]['reserve_hit_points_percent']==100
 heal=next(event for event in events if event.type=='healing')
 assert heal.details['healing']==400
 assert not any(event.type=='redistribution' for event in events)


def test_destroyed_slot_identity_is_round_local_not_a_persistent_tombstone():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load(); battle_end=BattleEndProfile.load()
 wave=Wave(ArmyUnit('hoplite',3,'batch'),0,
           [Slot('first-1','first',2,1,'hoplite','batch',0,30)])

 death_round=_snapshot([wave],registry,battle_end,{('batch','first-1'):3})
 assert len(death_round['slots'])==1
 assert death_round['slots'][0]['units']==0
 assert death_round['slots'][0]['casualties']==3
 assert death_round['slots'][0]['hit_points_percent']==0

 following_round=_snapshot([wave],registry,battle_end)
 assert following_round['slots']==[]


def test_round_start_refill_replaces_destroyed_marker_with_live_current_state():
 from ikariam_battle.engine import _prepare_round_start, _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load(); battle_end=BattleEndProfile.load()
 wave=Wave(ArmyUnit('hoplite',5,'batch'),5,
           [Slot('first-1','first',2,1,'hoplite','batch',0,30)])
 _prepare_round_start([wave],[],2,'attacker',{})
 state=_snapshot([wave],registry,battle_end)
 assert len(state['slots'])==1
 assert state['slots'][0]['units']==5
 assert state['slots'][0]['casualties']==0
 assert state['slots'][0]['hit_points_percent']==100

def test_partial_flank_casualties_reduce_later_long_range_shots():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':60,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84}]}}
 result=simulate(s)
 killed=result['casualties']['defender'].get('sulphur_carabineer',0)
 assert 0 < killed < 84
 second_phase=next(e for e in result['events']
                   if e['type']=='formation_fire_phase'
                   and e['details']['firing_phase']=='second')
 assert second_phase['details']['defender_shots']==84-killed


def test_low_accuracy_one_shot_volley_does_not_manufacture_misses():
 registry=UnitRegistry.load()
 hp=registry.get('hoplite').hit_points
 target=Wave(
  ArmyUnit('hoplite',3,'target-wave'),0,
  [Slot('first-1','first',1,1,'hoplite','target-wave',3,30,0)],
 )
 queues={('hoplite','target-wave','first-1'):[0,0,0]}
 volleys=[{
  'side':'attacker','source_unit':'mortar','source_wave':'source-wave',
  'runtime_line':'third','weapon_id':'primary','attack_upgrade':0,
  'row_numbers':[1,1,1],
 }]
 casualties=defaultdict(int); slot_casualties=defaultdict(int); events=[]
 _resolve_volleys(
  volleys,[target],queues,registry,WorkshopProfile.load(),ForgeProfile.load(),
  TargetingProfile.load(),events,1,
  Army((ArmyUnit('mortar',3,'source-wave'),),0),
  Army((ArmyUnit('hoplite',3,'target-wave'),),0),
  casualties,slot_casualties,{},
 )
 assert casualties['hoplite']==3
 assert target.slots[0].units==0
 damage=next(e for e in events if e.type=='damage')
 assert damage.details['weapon_accuracy']==10
 assert damage.details['accuracy_model']=='EXP-ACCURACY-CONCENTRATION-001'
 assert damage.details['accuracy_decisions']=={'one_shot_bypass':3}


def test_non_one_shot_accuracy_spreads_then_focuses_after_hp_threshold():
 registry=UnitRegistry.load()
 target=Wave(
  ArmyUnit('steam_giant',3,'target-wave'),0,
  [Slot('first-1','first',1,1,'steam_giant','target-wave',3,10,0)],
 )
 queues={('steam_giant','target-wave','first-1'):[0,0,0]}
 volleys=[{
  'side':'attacker','source_unit':'hoplite','source_wave':'source-wave',
  'runtime_line':'first','weapon_id':'primary','attack_upgrade':0,
  'row_numbers':[1,1,1,1,1],
 }]
 casualties=defaultdict(int); slot_casualties=defaultdict(int); events=[]
 _resolve_volleys(
  volleys,[target],queues,registry,WorkshopProfile.load(),ForgeProfile.load(),
  TargetingProfile.load(),events,1,
  Army((ArmyUnit('hoplite',5,'source-wave'),),0),
  Army((ArmyUnit('steam_giant',3,'target-wave'),),0),
  casualties,slot_casualties,{},
 )
 # Hoplite net hit is 300 vs Steam Giant. At 90% Accuracy the first four
 # hits spread: 300/300/300, then one survivor crosses below 90% remaining HP
 # at 600 damage and the fifth hit focuses it.
 assert casualties.get('steam_giant',0)==0
 assert queues[('steam_giant','target-wave','first-1')]==[900,300,300]
 damage=next(e for e in events if e.type=='damage')
 assert damage.details['weapon_accuracy']==90
 assert damage.details['accuracy_decisions']=={
  'spread_above_accuracy_threshold':4,
  'focus_below_accuracy_threshold':1,
 }


def test_sequential_volley_resolution_differs_from_legacy_pooled_casualty_math():
 registry=UnitRegistry.load()
 target=Wave(
  ArmyUnit('spearman',2,'target-wave'),0,
  [Slot('first-1','first',1,1,'spearman','target-wave',2,2,130)],
 )
 queues={('spearman','target-wave','first-1'):[130,0]}
 volleys=[{
  'side':'attacker',
  'source_unit':'swordsman',
  'source_wave':'source-wave',
  'runtime_line':'flank',
  'weapon_id':'primary',
  'attack_upgrade':0,
  'row_numbers':[1,1],
 }]
 casualties={'spearman':0}
 slot_casualties={('target-wave','first-1'):0}
 events=[]
 _resolve_volleys(
  volleys,[target],queues,registry,WorkshopProfile.load(),ForgeProfile.load(),
  TargetingProfile.load(),events,1,
  Army((ArmyUnit('swordsman',2,'source-wave'),),0),
  Army((ArmyUnit('spearman',2,'target-wave'),),0),
  casualties,slot_casualties,{},
 )

 hp=registry.get('spearman').hit_points
 damage=registry.get('swordsman').weapons[0].damage
 pooled_casualties=(130 + 2*damage)//hp
 assert (hp,damage,pooled_casualties)==(260,200,2)
 assert casualties['spearman']==1
 assert target.slots[0].units==1 and target.slots[0].damage==200
 assert queues[('spearman','target-wave','first-1')]==[200]


def test_ir_and_sr_hooks_are_explicitly_disabled_at_baseline():
 assert _ir_trigger(object()) is False
 assert _sr_trigger('flank',[],[]) is False


def test_round_redistribution_keeps_entry_waves_isolated():
 wave_a=Wave(
  ArmyUnit('hoplite',40,'wave-a'),10,
  [Slot('first-a','first',1,1,'hoplite','wave-a',30,30,90)],
  reserve_damage=10,
 )
 wave_b=Wave(
  ArmyUnit('hoplite',40,'wave-b'),10,
  [Slot('first-b','first',1,1,'hoplite','wave-b',30,30,5)],
  reserve_damage=2,
 )
 events=[]
 _redistribute([wave_a,wave_b],events,2,'attacker',{})

 assert wave_a.reserve_damage + sum(slot.damage for slot in wave_a.slots)==100
 assert wave_b.reserve_damage + sum(slot.damage for slot in wave_b.slots)==7
 rr=[e for e in events if e.type=='redistribution']
 assert {(e.details['wave_id'],e.details['total_wave_damage']) for e in rr}=={
  ('wave-a',100),('wave-b',7),
 }


def test_debug_case_hoplite_steam_giant_swordsman_reaches_combat_before_cross_wave_boundary():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':500,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'steam_giant','quantity':96,'entry_batch_id':'attacker-batch-1'},
      {'unit_id':'swordsman','quantity':440,'entry_batch_id':'attacker-batch-1'}]},
    'defender':{'forge_level':5,'units':[
      {'unit_id':'hoplite','quantity':450,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'steam_giant','quantity':96,'entry_batch_id':'defender-batch-1'},
      {'unit_id':'swordsman','quantity':400,'entry_batch_id':'defender-batch-1'}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert result['initial_state']['attacker']['reserve']['steam_giant']==96
 assert result['initial_state']['defender']['reserve']['steam_giant']==96
 assert not any(e['type']=='unsupported_mechanic' and e['round']==0
                and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
                for e in result['events'])
 assert any(e['type']=='attacking_matrix' for e in result['events'])


def test_future_entry_batch_arrives_as_reserve_at_its_configured_round():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a0','arrival_round':0},
      {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90}]}}
 result=simulate(s)
 arrival=next(e for e in result['events'] if e['type']=='entry_batch_arrived')
 assert arrival['round']==1 and arrival['details']['entry_batch_id']=='a1'
 # The front is still full after same-wave refill, so the newly arrived Steam
 # Giants wait in reserve instead of causing a round-0/preflight failure.
 assert not any(e['type']=='unsupported_mechanic' and e['round']==0
                and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
                for e in result['events'])


def test_future_doctor_arrival_does_not_assume_no_healing_before_damage_exists():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a0','arrival_round':0},
      {'unit_id':'doctor','quantity':2,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90}]}}
 result=simulate(s)
 assert any(e['type']=='entry_batch_arrived' and e['round']==1
            and e['details']['entry_batch_id']=='a1' for e in result['events'])
 assert 'EXP-HEAL-NONE-001' not in {a['id'] for a in result['assumptions']}
 side=result['healing_status']['sides']['attacker']
 assert side['doctor_count']==2
 assert side['status']=='not_reached'
 assert side['effect_applied'] is False
 assert side['healing_amount']==0
 assert side['engine_healing_applied']==0


def test_future_cook_arrival_applies_named_no_morale_assumption():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a0','arrival_round':0},
      {'unit_id':'cook','quantity':15,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90}]}}
 result=simulate(s)
 assert any(e['type']=='entry_batch_arrived' and e['round']==1
            and e['details']['entry_batch_id']=='a1' for e in result['events'])
 assert 'EXP-MORALE-NONE-001' in {a['id'] for a in result['assumptions']}
 assert result['morale_status']['sides']['attacker']=={
  'cook_count':15,'status':'ignored_by_named_assumption','effect_applied':False
 }


def test_future_support_assumptions_are_side_and_round_specific():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a0','arrival_round':0},
      {'unit_id':'doctor','quantity':2,'entry_batch_id':'a1','arrival_round':1},
      {'unit_id':'cook','quantity':15,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','arrival_round':0},
      {'unit_id':'doctor','quantity':3,'entry_batch_id':'d2','arrival_round':2},
      {'unit_id':'cook','quantity':12,'entry_batch_id':'d2','arrival_round':2}]}}
 result=simulate(s)
 assumption_events=[e for e in result['events'] if e['type']=='assumption_applied']
 assert not any(e['details']['id']=='EXP-HEAL-NONE-001' for e in assumption_events)
 assert any(e['side']=='attacker' and e['round']==1
            and e['details']['id']=='EXP-MORALE-NONE-001' for e in assumption_events)
 assert not any(e['side']=='defender'
                and e['details']['id']=='EXP-MORALE-NONE-001'
                for e in assumption_events)
 assert result['healing_status']['sides']['attacker']['status']=='not_reached'
 assert result['healing_status']['sides']['defender']['status']=='not_reached'
 assert result['morale_status']['sides']['attacker']['status']=='ignored_by_named_assumption'
 assert result['morale_status']['sides']['defender']['status']=='not_reached'
 rounds={row['round']:row for row in result['rounds']}
 assert rounds[0]['combat_statistics']['attacker']['healing']==0
 assert rounds[0]['combat_statistics']['defender']['healing']==0
 assert rounds[1]['combat_statistics']['attacker']['healing']==0
 assert rounds[1]['combat_statistics']['defender']['healing']==0
 assert result['combat_statistics']['attacker']['gross_healing']==0
 assert result['combat_statistics']['defender']['gross_healing']==0


def test_round_zero_doctor_presence_does_not_emit_healing_assumption_before_damage():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90},{'unit_id':'doctor','quantity':1}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','arrival_round':0},
      {'unit_id':'doctor','quantity':1,'entry_batch_id':'d2','arrival_round':2}]}}
 result=simulate(s)
 events=[e for e in result['events'] if e['type']=='assumption_applied'
         and e['details'].get('id')=='EXP-HEAL-NONE-001']
 assert events==[]
 assert result['healing_status']['sides']['attacker']['status']=='not_reached'
 assert result['healing_status']['sides']['defender']['status']=='not_reached'


def test_entry_batch_arrival_event_accumulates_repeated_unit_waves():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a0','arrival_round':0},
      {'unit_id':'doctor','quantity':10,'entry_batch_id':'a1','wave_id':'doctor-a','arrival_round':1},
      {'unit_id':'doctor','quantity':20,'entry_batch_id':'a1','wave_id':'doctor-b','arrival_round':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90}]}}
 result=simulate(s)
 arrival=next(e for e in result['events']
              if e['type']=='entry_batch_arrived'
              and e['side']=='attacker'
              and e['details']['entry_batch_id']=='a1')
 assert arrival['details']['units']=={'doctor':30}
 assert result['final_state']['attacker']['deployed_support']['doctor']==30


def test_same_batch_heavy_requirement_created_by_combat_is_supported_next_round():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'attack_upgrade':200}]},
    'defender':{'units':[
      {'unit_id':'steam_giant','quantity':30,'entry_batch_id':'d0','wave_id':'d-first'},
      {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'d0','wave_id':'d-reserve'}]}}
 result=simulate(s)
 assert result['rounds_completed']>=2
 assert result['casualties']['defender'].get('steam_giant')>=30
 assert not any(e['type']=='unsupported_mechanic'
                and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
                and e['side']=='defender'
                for e in result['events'])
 assert any(e['type']=='slot_handoff' and e['round']==2
            and e['side']=='defender'
            and e['details'].get('to_wave_id')=='d-reserve'
            for e in result['events'])


def test_same_batch_exhausted_mortar_hands_existing_third_slots_to_battering_rams():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'battering_ram','quantity':30,'entry_batch_id':'a0'},
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'a0'},
 ]}),registry,field)
 ram=next(w for w in waves if w.unit.unit_id=='battering_ram')
 mortar=next(w for w in waves if w.unit.unit_id=='mortar')
 assert ram.slots==[] and ram.reserve==30
 assert sorted((slot.damage_position,slot.units) for slot in mortar.slots)==[
  (1,6),(2,6),(3,6),(4,6),(5,6)]
 mortar.ammo_pool_shots=0

 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,4,'attacker',applied,registry,rules,field,
 )
 assert boundary is False
 assert mortar.reserve==30
 assert not any(slot.units for slot in mortar.slots)
 assert ram.reserve==0
 assert sorted((slot.damage_position,slot.units) for slot in ram.slots)==[
  (1,6),(2,6),(3,6),(4,6),(5,6)]
 assert _cross_wave_rebuild_requirements(waves,registry,rules,field)==[]
 handoffs=[
  event for event in events
  if event.type=='slot_handoff'
  and event.details.get('reason')=='same_batch_ranked_third_replacement'
 ]
 assert len(handoffs)==5
 assert all(event.details.get('from_unit_id')=='mortar' for event in handoffs)
 assert all(event.details.get('to_unit_id')=='battering_ram' for event in handoffs)


def test_exhausted_mortar_hands_third_slots_to_later_mortar_without_same_batch_peer():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'a0','wave_id':'mortar-a'},
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'b0','wave_id':'mortar-b'},
 ]}),registry,field)
 mortar_a=next(w for w in waves if w.unit.wave_id=='mortar-a')
 mortar_b=next(w for w in waves if w.unit.wave_id=='mortar-b')
 assert mortar_b.slots==[] and mortar_b.reserve==30
 mortar_a.ammo_pool_shots=0

 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,4,'attacker',applied,registry,rules,field,
 )
 assert boundary is False
 assert not any(slot.units for slot in mortar_a.slots)
 assert mortar_a.reserve==30
 assert mortar_b.reserve==0
 assert sorted((slot.damage_position,slot.units) for slot in mortar_b.slots)==[
  (1,6),(2,6),(3,6),(4,6),(5,6)]
 assert _cross_wave_rebuild_requirements(waves,registry,rules,field)==[]
 mortar_handoffs=[
  event for event in events
  if event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  and event.details.get('from_unit_id')=='mortar'
  and event.details.get('to_unit_id')=='mortar'
 ]
 assert len(mortar_handoffs)==5
 assert all(event.details.get('from_wave_id')=='mortar-a' for event in mortar_handoffs)
 assert all(event.details.get('to_wave_id')=='mortar-b' for event in mortar_handoffs)


def test_same_unit_cross_batch_mortar_handoff_precedes_same_batch_ram():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'a0','wave_id':'mortar-a'},
  {'unit_id':'battering_ram','quantity':30,'entry_batch_id':'a0','wave_id':'ram-a'},
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'b0','wave_id':'mortar-b'},
 ]}),registry,field)
 mortar_a=next(w for w in waves if w.unit.wave_id=='mortar-a')
 ram_a=next(w for w in waves if w.unit.wave_id=='ram-a')
 mortar_b=next(w for w in waves if w.unit.wave_id=='mortar-b')
 assert sorted((slot.damage_position,slot.units) for slot in mortar_a.slots)==[
  (1,6),(2,6),(3,6),(4,6),(5,6)]
 assert ram_a.slots==[] and ram_a.reserve==30
 assert mortar_b.slots==[] and mortar_b.reserve==30
 mortar_a.ammo_pool_shots=0

 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,4,'attacker',applied,registry,rules,field,
 )
 assert boundary is False
 assert not any(slot.units for slot in mortar_a.slots)
 assert mortar_a.reserve==30
 assert ram_a.slots==[] and ram_a.reserve==30
 assert mortar_b.reserve==0
 assert sorted((slot.damage_position,slot.units) for slot in mortar_b.slots)==[
  (1,6),(2,6),(3,6),(4,6),(5,6)]
 handoffs=[
  event for event in events
  if event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  and event.details.get('from_wave_id')=='mortar-a'
  and event.details.get('to_wave_id')=='mortar-b'
 ]
 assert len(handoffs)==5
 assert all(event.details.get('from_entry_batch_id')=='a0' for event in handoffs)
 assert all(event.details.get('entry_batch_id')=='b0' for event in handoffs)
 assert len([
  event for event in events
  if event.type=='slot_handoff'
  and event.details.get('reason')=='same_unit_same_line_wave_replacement'
  and event.details.get('from_unit_id')=='mortar'
  and event.details.get('to_unit_id')=='mortar'
 ])==5
 assert not any(
  event.type=='slot_handoff'
  and event.details.get('to_unit_id')=='battering_ram'
  and event.details.get('reason')=='same_batch_ranked_third_replacement'
  for event in events
 )


def test_exhausted_mortar_does_not_pull_third_line_ram_from_another_entry_batch():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'mortar','quantity':30,'entry_batch_id':'a0'},
  {'unit_id':'battering_ram','quantity':30,'entry_batch_id':'a1'},
 ]}),registry,field)
 mortar=next(w for w in waves if w.unit.unit_id=='mortar')
 ram=next(w for w in waves if w.unit.unit_id=='battering_ram')
 assert ram.slots==[] and ram.reserve==30
 mortar.ammo_pool_shots=0
 requirements=_cross_wave_rebuild_requirements(waves,registry,rules,field)
 assert any(
  requirement['unit_id']=='battering_ram'
  and requirement['entry_batch_id']=='a1'
  and requirement['runtime_line']=='third'
  for requirement in requirements
 )


def test_exhausted_mortar_to_ram_replacement_continues_past_round_three():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':4,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':5000,'entry_batch_id':'a0'},
      {'unit_id':'battering_ram','quantity':30,'entry_batch_id':'a0'},
      {'unit_id':'mortar','quantity':30,'entry_batch_id':'a0'}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':10000,'entry_batch_id':'d0'}]}}
 result=simulate(s)
 assert result['rounds_completed']==4
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
  and event['side']=='attacker'
  for event in result['events']
 )
 round4_handoffs=[
  event for event in result['events']
  if event['round']==4
  and event['type']=='slot_handoff'
  and event['side']=='attacker'
  and event['details'].get('reason')=='same_batch_ranked_third_replacement'
 ]
 assert len(round4_handoffs)==5
 assert all(event['details'].get('from_unit_id')=='mortar' for event in round4_handoffs)
 assert all(event['details'].get('to_unit_id')=='battering_ram' for event in round4_handoffs)


def test_post_combat_empty_slots_with_same_wave_reserve_refill_before_cross_wave_check():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'attack_upgrade':200}]},
    'defender':{'units':[
      {'unit_id':'steam_giant','quantity':40,'entry_batch_id':'d0','wave_id':'d-first'}]}}
 result=simulate(s)
 round1_boundaries=[e for e in result['events']
                    if e['type']=='unsupported_mechanic'
                    and e['round']==1
                    and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD']
 assert round1_boundaries==[]
 assert result['rounds_completed']>=1
 # The 30 deployed Giants die in Round 1, but the wave still owns its slots and
 # its own 10-unit Reserve is refilled at the next supported round boundary.
 assert result['rounds'][1]['casualties']['defender'].get('steam_giant')==30
 assert any(e['type']=='slot_repacked' and e['round']==2 and e['side']=='defender'
            and e['details']['units']==10 for e in result['events'])


def test_post_combat_projection_consumes_supported_same_batch_heavy_handoff():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 waves=deploy(Army.from_dict({'units':[
   {'unit_id':'steam_giant','quantity':40,'entry_batch_id':'d0','wave_id':'owner'},
   {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'d0','wave_id':'reserve'},
 ]}),registry,LAND_MINI)
 owner=next(w for w in waves if w.unit.wave_id=='owner')
 reserve=next(w for w in waves if w.unit.wave_id=='reserve')
 for slot in owner.slots:
  slot.units=0
 owner.reserve=10
 assert reserve.slots==[] and reserve.reserve==10
 requirements=_cross_wave_rebuild_requirements(waves,registry,rules,LAND_MINI)
 assert requirements==[]


def test_projected_reserve_uses_complete_unit_and_wave_identity():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 waves=deploy(Army.from_dict({'units':[
   {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','wave_id':'shared'},
   {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'d0','wave_id':'shared'},
   {'unit_id':'swordsman','quantity':30,'entry_batch_id':'d1','wave_id':'shared'},
 ]}),registry,LAND_MINI)
 hoplite=next(w for w in waves if w.unit.unit_id=='hoplite')
 steam=next(w for w in waves if w.unit.unit_id=='steam_giant')
 swordsman=next(w for w in waves if w.unit.unit_id=='swordsman')
 for slot in hoplite.slots:
  slot.units=0
 hoplite.reserve=0
 steam.reserve=10
 assert steam.slots==[]
 assert swordsman.reserve==30 and swordsman.slots==[]
 requirements=_cross_wave_rebuild_requirements(waves,registry,rules,LAND_MINI)
 assert not any(r['unit_id']=='steam_giant' for r in requirements)
 assert any(r['unit_id']=='swordsman' and r['wave_id']=='shared'
            and r['runtime_line']=='first'
            for r in requirements)


def test_supported_same_batch_handoff_is_projected_before_other_batch_requirement():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 waves=deploy(Army.from_dict({'units':[
   {'unit_id':'steam_giant','quantity':30,'entry_batch_id':'d0','wave_id':'front'},
   {'unit_id':'steam_giant','quantity':30,'entry_batch_id':'d0','wave_id':'same-batch'},
   {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'d1','wave_id':'other-batch'},
 ]}),registry,LAND_MINI)
 front=next(w for w in waves if w.unit.wave_id=='front')
 same_batch=next(w for w in waves if w.unit.wave_id=='same-batch')
 other_batch=next(w for w in waves if w.unit.wave_id=='other-batch')
 for slot in front.slots:
  slot.units=0
 front.reserve=0
 assert same_batch.slots==[] and same_batch.reserve==30
 assert other_batch.slots==[] and other_batch.reserve==10
 requirements=_cross_wave_rebuild_requirements(waves,registry,rules,LAND_MINI)
 assert requirements==[]


def test_pending_supported_handoff_at_max_rounds_keeps_outcome_inconclusive():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'attack_upgrade':200}]},
    'defender':{'units':[
      {'unit_id':'steam_giant','quantity':30,'entry_batch_id':'d0','wave_id':'front'},
      {'unit_id':'steam_giant','quantity':10,'entry_batch_id':'d0','wave_id':'reserve'}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert result['status']=='inconclusive'
 assert result['outcome']=='inconclusive'
 assert result['final_state']['defender']['reserve']['steam_giant']==10
 assert any(e['type']=='safety_limit_reached' for e in result['events'])
 assert not any(e['type']=='battle_termination' and e['round']==1
                for e in result['events'])


def test_round_zero_empty_side_waits_for_scheduled_combat_arrival_instead_of_losing():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','arrival_round':0}]}}
 result=simulate(s)
 assert result['status']=='inconclusive'
 assert result['outcome']=='inconclusive'
 assert not any(e['type']=='battle_termination' and e['round']==0 for e in result['events'])
 wait=next(e for e in result['events'] if e['type']=='waiting_for_arrival' and e['round']==0)
 assert wait['side']=='attacker'
 assert wait['details']['next_arrival_round']==1
 assert any(e['type']=='entry_batch_arrived' and e['round']==1
            and e['side']=='attacker' and e['details']['entry_batch_id']=='a1'
            for e in result['events'])
 assert any(e['type']=='unsupported_mechanic' and e['round']==1
            and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
            for e in result['events'])


def test_pre_engagement_wait_can_span_empty_rounds_until_future_arrival():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a3','arrival_round':3}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','arrival_round':0}]}}
 result=simulate(s)
 assert not any(e['type']=='battle_termination' for e in result['events'])
 waits=[e for e in result['events'] if e['type']=='waiting_for_arrival']
 assert waits and waits[0]['round']==0
 assert any(e['round']==1 and e['side']=='attacker' for e in waits)
 assert any(e['round']==2 and e['side']=='attacker' for e in waits)
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='attacker' for e in result['events'])
 assert result['status']=='inconclusive'


def test_future_non_sustaining_artillery_does_not_delay_round_zero_loss():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
    'attacker':{'units':[
      {'unit_id':'mortar','quantity':6,'entry_batch_id':'a1','arrival_round':1}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d0','arrival_round':0}]}}
 result=simulate(s)
 assert result['status']=='completed'
 assert result['outcome']=='defender'
 assert result['rounds_completed']==0
 assert any(e['type']=='battle_termination' and e['round']==0 for e in result['events'])
 assert not any(e['type']=='waiting_for_arrival' for e in result['events'])


def test_both_round_zero_empty_armies_emit_combined_initial_wait_event():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a3','arrival_round':3}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d3','arrival_round':3}]}}
 result=simulate(s)
 wait=next(e for e in result['events']
           if e['type']=='waiting_for_arrival' and e['round']==0)
 assert wait['side'] is None
 assert wait['details']['pending_sides']==['attacker','defender']
 assert wait['details']['next_arrival_round']==3
 assert set(wait['details']['pending'])=={'attacker','defender'}
 assert wait['details']['pending']['attacker'][0]['entry_batch_id']=='a3'
 assert wait['details']['pending']['defender'][0]['entry_batch_id']=='d3'
 assert not any(e['type']=='battle_termination' and e['round']==0
                for e in result['events'])
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='attacker' for e in result['events'])
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='defender' for e in result['events'])


def test_arrival_cross_wave_boundary_preserves_boundary_round_snapshot():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
    'attacker':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a3','arrival_round':3}]},
    'defender':{'units':[
      {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d3','arrival_round':3}]}}
 result=simulate(s)
 assert result['status']=='inconclusive'
 assert result['rounds_completed']==3
 round3=next(row for row in result['rounds'] if row['round']==3)
 assert round3['casualties']=={'attacker':{},'defender':{}}
 assert round3['attacker']['reserve']['hoplite']==90
 assert round3['defender']['reserve']['hoplite']==90
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='attacker' for e in result['events'])
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='defender' for e in result['events'])
 assert any(e['type']=='unsupported_mechanic' and e['round']==3
            and e['phase']=='round_start'
            and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
            for e in result['events'])


def test_barbarian_land_army_can_fight_player_army_and_scores_zero():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'army_kind':'player','forge_level':0,'units':[
      {'unit_id':'hoplite','quantity':90}]},
    'defender':{'army_kind':'barbarian','forge_level':0,'units':[
      {'unit_id':'barbarian_axe_swinger','quantity':90,
       'entry_batch_id':'barbarian-garrison'}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 initial=result['initial_state']['defender']
 assert initial['remaining']['barbarian_axe_swinger']==90
 assert any(
  slot['unit_id']=='barbarian_axe_swinger'
  for slot in initial['slots']
 )
 assert result['military_score']['defender']['general_score_lost']==0


def test_army_package_rejects_player_and_barbarian_unit_mixing():
 with pytest.raises(ScenarioError,match='belongs to the barbarian army package'):
  simulate({'policy':'experimental','battlefield':'land-mini','max_rounds':1,
            'attacker':{'army_kind':'player','units':[
              {'unit_id':'barbarian_clubman','quantity':30}]},
            'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}})
 with pytest.raises(ScenarioError,match='belongs to the player army package'):
  simulate({'policy':'experimental','battlefield':'land-mini','max_rounds':1,
            'attacker':{'army_kind':'barbarian','units':[
              {'unit_id':'hoplite','quantity':30,'entry_batch_id':'barbarian'}]},
            'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}})


def test_typed_barbarian_scenario_cannot_bypass_package_invariants():
 defender=Army((
  ArmyUnit('hoplite',30),
 ),0,'player')

 invalid_armies=[
  Army((ArmyUnit('barbarian_axe_swinger',30,entry_batch_id='barbarian'),),5,'barbarian'),
  Army((ArmyUnit('barbarian_axe_swinger',30,attack_upgrade=1,entry_batch_id='barbarian'),),0,'barbarian'),
  Army((ArmyUnit('barbarian_axe_swinger',30,entry_batch_id='barbarian',arrival_round=1),),0,'barbarian'),
  Army((
   ArmyUnit('barbarian_axe_swinger',15,wave_id='w1',entry_batch_id='a'),
   ArmyUnit('barbarian_ram',1,wave_id='w2',entry_batch_id='b'),
  ),0,'barbarian'),
  Army((
   ArmyUnit('barbarian_axe_swinger',15,wave_id='w1',entry_batch_id='barbarian'),
   ArmyUnit('barbarian_axe_swinger',15,wave_id='w2',entry_batch_id='barbarian'),
  ),0,'barbarian'),
 ]
 messages=[
  'do not use Forge',
  'do not use Workshop',
  'do not use delayed entry',
  'one fixed entry batch',
  'cannot be split across waves',
 ]
 for army,message in zip(invalid_armies,messages):
  with pytest.raises(ScenarioError,match=message):
   simulate(Scenario(
    attacker=army,defender=defender,policy=Policy.EXPERIMENTAL,
    battlefield='land-mini',max_rounds=1,
   ))


@pytest.mark.parametrize('bad',['pirate',[],{},None,False])
def test_typed_scenario_rejects_invalid_army_kind(bad):
 attacker=Army((ArmyUnit('hoplite',30),),0,bad)
 defender=Army((ArmyUnit('hoplite',30),),0,'player')
 with pytest.raises(ScenarioError,match='army_kind must be player or barbarian'):
  simulate(Scenario(
   attacker=attacker,defender=defender,policy=Policy.EXPERIMENTAL,
   battlefield='land-mini',max_rounds=1,
  ))



def test_exhausted_land_long_range_whole_wave_fills_open_first_slots():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':250,'wave_id':'front'},
  {'unit_id':'sulphur_carabineer','quantity':24,'wave_id':'ranged'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 # Keep five First slots occupied, leaving two open. 24 Carabineers fit exactly
 # as two First slots because land-max First slot space is 50 and unit size is 4.
 front.reserve=0
 for slot in front.slots:
  slot.units=50 if slot.damage_position in {1,2,3,4,5} else 0
  slot.damage=0
 ranged.reserve=0
 for slot in ranged.slots:
  slot.damage=0
 ranged.ammo_pool_shots=0
 events=[]; applied={}
 _prepare_round_start(waves,events,4,'defender',applied,registry,rules,field)
 live=[slot for slot in ranged.slots if slot.units]
 assert {slot.line for slot in live}=={'first'}
 assert [slot.damage_position for slot in live]==[6,7]
 assert [slot.units for slot in live]==[12,12]
 assert select_active_weapon(registry.get('sulphur_carabineer'),'first').id=='secondary'
 assert any(
  event.type=='formation_fallback'
  and event.details.get('rule')=='land_exhausted_long_range_to_first'
  and event.details.get('primary_ammo_exhausted') is True
  for event in events
 )


def test_land_long_range_with_ammunition_stays_second():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':250,'wave_id':'front'},
  {'unit_id':'archer','quantity':60,'wave_id':'ranged'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 front.reserve=0
 for slot in front.slots:
  slot.units=50 if slot.damage_position in {1,2,3,4,5} else 0
 ranged.reserve=0
 assert ranged.ammo_pool_shots and ranged.ammo_pool_shots>0
 events=[]; applied={}
 _prepare_round_start(waves,events,2,'defender',applied,registry,rules,field)
 assert {slot.line for slot in ranged.slots if slot.units}=={'second'}
 assert not any(
  event.type=='formation_fallback'
  and event.details.get('unit_id')=='archer'
  for event in events
 )


def test_zero_ammo_land_long_range_fills_first_only_and_keeps_excess_in_reserve():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':300,'wave_id':'front'},
  {'unit_id':'sulphur_carabineer','quantity':84,'wave_id':'ranged'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 front.reserve=0
 for slot in front.slots:
  slot.units=50 if slot.damage_position in {1,2,3,4,5,6} else 0
  slot.damage=0
 ranged.reserve=0
 for slot in ranged.slots:
  slot.damage=0
 ranged.reserve_damage=0
 ranged.ammo_pool_shots=0
 events=[]; applied={}
 _prepare_round_start(waves,events,3,'defender',applied,registry,rules,field)
 assert sum(slot.units for slot in ranged.slots if slot.line=='second')==0
 assert ranged.reserve==72
 promoted=[wave for wave in waves if wave.unit.wave_id=='ranged::front-fallback-r3']
 assert len(promoted)==1
 front_wave=promoted[0]
 assert {slot.line for slot in front_wave.slots if slot.units}=={'first'}
 assert sum(slot.units for slot in front_wave.slots)==12
 assert [slot.damage_position for slot in front_wave.slots if slot.units]==[7]
 assert front_wave.ammo_pool_shots==0
 assert front_wave.ammo_capacity_shots==ranged.ammo_capacity_shots
 assert front_wave.ammo_capacity_shots and front_wave.ammo_capacity_shots>0
 assert any(
  event.type=='formation_fallback'
  and event.details.get('rule')=='land_exhausted_long_range_partial_to_first'
  and event.details.get('whole_wave') is False
  and event.details.get('quantity')==12
  and event.details.get('reserve_remaining')==72
  and event.details.get('native_second_deployed')==0
  for event in events
 )


def test_damaged_partial_exhausted_land_long_range_rr_precedes_first_selection():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':300,'wave_id':'front'},
  {'unit_id':'sulphur_carabineer','quantity':84,'wave_id':'ranged'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 front.reserve=0
 for slot in front.slots:
  slot.units=50 if slot.damage_position in {1,2,3,4,5,6} else 0
 ranged.reserve=0
 ranged.ammo_pool_shots=0
 next(slot for slot in ranged.slots if slot.units).damage=700
 events=[]; applied={}
 boundary=_prepare_round_start(waves,events,3,'defender',applied,registry,rules,field)
 assert boundary is False
 assert sum(slot.units for slot in ranged.slots if slot.line=='second')==0
 assert ranged.reserve==72
 promoted=[wave for wave in waves if wave.unit.wave_id=='ranged::front-fallback-r3']
 assert len(promoted)==1
 front_wave=promoted[0]
 assert sum(slot.units for slot in front_wave.slots if slot.line=='first')==12
 # RR over the original 84 survivors allocates half-up(700*12/84)=100
 # to the promoted First subset and keeps 600 with the 72 Reserve survivors.
 assert sum(slot.damage for slot in front_wave.slots)==100
 assert ranged.reserve_damage==600
 assert any(
  event.type=='redistribution'
  and event.details.get('rule')=='RR_BEFORE_DEPLOYMENT_SELECTION'
  and event.details.get('split_damage')==100
  and event.details.get('reserve_damage')==600
  for event in events
 )
 assert any(
  event.type=='formation_fallback'
  and event.details.get('damage_partition')=='rr_before_selection_proportional'
  for event in events
 )



def test_zero_ammo_land_long_range_with_full_front_stays_entirely_in_reserve():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':350,'wave_id':'front'},
  {'unit_id':'archer','quantity':84,'wave_id':'ranged'},
 ]}),registry,field)
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 ranged.ammo_pool_shots=0
 events=[]; applied={}
 _prepare_round_start(waves,events,4,'defender',applied,registry,rules,field)
 assert sum(slot.units for slot in ranged.slots if slot.line=='second')==0
 assert ranged.reserve==84


def test_three_remaining_carrier_shots_repeat_when_deployed_carriers_die_before_fire():
 registry=UnitRegistry.load()
 rules=FormationRules.load('formation-naval')
 field=NAVAL_BATTLEFIELDS['naval-max']
 waves=deploy(
  Army.from_dict({'units':[{'unit_id':'balloon_carrier','quantity':500,'wave_id':'carrier'}]}),
  registry,field,'formation-naval'
 )
 carrier=next(w for w in waves if w.unit.wave_id=='carrier')
 carrier.ammo_pool_shots=3
 events=[]; applied={}
 _prepare_round_start(waves,events,6,'attacker',applied,registry,rules,field)
 assert sum(slot.units for slot in carrier.slots if slot.line=='balloon')==3
 assert carrier.reserve==497
 assert carrier.ammo_pool_shots==3

 for slot in carrier.slots:
  if slot.line=='balloon':
   slot.units=0
   slot.damage=0
 assert carrier.alive==497
 assert carrier.ammo_pool_shots==3

 events2=[]; applied2={}
 _prepare_round_start(waves,events2,7,'attacker',applied2,registry,rules,field)
 assert sum(slot.units for slot in carrier.slots if slot.line=='balloon')==3
 assert carrier.reserve==494
 assert carrier.ammo_pool_shots==3
 assert any(
  event.type=='ammo_limited_deployment'
  and event.details.get('unit_id')=='balloon_carrier'
  and event.details.get('ammo_pool_shots')==3
  and event.details.get('deployed_units')==3
  for event in events2
 )



def test_ammo_limited_native_refill_uses_same_wave_rr_before_selection_invariant():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(
  Army.from_dict({'units':[{'unit_id':'archer','quantity':84,'wave_id':'ranged'}]}),
  registry,field,
 )
 ranged=next(w for w in waves if w.unit.wave_id=='ranged')
 ranged.ammo_pool_shots=3
 ranged.reserve=0
 for slot in ranged.slots:
  slot.damage=0
 next(slot for slot in ranged.slots if slot.units).damage=840
 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,5,'attacker',applied,registry,rules,field
 )
 assert boundary is False
 assert sum(slot.units for slot in ranged.slots if slot.line=='second')==3
 assert ranged.reserve==81
 # RR population is all 84 survivors: 840 * 3 / 84 = 30 deployed damage.
 assert sum(slot.damage for slot in ranged.slots if slot.line=='second')==30
 assert ranged.reserve_damage==810
 assert sum(slot.damage for slot in ranged.slots)+ranged.reserve_damage==840



def test_same_geometry_garrison_exit_is_recorded_before_independent_cross_wave_boundary():
 s={
  'policy':'experimental','battlefield':'land-max','max_rounds':2,
  'town_hall_level':25,'wall_level':3,
  'attacker':{'forge_level':5,'units':[
   {'unit_id':'hoplite','quantity':700},
   {'unit_id':'swordsman','quantity':480},
   {'unit_id':'sulphur_carabineer','quantity':168},
   {'unit_id':'mortar','quantity':60},
  ]},
  'defender':{'forge_level':5,'units':[
   {'unit_id':'steam_giant','quantity':224},
   {'unit_id':'swordsman','quantity':480},
   {'unit_id':'archer','quantity':700},
   {'unit_id':'catapult','quantity':60},
   {'unit_id':'mortar','quantity':36},
  ]},
 }
 result=simulate(s)
 exit_events=[
  e for e in result['events']
  if e['type']=='garrison_state_change'
  and e['details'].get('direction')=='exit_open_field'
 ]
 cross_events=[
  e for e in result['events']
  if e['type']=='unsupported_mechanic'
  and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
 ]
 if cross_events:
  assert exit_events
  assert exit_events[0]['round'] <= cross_events[0]['round']



def test_partial_fallback_generated_wave_id_may_match_another_unit_wave_id():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':300,'wave_id':'front'},
  {'unit_id':'archer','quantity':84,'wave_id':'ranged'},
  {'unit_id':'mortar','quantity':5,'wave_id':'ranged::front-fallback-r3'},
 ]}),registry,field)
 front=next(w for w in waves if w.unit.wave_id=='front')
 ranged=next(w for w in waves if w.unit.unit_id=='archer')
 front.reserve=0
 for slot in front.slots:
  slot.units=50 if slot.damage_position in {1,2,3,4,5,6} else 0
 ranged.reserve=0
 ranged.ammo_pool_shots=0
 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,3,'attacker',applied,registry,rules,field
 )
 assert boundary is False
 assert any(
  w.unit.unit_id=='archer' and w.unit.wave_id=='ranged::front-fallback-r3'
  for w in waves
 )
 assert any(
  w.unit.unit_id=='mortar' and w.unit.wave_id=='ranged::front-fallback-r3'
  for w in waves
 )


def test_partial_fallback_disambiguates_generated_id_from_same_unit_user_wave():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':300,'wave_id':'front'},
 ]}),registry,field)
 waves.extend([
  Wave(
   ArmyUnit('sulphur_carabineer',57,'src',entry_batch_id='batch-a'),
   57,[],0,0,0,171,
  ),
  Wave(
   ArmyUnit(
    'sulphur_carabineer',16,'src::front-fallback-r4',
    entry_batch_id='batch-b',
   ),
   16,[],0,48,0,48,
  ),
 ])
 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,4,'attacker',applied,registry,rules,field
 )
 assert boundary is False
 generated=[
  w for w in waves
  if w.unit.unit_id=='sulphur_carabineer'
  and w.unit.wave_id.startswith('src::front-fallback-r4')
  and w.unit.wave_id!='src::front-fallback-r4'
 ]
 assert len(generated)==1
 assert generated[0].unit.wave_id=='src::front-fallback-r4::2'
 assert any(
  event.type=='formation_fallback'
  and event.details.get('source_wave_id')=='src'
  and event.details.get('wave_id')==generated[0].unit.wave_id
  for event in events
 )


def test_partial_fallback_reserves_id_against_delayed_same_unit_arrival():
 registry=UnitRegistry.load(); rules=FormationRules.load(); field=LAND_BATTLEFIELDS['land-max']
 waves=deploy(Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':300,'wave_id':'front'},
 ]}),registry,field)
 waves.append(Wave(
  ArmyUnit('sulphur_carabineer',57,'src',entry_batch_id='batch-a'),
  57,[],0,0,0,171,
 ))
 scheduled=Army.from_dict({'units':[
  {
   'unit_id':'sulphur_carabineer','quantity':16,
   'wave_id':'src::front-fallback-r4','entry_batch_id':'batch-b',
   'arrival_round':5,
  },
 ]})
 reserved={(item.unit_id,item.wave_id) for item in scheduled.units}
 events=[]; applied={}
 boundary=_prepare_round_start(
  waves,events,4,'attacker',applied,registry,rules,field,
  reserved_wave_ids=reserved,
 )
 assert boundary is False
 generated=next(
  w for w in waves
  if w.unit.unit_id=='sulphur_carabineer'
  and w.unit.wave_id.startswith('src::front-fallback-r4::')
 )
 assert generated.unit.wave_id=='src::front-fallback-r4::2'
 arrivals=_arrival_waves(scheduled,5,registry,events,'attacker')
 waves.extend(arrivals)
 identities=[
  (w.unit.unit_id,w.unit.wave_id)
  for w in waves
  if w.unit.unit_id=='sulphur_carabineer'
 ]
 assert len(identities)==len(set(identities))


def test_tender_healing_event_does_not_pollute_doctor_status():
 scenario_obj=Scenario.from_dict({
  'policy':'experimental','battlefield':'naval-max','max_rounds':1,
  'attacker':{'units':[{'unit_id':'steam_ram','quantity':1}]},
  'defender':{'units':[{'unit_id':'steam_ram','quantity':1}]},
 })
 result={'events':[{
  'type':'healing','side':'attacker',
  'details':{'support_unit_id':'tender','healing':3500},
 }]}
 status=_healing_status(scenario_obj,result,SupportProfile.load())
 attacker=status['sides']['attacker']
 assert attacker['doctor_count']==0
 assert attacker['status']=='not_present'
 assert attacker['effect_applied'] is False
 assert attacker['healing_amount']==0
